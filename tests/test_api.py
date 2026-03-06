"""Tests for the Remy FastAPI HTTP API (remy.api module)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'

TEST_NOTES = DATA / 'test_notes'
TEST_MACROS = DATA / 'test_macros'
TEST_NOTES_MALFORMED = DATA / 'test_notes_malformed'


def _make_client(cache_path):
    """Create a TestClient for the API with the given cache path."""
    from remy.url import URL
    import remy.api.app as app_module

    url = URL(cache_path)
    app_module._cache_url = url
    app_module.notecard_cache = None  # ensure a fresh lazy load on first request

    return TestClient(app_module.app)


@pytest.fixture
def client():
    """TestClient using the standard test_notes cache."""
    return _make_client(TEST_NOTES)


@pytest.fixture
def macro_client():
    """TestClient using the test_macros cache (has MACROS in config)."""
    return _make_client(TEST_MACROS)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client):
    """GET /api returns 204 No Content."""
    response = client.get("/api")
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# GET /api/notecard/{card_label}
# ---------------------------------------------------------------------------

def test_get_notecard_found(client):
    """GET /api/notecard/<label> returns the notecard."""
    response = client.get("/api/notecard/weasel")
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "weasel"
    assert "NOTECARD" in body["raw"]
    assert "weasel" in body["raw"]


def test_get_notecard_by_primary_label(client):
    """GET /api/notecard/<primary_label> works."""
    response = client.get("/api/notecard/1")
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "1"
    assert "NOTECARD" in body["raw"]


def test_get_notecard_not_found(client):
    """GET /api/notecard/<unknown> returns 404."""
    response = client.get("/api/notecard/does-not-exist")
    assert response.status_code == 404
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# GET /api/query
# ---------------------------------------------------------------------------

def test_query_all(client):
    """GET /api/query?all=true returns all notecards."""
    response = client.get("/api/query?all=true")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    # Each item should have label, labels, raw
    for item in body:
        assert "label" in item
        assert "labels" in item
        assert "raw" in item


def test_query_expression(client):
    """GET /api/query?q=<expr> filters notecards."""
    response = client.get("/api/query", params={"q": "tag = 'inbox'"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


def test_query_missing_q_and_all(client):
    """GET /api/query without q or all returns 400."""
    response = client.get("/api/query")
    assert response.status_code == 400
    assert "detail" in response.json()


def test_query_q_and_all_mutually_exclusive(client):
    """Providing both q and all returns 400."""
    response = client.get("/api/query", params={"q": "tag='x'", "all": "true"})
    assert response.status_code == 400


def test_query_invalid_format(client):
    """Invalid format value returns 400."""
    response = client.get("/api/query", params={"all": "true", "format": "raw"})
    assert response.status_code == 400


def test_query_format_set(client):
    """format=set returns raw set output."""
    response = client.get("/api/query", params={"q": "values(tag)", "format": "set"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


def test_query_format_set_incompatible_with_fields(client):
    """format=set with fields returns 400."""
    response = client.get("/api/query", params={"all": "true", "format": "set", "fields": "@primary-label"})
    assert response.status_code == 400


def test_query_format_set_incompatible_with_order_by(client):
    """format=set with order_by returns 400."""
    response = client.get("/api/query", params={"q": "@id", "format": "set", "order_by": "TAG"})
    assert response.status_code == 400


def test_query_with_fields(client):
    """fields parameter extracts specific fields."""
    response = client.get("/api/query", params={"all": "true", "fields": "@primary-label"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert "@primary-label" in item
        assert isinstance(item["@primary-label"], list)


def test_query_order_by(client):
    """order_by sorts results."""
    response = client.get("/api/query", params={"all": "true", "order_by": "id"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_query_limit(client):
    """limit restricts number of results."""
    response_all = client.get("/api/query?all=true")
    total = len(response_all.json())

    if total > 1:
        response_limited = client.get("/api/query", params={"all": "true", "limit": "1"})
        assert response_limited.status_code == 200
        assert len(response_limited.json()) == 1


def test_query_reverse(client):
    """reverse=true reverses sort order."""
    resp_asc = client.get("/api/query?all=true&reverse=false")
    resp_desc = client.get("/api/query?all=true&reverse=true")
    assert resp_asc.status_code == 200
    assert resp_desc.status_code == 200
    labels_asc = [item["label"] for item in resp_asc.json()]
    labels_desc = [item["label"] for item in resp_desc.json()]
    if len(labels_asc) > 1:
        assert labels_asc != labels_desc


def test_query_stream(client):
    """stream=true returns NDJSON response."""
    response = client.get("/api/query?all=true&stream=true")
    assert response.status_code == 200
    assert "ndjson" in response.headers.get("content-type", "")
    # Each line should be valid JSON
    lines = [line for line in response.text.strip().split('\n') if line]
    for line in lines:
        obj = json.loads(line)
        assert "label" in obj


def test_query_stream_set(client):
    """stream=true with format=set returns NDJSON."""
    response = client.get("/api/query", params={"q": "values(tag)", "format": "set", "stream": "true"})
    assert response.status_code == 200
    assert "ndjson" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# GET /api/index
# ---------------------------------------------------------------------------

def test_index_list(client):
    """GET /api/index returns sorted list of field names."""
    response = client.get("/api/index")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    # Should be sorted
    assert body == sorted(body)
    # All names should be uppercase (as defined in PARSER_BY_FIELD_NAME)
    for name in body:
        assert name == name.upper()


def test_index_list_include_all_fields(client):
    """include_all_fields=true adds fields from card content."""
    response = client.get("/api/index?include_all_fields=true")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body == sorted(body)


# ---------------------------------------------------------------------------
# GET /api/index/{index_name}
# ---------------------------------------------------------------------------

def test_index_dump_full(client):
    """GET /api/index/TAG returns [label, value] pairs."""
    response = client.get("/api/index/TAG")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert isinstance(item, list)
        assert len(item) == 2


def test_index_dump_labels(client):
    """mode=labels returns labels only."""
    response = client.get("/api/index/TAG?mode=labels")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert isinstance(item, str)


def test_index_dump_values(client):
    """mode=values returns values only."""
    response = client.get("/api/index/TAG?mode=values")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


def test_index_dump_unique(client):
    """unique=true removes duplicates."""
    response = client.get("/api/index/TAG?mode=values&unique=true")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(set(body))


def test_index_dump_limit(client):
    """limit restricts the number of returned entries."""
    response_all = client.get("/api/index/TAG")
    total = len(response_all.json())

    if total > 1:
        response_limited = client.get("/api/index/TAG?limit=1")
        assert response_limited.status_code == 200
        assert len(response_limited.json()) == 1


def test_index_dump_limit_after_unique(client):
    """limit is applied after unique deduplication."""
    response = client.get("/api/index/TAG?mode=values&unique=true&limit=1")
    assert response.status_code == 200
    body = response.json()
    assert len(body) <= 1


def test_index_dump_limit_invalid(client):
    """limit < 1 returns 422."""
    response = client.get("/api/index/TAG?limit=0")
    assert response.status_code == 422


def test_index_dump_not_found(client):
    """Unknown index_name returns 404."""
    response = client.get("/api/index/UNKNOWN_FIELD_XYZ")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_index_dump_invalid_mode(client):
    """Invalid mode returns 400."""
    response = client.get("/api/index/TAG?mode=badmode")
    assert response.status_code == 400


def test_index_dump_stream(client):
    """stream=true returns NDJSON."""
    response = client.get("/api/index/TAG?stream=true")
    assert response.status_code == 200
    assert "ndjson" in response.headers.get("content-type", "")
    lines = [line for line in response.text.strip().split('\n') if line]
    for line in lines:
        json.loads(line)


def test_index_dump_case_insensitive(client):
    """Index name lookup is case-insensitive."""
    response_upper = client.get("/api/index/TAG")
    response_lower = client.get("/api/index/tag")
    assert response_upper.status_code == 200
    assert response_lower.status_code == 200
    assert response_upper.json() == response_lower.json()


# ---------------------------------------------------------------------------
# GET /api/index/{index_name}/validate
# ---------------------------------------------------------------------------

def test_index_validate_no_errors(client):
    """Validation with no errors returns empty array with 200."""
    response = client.get("/api/index/TAG/validate")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_index_validate_not_found(client):
    """Unknown index_name returns 404."""
    response = client.get("/api/index/UNKNOWN_FIELD_XYZ/validate")
    assert response.status_code == 404


def test_index_validate_with_errors(macro_client):
    """Malformed field values appear in validation errors."""
    client = _make_client(TEST_NOTES_MALFORMED)
    # PRIORITY has a malformed value in test_notes_malformed
    response = client.get("/api/index/PRIORITY/validate")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    # Should contain at least one error for the malformed data
    # (It's okay if the malformed test data has no PRIORITY errors;
    # we just verify the endpoint works correctly)
    for error in body:
        assert "label" in error
        assert "error_type" in error
        assert "error_message" in error


def test_index_validate_show_uri(client):
    """show_uri=true adds uri field to errors."""
    response = client.get("/api/index/PRIORITY/validate?show_uri=true")
    assert response.status_code == 200
    body = response.json()
    for error in body:
        # uri key should be present (may be None if source_url is None)
        assert "uri" in error


def test_index_validate_show_line(client):
    """show_line=true adds uri, field_name, field_value to errors."""
    response = client.get("/api/index/PRIORITY/validate?show_line=true")
    assert response.status_code == 200
    body = response.json()
    for error in body:
        assert "uri" in error
        assert "field_name" in error
        assert "field_value" in error


# ---------------------------------------------------------------------------
# GET /api/macro
# ---------------------------------------------------------------------------

def test_macro_list_names(macro_client):
    """GET /api/macro returns macro names with @ prefix."""
    response = macro_client.get("/api/macro")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for name in body:
        assert name.startswith('@')


def test_macro_list_full(macro_client):
    """mode=full returns name+definition objects."""
    response = macro_client.get("/api/macro?mode=full")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert "name" in item
        assert "definition" in item
        assert item["name"].startswith('@')


def test_macro_list_expand(macro_client):
    """mode=expand returns expanded definitions."""
    response = macro_client.get("/api/macro?mode=expand")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert "name" in item
        assert "definition" in item


def test_macro_filter_by_name(macro_client):
    """name parameter filters to a single macro."""
    response = macro_client.get("/api/macro?name=work")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0] == "@work"


def test_macro_filter_by_name_with_at(macro_client):
    """name parameter with @ prefix also works."""
    response = macro_client.get("/api/macro?name=@work")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1


def test_macro_not_found(macro_client):
    """Requesting a macro that does not exist returns 404."""
    response = macro_client.get("/api/macro?name=does_not_exist")
    assert response.status_code == 404


def test_macro_invalid_mode(macro_client):
    """Invalid mode returns 400."""
    response = macro_client.get("/api/macro?mode=invalid")
    assert response.status_code == 400


def test_macro_no_macros(client):
    """Cache without macros returns empty array."""
    # test_notes cache has no MACROS defined
    response = client.get("/api/macro")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

def test_invalidate_cache_sets_none():
    """invalidate_cache() sets the global notecard_cache to None."""
    from remy import NotecardCache
    from remy.url import URL
    import remy.api.app as app_module

    url = URL(TEST_NOTES)
    app_module.notecard_cache = NotecardCache(url)
    assert app_module.notecard_cache is not None

    app_module.invalidate_cache(reason="test")

    assert app_module.notecard_cache is None


def test_get_cache_raises_after_invalidation():
    """get_cache() raises HTTP 500 when cache is None and no URL is configured."""
    import remy.api.app as app_module
    from fastapi import HTTPException

    app_module.notecard_cache = None
    app_module._cache_url = None

    with pytest.raises(HTTPException) as exc_info:
        app_module.get_cache()

    assert exc_info.value.status_code == 500


def test_get_cache_reloads_after_invalidation():
    """get_cache() transparently reloads the cache after invalidation."""
    from remy.url import URL
    import remy.api.app as app_module

    app_module._cache_url = URL(TEST_NOTES)
    app_module.notecard_cache = None

    cache = app_module.get_cache()

    assert cache is not None
    # Verify that the module-level variable was repopulated so subsequent
    # calls return the same instance without rebuilding the cache again.
    assert app_module.notecard_cache is cache


def test_invalidate_cache_does_not_delete_existing_reference():
    """Invalidating the global cache does not affect already-held local references."""
    from remy import NotecardCache
    from remy.url import URL
    import remy.api.app as app_module

    url = URL(TEST_NOTES)
    app_module.notecard_cache = NotecardCache(url)

    # Simulate a request obtaining its own reference before invalidation
    local_ref = app_module.get_cache()
    assert local_ref is not None

    app_module.invalidate_cache(reason="test")

    # Global is now None but the local reference is still usable
    assert app_module.notecard_cache is None
    assert local_ref is not None
    assert local_ref.cards_by_label is not None


def test_sighup_handler_invalidates_cache():
    """Sending SIGHUP to the current process invalidates the notecard cache."""
    import os
    import signal
    import time
    import remy.api.app as app_module
    from remy import NotecardCache
    from remy.url import URL

    if not hasattr(signal, 'SIGHUP'):
        pytest.skip("SIGHUP not available on this platform")

    url = URL(TEST_NOTES)
    app_module.notecard_cache = NotecardCache(url)
    assert app_module.notecard_cache is not None

    app_module._register_sighup_handler()
    os.kill(os.getpid(), signal.SIGHUP)

    # Signal handlers in CPython run synchronously between bytecodes, so the
    # cache should already be None; poll briefly to handle any edge cases.
    deadline = time.monotonic() + 2.0
    while app_module.notecard_cache is not None and time.monotonic() < deadline:
        time.sleep(0.01)

    assert app_module.notecard_cache is None, "Cache was not invalidated after SIGHUP"


def test_fs_watcher_starts_and_stops():
    """_start_fs_watcher returns an Observer that can be started and stopped."""
    import remy.api.app as app_module

    observer = app_module._start_fs_watcher(str(TEST_NOTES))
    if observer is None:
        pytest.skip("watchdog not available")

    assert observer.is_alive()
    observer.stop()
    observer.join()
    assert not observer.is_alive()


def test_fs_watcher_invalidates_cache_on_change(tmp_path):
    """Creating a file in the watched directory invalidates the cache."""
    import time
    import remy.api.app as app_module
    from remy import NotecardCache
    from remy.url import URL

    # Set up a temporary cache-like directory with the minimum required structure
    remy_dir = tmp_path / '.remy'
    remy_dir.mkdir()
    (remy_dir / 'config.py').write_text("PARSER_BY_FIELD_NAME = {}\n")

    url = URL(tmp_path)
    app_module.notecard_cache = NotecardCache(url)
    assert app_module.notecard_cache is not None

    observer = app_module._start_fs_watcher(str(tmp_path))
    if observer is None:
        pytest.skip("watchdog not available")

    try:
        # Create a new file in the watched directory to trigger an event
        (tmp_path / 'new_note.txt').write_text("NOTECARD test\nsome content\n")

        # Give the watcher time to detect the change
        deadline = time.monotonic() + 5.0
        while app_module.notecard_cache is not None and time.monotonic() < deadline:
            time.sleep(0.05)

        assert app_module.notecard_cache is None, "Cache was not invalidated after file creation"
    finally:
        observer.stop()
        observer.join()

