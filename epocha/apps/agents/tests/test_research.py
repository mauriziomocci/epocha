"""Tests for biographical research via Wikipedia and web search."""

from unittest.mock import MagicMock, patch

from epocha.apps.agents.research import (
    research_person,
    search_duckduckgo,
    search_wikipedia,
)


class TestSearchWikipedia:
    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_summary_for_known_person(self, mock_get):
        """Wikipedia search should return a biographical summary."""
        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "pages": [{"key": "Lucrezia_Borgia", "title": "Lucrezia Borgia"}]
        }

        summary_response = MagicMock()
        summary_response.status_code = 200
        summary_response.json.return_value = {
            "title": "Lucrezia Borgia",
            "extract": (
                "Lucrezia Borgia was an Italian noblewoman of the House of Borgia."
            ),
        }

        mock_get.side_effect = [search_response, summary_response]

        result = search_wikipedia("Lucrezia Borgia")

        assert result is not None
        assert "Borgia" in result

    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_none_for_unknown_person(self, mock_get):
        """Wikipedia search should return None if no results found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"pages": []}
        mock_get.return_value = mock_response

        result = search_wikipedia("Zxqwerty Nonexistent Person")

        assert result is None

    @patch("epocha.apps.agents.research.requests.get")
    def test_handles_api_error_gracefully(self, mock_get):
        """Wikipedia search should return None on API errors."""
        mock_get.side_effect = Exception("Connection timeout")

        result = search_wikipedia("Lucrezia Borgia")

        assert result is None

    @patch("epocha.apps.agents.research.requests.get")
    def test_tries_english_fallback(self, mock_get):
        """If the first language returns no results, try English."""
        empty_response = MagicMock()
        empty_response.status_code = 200
        empty_response.json.return_value = {"pages": []}

        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "pages": [{"key": "Lucrezia_Borgia", "title": "Lucrezia Borgia"}]
        }

        summary_response = MagicMock()
        summary_response.status_code = 200
        summary_response.json.return_value = {
            "title": "Lucrezia Borgia",
            "extract": "Lucrezia Borgia was a noblewoman.",
        }

        mock_get.side_effect = [empty_response, search_response, summary_response]

        result = search_wikipedia("Lucrezia Borgia", language="it")

        assert result is not None


class TestSearchDuckDuckGo:
    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_biography_snippet(self, mock_get):
        """DuckDuckGo should return an abstract text for known people."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Abstract": "Lucrezia Borgia was a duchess and political pawn.",
            "RelatedTopics": [
                {"Text": "Known for alleged poisonings at the papal court."}
            ],
        }
        mock_get.return_value = mock_response

        result = search_duckduckgo("Lucrezia Borgia biography")

        assert result is not None
        assert "Borgia" in result

    @patch("epocha.apps.agents.research.requests.get")
    def test_returns_none_on_empty_result(self, mock_get):
        """DuckDuckGo should return None if no useful data found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Abstract": "", "RelatedTopics": []}
        mock_get.return_value = mock_response

        result = search_duckduckgo("Zxqwerty Nonexistent Person")

        assert result is None


class TestResearchPerson:
    @patch("epocha.apps.agents.research.search_duckduckgo")
    @patch("epocha.apps.agents.research.search_wikipedia")
    def test_uses_wikipedia_first(self, mock_wiki, mock_ddg):
        """research_person should prefer Wikipedia over DuckDuckGo."""
        mock_wiki.return_value = "Wikipedia bio text"

        result = research_person("Lucrezia Borgia")

        assert result == "Wikipedia bio text"
        mock_ddg.assert_not_called()

    @patch("epocha.apps.agents.research.search_duckduckgo")
    @patch("epocha.apps.agents.research.search_wikipedia")
    def test_falls_back_to_duckduckgo(self, mock_wiki, mock_ddg):
        """If Wikipedia returns nothing, fall back to DuckDuckGo."""
        mock_wiki.return_value = None
        mock_ddg.return_value = "DuckDuckGo bio text"

        result = research_person("Lucrezia Borgia")

        assert result == "DuckDuckGo bio text"

    @patch("epocha.apps.agents.research.search_duckduckgo")
    @patch("epocha.apps.agents.research.search_wikipedia")
    def test_returns_none_when_both_fail(self, mock_wiki, mock_ddg):
        """If both sources fail, return None."""
        mock_wiki.return_value = None
        mock_ddg.return_value = None

        result = research_person("Completely Unknown Person")

        assert result is None
