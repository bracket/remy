"""Unit tests for the Remy MCP server tools."""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int, json_data):
    """Build a mock httpx.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


# ---------------------------------------------------------------------------
# handle_api_response
# ---------------------------------------------------------------------------

class TestHandleApiResponse:
    def test_not_found_raises_value_error(self):
        from remy.mcp import handle_api_response
        resp = _make_response(404, {"detail": "Notecard 'x' not found"})
        with pytest.raises(ValueError, match="Notecard 'x' not found"):
            handle_api_response(resp)

    def test_bad_request_raises_value_error(self):
        from remy.mcp import handle_api_response
        resp = _make_response(400, {"detail": "Bad request detail"})
        with pytest.raises(ValueError, match="Bad request detail"):
            handle_api_response(resp)

    def test_unprocessable_entity_raises_value_error(self):
        from remy.mcp import handle_api_response
        resp = _make_response(422, {"detail": "Unprocessable"})
        with pytest.raises(ValueError, match="Unprocessable"):
            handle_api_response(resp)

    def test_server_error_raises_runtime_error(self):
        from remy.mcp import handle_api_response
        resp = _make_response(500, {"detail": "Internal error"})
        with pytest.raises(RuntimeError, match="Internal error"):
            handle_api_response(resp)

    def test_successful_response_returns_json(self):
        from remy.mcp import handle_api_response
        data = [{"label": "foo"}]
        resp = _make_response(200, data)
        resp.raise_for_status = MagicMock()
        assert handle_api_response(resp) == data


# ---------------------------------------------------------------------------
# query_notecards
# ---------------------------------------------------------------------------

class TestQueryNotecards:
    def _call(self, **kwargs):
        from remy.mcp import query_notecards
        return query_notecards(**kwargs)

    def test_requires_query_or_all(self):
        with pytest.raises(ValueError, match="Provide either"):
            self._call()

    def test_query_and_all_mutually_exclusive(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            self._call(query="tag='x'", all=True)

    def test_query_makes_http_request(self):
        from remy.mcp import query_notecards
        data = [{"label": "a", "labels": ["a"], "raw": "NOTECARD a\n\nContent\n"}]
        mock_resp = _make_response(200, data)
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = query_notecards(query="tag = 'inbox'")

        assert result == data
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[0][0] == "/api/query"
        params = call_args[1]["params"]
        assert params["q"] == "tag = 'inbox'"
        assert params["format"] == "json"

    def test_all_parameter(self):
        from remy.mcp import query_notecards
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            query_notecards(all=True)

        params = mock_client.get.call_args[1]["params"]
        assert params.get("all") == "true"
        assert "q" not in params

    def test_limit_and_fields_passed_through(self):
        from remy.mcp import query_notecards
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            query_notecards(query="tag='x'", limit=5, fields="@primary-label,tag")

        params = mock_client.get.call_args[1]["params"]
        assert params["limit"] == "5"
        assert params["fields"] == "@primary-label,tag"


# ---------------------------------------------------------------------------
# get_notecard
# ---------------------------------------------------------------------------

class TestGetNotecard:
    def test_found(self):
        from remy.mcp import get_notecard
        data = {"label": "my-note", "raw": "NOTECARD my-note\n\nContent\n"}
        mock_resp = _make_response(200, data)
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = get_notecard("my-note")

        assert result == data
        mock_client.get.assert_called_once_with("/api/notecard/my-note")

    def test_not_found_raises_value_error(self):
        from remy.mcp import get_notecard
        mock_resp = _make_response(404, {"detail": "Notecard 'missing' not found."})

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            with pytest.raises(ValueError, match="Notecard 'missing' not found"):
                get_notecard("missing")


# ---------------------------------------------------------------------------
# list_field_indexes
# ---------------------------------------------------------------------------

class TestListFieldIndexes:
    def test_returns_list(self):
        from remy.mcp import list_field_indexes
        data = ["CREATED", "TAG"]
        mock_resp = _make_response(200, data)
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_field_indexes()

        assert result == data
        mock_client.get.assert_called_once_with("/api/index", params={})

    def test_include_all_fields_passed(self):
        from remy.mcp import list_field_indexes
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            list_field_indexes(include_all_fields=True)

        params = mock_client.get.call_args[1]["params"]
        assert params.get("include_all_fields") == "true"


# ---------------------------------------------------------------------------
# dump_field_index
# ---------------------------------------------------------------------------

class TestDumpFieldIndex:
    def test_full_mode(self):
        from remy.mcp import dump_field_index
        data = [["note-a", "inbox"], ["note-b", "work"]]
        mock_resp = _make_response(200, data)
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = dump_field_index("TAG")

        assert result == data
        call_args = mock_client.get.call_args
        assert call_args[0][0] == "/api/index/TAG"
        params = call_args[1]["params"]
        assert params["mode"] == "full"

    def test_limit_parameter_passed(self):
        from remy.mcp import dump_field_index
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            dump_field_index("TAG", limit=10)

        params = mock_client.get.call_args[1]["params"]
        assert params["limit"] == "10"

    def test_not_found_raises_value_error(self):
        from remy.mcp import dump_field_index
        mock_resp = _make_response(404, {"detail": "Field index 'UNKNOWN' not found in configuration."})

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            with pytest.raises(ValueError, match="Field index 'UNKNOWN' not found"):
                dump_field_index("UNKNOWN")

    def test_unique_and_mode_passed(self):
        from remy.mcp import dump_field_index
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            dump_field_index("TAG", mode="values", unique=True)

        params = mock_client.get.call_args[1]["params"]
        assert params["mode"] == "values"
        assert params["unique"] == "true"


# ---------------------------------------------------------------------------
# validate_field_index
# ---------------------------------------------------------------------------

class TestValidateFieldIndex:
    def test_no_errors(self):
        from remy.mcp import validate_field_index
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = validate_field_index("TAG")

        assert result == []
        call_args = mock_client.get.call_args
        assert "/validate" in call_args[0][0]

    def test_show_details_passes_show_line(self):
        from remy.mcp import validate_field_index
        mock_resp = _make_response(200, [])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            validate_field_index("TAG", show_details=True)

        params = mock_client.get.call_args[1]["params"]
        assert params.get("show_line") == "true"

    def test_not_found_raises_value_error(self):
        from remy.mcp import validate_field_index
        mock_resp = _make_response(404, {"detail": "Field index 'X' not found in configuration."})

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            with pytest.raises(ValueError):
                validate_field_index("X")


# ---------------------------------------------------------------------------
# list_macros
# ---------------------------------------------------------------------------

class TestListMacros:
    def test_names_mode(self):
        from remy.mcp import list_macros
        data = ["@inbox", "@work"]
        mock_resp = _make_response(200, data)
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = list_macros()

        assert result == data
        params = mock_client.get.call_args[1]["params"]
        assert params["mode"] == "names"

    def test_name_filter_passed(self):
        from remy.mcp import list_macros
        mock_resp = _make_response(200, ["@work"])
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            list_macros(name="work")

        params = mock_client.get.call_args[1]["params"]
        assert params["name"] == "work"

    def test_macro_not_found_raises_value_error(self):
        from remy.mcp import list_macros
        mock_resp = _make_response(404, {"detail": "Macro '@missing' not found."})

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            with pytest.raises(ValueError, match="Macro '@missing' not found"):
                list_macros(name="missing")


# ---------------------------------------------------------------------------
# query_set
# ---------------------------------------------------------------------------

class TestQuerySet:
    def test_values_query(self):
        from remy.mcp import query_set
        data = ["archive", "inbox", "work"]
        mock_resp = _make_response(200, data)
        mock_resp.raise_for_status = MagicMock()

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            result = query_set("values(tag)")

        assert result == data
        params = mock_client.get.call_args[1]["params"]
        assert params["q"] == "values(tag)"
        assert params["format"] == "set"

    def test_invalid_query_raises_value_error(self):
        from remy.mcp import query_set
        mock_resp = _make_response(400, {"detail": "Parse error in query"})

        with patch("remy.mcp.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.get.return_value = mock_resp

            with pytest.raises(ValueError, match="Parse error in query"):
                query_set("!!!invalid!!!")
