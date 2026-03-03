"""
FastAPI application for the Remy HTTP API.

Exposes Remy's read-only functionality (query, index, macro) as RESTful JSON
endpoints with automatic OpenAPI documentation.
"""

import json
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

# Global cache reference, set at startup
notecard_cache = None

app = FastAPI(
    title="Remy API",
    description="HTTP API for the Remy notecard management system.",
    version="0.1.0",
)


def get_cache():
    """Return the loaded notecard cache, raising 500 if not configured."""
    if notecard_cache is None:
        raise HTTPException(status_code=500, detail="Notecard cache is not configured.")
    return notecard_cache


def _make_json_serializable(value):
    """Convert non-JSON-serializable types to reasonable string representations."""
    from datetime import datetime, date, time, timedelta

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    elif isinstance(value, timedelta):
        return str(value)
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    else:
        return str(value)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api", status_code=204, summary="Health check")
def health_check():
    """Return 204 No Content to confirm the API is running."""
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Notecards
# ---------------------------------------------------------------------------

@app.get("/api/notecard/{card_label}", summary="Retrieve a notecard by label")
def get_notecard(card_label: str):
    """Retrieve a single notecard by its label.

    Returns a JSON object with the notecard's label and full raw text.
    Returns 404 if no notecard with the given label exists.
    """
    from remy.cli.__main__ import format_notecard_raw

    cache = get_cache()
    card = cache.cards_by_label.get(card_label)
    if card is None:
        raise HTTPException(
            status_code=404,
            detail=f"Notecard with label '{card_label}' not found.",
        )
    return {
        "label": card_label,
        "raw": format_notecard_raw(card),
    }


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def _load_config_macros(cache):
    """Load macros from the cache config, returning None if unavailable."""
    from remy.query.eval import parse_config_macros
    from remy.exceptions import RemyError

    try:
        config_module = cache.config_module
        if hasattr(config_module, 'MACROS'):
            return parse_config_macros(config_module.MACROS)
    except RemyError as e:
        if "Configuration file not found" not in str(e):
            raise
    return None


def _execute_query_filter(cache, query_string):
    """Parse and evaluate *query_string*, returning a list of matching notecards."""
    from remy.query.parser import parse_query
    from remy.query.eval import evaluate_query, resolve_macros
    from remy.query.util import extract_field_names

    ast = parse_query(query_string)
    config_macros = _load_config_macros(cache)
    ast = resolve_macros(ast, config_macros)
    field_names = extract_field_names(ast)
    field_indices = cache.field_indices(field_names)
    matching_labels = evaluate_query(ast, field_indices)

    unique_cards = list(
        {
            card.primary_label: card
            for label in matching_labels
            if (card := cache.cards_by_label.get(label)) is not None
        }.values()
    )
    return unique_cards


def _execute_query_raw(cache, query_string):
    """Parse and evaluate *query_string*, returning the raw set result."""
    from remy.query.parser import parse_query
    from remy.query.eval import _evaluate, resolve_macros
    from remy.query.util import extract_field_names

    ast = parse_query(query_string)
    config_macros = _load_config_macros(cache)
    ast = resolve_macros(ast, config_macros)
    field_names = extract_field_names(ast)
    field_indices = cache.field_indices(field_names)
    return _evaluate(ast, field_indices)


def _get_sort_key(card, cache, order_by_key):
    """Return a sort key tuple for *card*."""
    primary_label = card.primary_label
    if order_by_key == 'id':
        return (primary_label, primary_label)
    field_name_upper = order_by_key.upper()
    try:
        field_index = cache.field_index(field_name_upper)
        values = field_index.inverse.get(primary_label, [])
        if not values:
            return (1, None, primary_label)
        return (0, min(values), primary_label)
    except (KeyError, AttributeError):
        return (1, None, primary_label)


def _extract_field_values(card, field_names, cache):
    """Extract field values from *card* for the given *field_names*."""
    result = {}
    for field_name in field_names:
        fl = field_name.lower()
        if fl in ('@primary-label', '@id'):
            result[field_name] = [card.primary_label]
        elif fl == '@label':
            result[field_name] = list(card.labels)
        elif fl in ('@title', '@first-block'):
            fb = card.first_block
            result[field_name] = [fb] if fb else []
        else:
            field_name_upper = field_name.upper()
            try:
                field_index = cache.field_index(field_name_upper)
                values = field_index.inverse.get(card.primary_label, [])
                result[field_name] = [_make_json_serializable(v) for v in values]
            except (KeyError, AttributeError):
                result[field_name] = []
    return result


def _card_to_json(card, cache):
    """Serialize *card* to a JSON-compatible dict (no fields selection)."""
    from remy.cli.__main__ import format_notecard_raw
    return {
        "label": card.primary_label,
        "labels": list(card.labels),
        "raw": format_notecard_raw(card),
    }


def _pairset_to_json(pairset, limit=None, reverse=False):
    """Serialize a PairSet to a JSON-compatible list of [label, value] pairs."""
    items = reversed(pairset) if reverse else iter(pairset)
    result = []
    for typed_value, label in items:
        _, value = typed_value
        result.append([label, _make_json_serializable(value)])
        if limit is not None and len(result) >= limit:
            break
    return result


def _labelset_to_json(labelset, limit=None, reverse=False):
    """Serialize a LabelSet to a sorted JSON-compatible list."""
    items = sorted(labelset, reverse=reverse)
    if limit is not None:
        items = items[:limit]
    return items


def _valueset_to_json(valueset, limit=None, reverse=False):
    """Serialize a ValueSet to a JSON-compatible list."""
    values = list(valueset)
    if reverse:
        values = list(reversed(values))
    if limit is not None:
        values = values[:limit]
    return [_make_json_serializable(v) for v in values]


def _serialize_set_result(raw_result, limit=None, reverse=False):
    """Serialize a raw set result (PairSet / LabelSet / ValueSet) to a Python list."""
    from remy.query.set_types import ValueSet
    from sortedcontainers import SortedSet

    if isinstance(raw_result, SortedSet):
        return _pairset_to_json(raw_result, limit=limit, reverse=reverse)
    elif isinstance(raw_result, ValueSet):
        return _valueset_to_json(raw_result, limit=limit, reverse=reverse)
    elif isinstance(raw_result, set):
        return _labelset_to_json(raw_result, limit=limit, reverse=reverse)
    else:
        raise HTTPException(status_code=500, detail=f"Unexpected set type: {type(raw_result).__name__}")


@app.get("/api/query", summary="Query notecards")
def query_notecards(
    q: Optional[str] = Query(None, description="Query expression"),
    all_notecards: bool = Query(False, alias="all", description="Return all notecards"),
    output_format: str = Query("json", alias="format", description="Output format: json or set"),
    order_by: str = Query("id", description="Sort key: 'id' or a field name"),
    reverse: bool = Query(False, description="Reverse sort order"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results"),
    fields: Optional[str] = Query(None, description="Comma-separated field names"),
    stream: bool = Query(False, description="Stream results as NDJSON"),
):
    """Query and filter notecards.

    Exactly one of ``q`` or ``all=true`` must be provided.
    Use ``format=json`` (default) for a JSON array or ``format=set`` for raw
    set output.  Pass ``stream=true`` for chunked NDJSON output.
    """
    from remy.exceptions import RemyError

    cache = get_cache()

    # Validate format
    format_lower = output_format.lower()
    if format_lower not in ('json', 'set'):
        raise HTTPException(status_code=400, detail=f"Invalid format '{output_format}'. Must be 'json' or 'set'.")

    # Validate mutual exclusivity
    if q and all_notecards:
        raise HTTPException(status_code=400, detail="Parameters 'q' and 'all' are mutually exclusive.")
    if not q and not all_notecards:
        raise HTTPException(status_code=400, detail="Either 'q' or 'all=true' must be provided.")

    # Validate incompatible combinations with format=set
    if format_lower == 'set':
        if fields:
            raise HTTPException(status_code=400, detail="'fields' is incompatible with format=set.")
        if order_by != 'id':
            raise HTTPException(status_code=400, detail="'order_by' is incompatible with format=set.")

    field_names = [f.strip() for f in fields.split(',') if f.strip()] if fields else None

    # --- format=set ---
    if format_lower == 'set':
        query_string = '@id' if all_notecards else q
        try:
            raw_result = _execute_query_raw(cache, query_string)
        except RemyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        serialized = _serialize_set_result(raw_result, limit=limit, reverse=reverse)

        if stream:
            def _generate():
                for item in serialized:
                    yield json.dumps(item, ensure_ascii=False) + '\n'
            return StreamingResponse(_generate(), media_type="application/x-ndjson")

        return serialized

    # --- format=json ---
    if all_notecards:
        cards = list(
            {card.primary_label: card for card in cache.cards_by_label.values()}.values()
        )
    else:
        try:
            cards = _execute_query_filter(cache, q)
        except RemyError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Sort
    cards.sort(key=lambda c: _get_sort_key(c, cache, order_by), reverse=reverse)

    # Limit
    if limit is not None:
        cards = cards[:limit]

    # Build response objects
    if field_names:
        result_items = [_extract_field_values(card, field_names, cache) for card in cards]
    else:
        result_items = [_card_to_json(card, cache) for card in cards]

    if stream:
        def _generate():
            for item in result_items:
                yield json.dumps(item, ensure_ascii=False) + '\n'
        return StreamingResponse(_generate(), media_type="application/x-ndjson")

    return result_items


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

@app.get("/api/index", summary="List field index names")
def list_indices(
    include_all_fields: bool = Query(False, description="Also include field names found in card content"),
):
    """List all configured field index names.

    Returns an alphabetically sorted JSON array of field index names.
    When ``include_all_fields=true``, also includes names discovered from
    notecard content that have no configured parser.
    """
    cache = get_cache()

    try:
        field_names = set(cache.config_module.PARSER_BY_FIELD_NAME.keys())
    except AttributeError:
        raise HTTPException(
            status_code=500,
            detail="Configuration file missing or PARSER_BY_FIELD_NAME not defined.",
        )

    if include_all_fields:
        from remy.ast.parse import parse_content
        from remy.ast import Field

        for label, card in cache.cards_by_label.items():
            if label != card.primary_label:
                continue
            for node in parse_content(card.content):
                if isinstance(node, Field):
                    field_names.add(node.label.upper())

    return sorted(field_names)


@app.get("/api/index/{index_name}/validate", summary="Validate field parsing")
def validate_index(
    index_name: str,
    show_uri: bool = Query(False, description="Include source file URI in each error"),
    show_line: bool = Query(False, description="Include source URI, field name, and raw field value"),
):
    """Validate field parsing for a specific field index.

    Returns a list of parsing errors.  An empty array means no errors.
    Always returns 200 OK; the presence of errors is indicated by a non-empty array.
    """
    from remy.ast.parse import parse_content
    from remy.ast import Field

    cache = get_cache()

    try:
        field_parser = cache.config_module.PARSER_BY_FIELD_NAME[index_name.upper()]
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Field index '{index_name}' not found in configuration.",
        )
    except AttributeError:
        raise HTTPException(
            status_code=500,
            detail="Configuration file missing or PARSER_BY_FIELD_NAME not defined.",
        )

    errors = []
    field_name_upper = index_name.upper()

    for label, card in cache.cards_by_label.items():
        if label != card.primary_label:
            continue
        for node in parse_content(card.content):
            if not isinstance(node, Field):
                continue
            if node.label.upper() != field_name_upper:
                continue
            try:
                list(field_parser(node.value))
            except Exception as e:
                error = {
                    "label": card.primary_label,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                if show_uri or show_line:
                    error["uri"] = str(card.source_url) if card.source_url else None
                if show_line:
                    error["field_name"] = node.label
                    error["field_value"] = node.value
                errors.append(error)

    return errors


@app.get("/api/index/{index_name}", summary="Dump a field index")
def dump_index(
    index_name: str,
    mode: str = Query("full", description="Output mode: full, labels, or values"),
    unique: bool = Query(False, description="Remove duplicate entries"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of entries to return"),
    stream: bool = Query(False, description="Stream results as NDJSON"),
):
    """Dump the contents of a specific field index.

    ``mode=full`` returns ``[label, value]`` pairs; ``mode=labels`` returns
    labels only; ``mode=values`` returns values only.  When both ``unique``
    and ``limit`` are specified, deduplication is applied first.
    """
    cache = get_cache()

    mode_lower = mode.lower()
    if mode_lower not in ('full', 'labels', 'values'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be 'full', 'labels', or 'values'.",
        )

    try:
        field_index = cache.field_index(index_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Field index '{index_name}' not found in configuration.",
        )
    except AttributeError:
        raise HTTPException(
            status_code=500,
            detail="Configuration file missing or PARSER_BY_FIELD_NAME not defined.",
        )

    data = []
    if mode_lower == 'full':
        for (type_id, value), label in field_index.index:
            data.append([label, _make_json_serializable(value)])
    elif mode_lower == 'labels':
        for (type_id, value), label in field_index.index:
            data.append(label)
    elif mode_lower == 'values':
        for (type_id, value), label in field_index.index:
            data.append(_make_json_serializable(value))

    if unique:
        seen = set()
        unique_data = []
        for item in data:
            key = tuple(item) if isinstance(item, list) else item
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        data = unique_data

    if limit is not None:
        data = data[:limit]

    if stream:
        def _generate():
            for item in data:
                yield json.dumps(item, ensure_ascii=False) + '\n'
        return StreamingResponse(_generate(), media_type="application/x-ndjson")

    return data


# ---------------------------------------------------------------------------
# Macro
# ---------------------------------------------------------------------------

@app.get("/api/macro", summary="List query macros")
def list_macros(
    mode: str = Query("names", description="Display mode: names, full, or expand"),
    name: Optional[str] = Query(None, description="Filter to a specific macro name"),
):
    """List configured query macros.

    ``mode=names`` returns macro names only; ``mode=full`` returns definitions;
    ``mode=expand`` returns expanded definitions.
    """
    from remy.query.eval import parse_config_macros, resolve_macros
    from remy.query.parser import parse_query
    from remy.query.ast_nodes import MacroReference, StatementList, MacroDefinition
    from remy.exceptions import RemyError
    from remy.cli.__main__ import _format_ast_node, _expand_macro_body

    cache = get_cache()

    mode_lower = mode.lower()
    if mode_lower not in ('names', 'full', 'expand'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be 'names', 'full', or 'expand'.",
        )

    try:
        config_macros_dict = cache.config_module.MACROS
    except AttributeError:
        config_macros_dict = {}

    if not config_macros_dict:
        if name:
            raise HTTPException(status_code=404, detail=f"Macro '{name}' not found.")
        return []

    try:
        parsed_macros = parse_config_macros(config_macros_dict)
    except RemyError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config macros: {e}")

    # Normalize requested name
    lookup_name = None
    if name:
        lookup_name = name.lstrip('@')
        if lookup_name not in parsed_macros:
            raise HTTPException(status_code=404, detail=f"Macro '@{lookup_name}' not found.")
        macro_names = [lookup_name]
    else:
        macro_names = sorted(parsed_macros.keys())

    if mode_lower == 'names':
        return [f"@{n}" for n in macro_names]

    result = []

    if mode_lower == 'full':
        for n in macro_names:
            # Try to retrieve the original definition string
            original_def = None
            for key, value in config_macros_dict.items():
                try:
                    temp_ast = parse_query(value)
                    if isinstance(temp_ast, StatementList) and len(temp_ast.statements) == 1:
                        temp_def = temp_ast.statements[0]
                    else:
                        temp_def = temp_ast
                    if isinstance(temp_def, MacroDefinition) and temp_def.name == n:
                        original_def = value
                        break
                except Exception:
                    continue

            if original_def:
                result.append({"name": f"@{n}", "definition": original_def})
            else:
                macro_def = parsed_macros[n]
                body_str = _format_ast_node(macro_def.body)
                if macro_def.parameters:
                    params = ', '.join(macro_def.parameters)
                    result.append({"name": f"@{n}", "definition": f"@{n}({params}) := {body_str}"})
                else:
                    result.append({"name": f"@{n}", "definition": f"@{n} := {body_str}"})

    elif mode_lower == 'expand':
        for n in macro_names:
            macro_def = parsed_macros[n]
            try:
                if macro_def.parameters:
                    expanded_body = _expand_macro_body(macro_def.body, parsed_macros)
                    body_str = _format_ast_node(expanded_body)
                    params = ', '.join(macro_def.parameters)
                    definition = f"@{n}({params}) := {body_str}"
                else:
                    macro_ref = MacroReference(n, [])
                    expanded = resolve_macros(macro_ref, parsed_macros)
                    definition = f"@{n} := {_format_ast_node(expanded)}"
                result.append({"name": f"@{n}", "definition": definition})
            except RemyError as e:
                raise HTTPException(status_code=400, detail=f"Error expanding macro @{n}: {e}")

    return result
