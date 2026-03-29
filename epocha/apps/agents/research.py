"""Biographical research via Wikipedia and web search.

Provides functions to look up information about historical, real, or
living persons. Used by the enrichment pipeline to build accurate
agent personality profiles.

Search strategy:
1. Wikipedia REST API (search + page summary)
2. DuckDuckGo Instant Answer API (fallback)

Both sources are free, require no API keys, and return structured data.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_WIKIPEDIA_SEARCH_URL = "https://{lang}.wikipedia.org/w/rest.php/v1/search/page"
_WIKIPEDIA_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
_DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"

_REQUEST_TIMEOUT = 10
_USER_AGENT = "Epocha/1.0 (civilization simulator; research for agent profiles)"

# Maximum length of biographical text to return (characters).
_MAX_BIO_LENGTH = 3000


def search_wikipedia(name: str, language: str = "en") -> str | None:
    """Search Wikipedia for a person and return their page summary.

    Tries the specified language first, then falls back to English.
    Returns the extract text or None if not found.

    Args:
        name: Full name of the person to search for.
        language: ISO 639-1 language code for the initial search.
    """
    headers = {"User-Agent": _USER_AGENT}

    languages = [language, "en"] if language != "en" else ["en"]

    for lang in languages:
        try:
            search_url = _WIKIPEDIA_SEARCH_URL.format(lang=lang)
            search_resp = requests.get(
                search_url,
                params={"q": name, "limit": 1},
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            search_resp.raise_for_status()
            pages = search_resp.json().get("pages", [])

            if not pages:
                continue

            page_key = pages[0]["key"]
            summary_url = _WIKIPEDIA_SUMMARY_URL.format(lang=lang, title=page_key)
            summary_resp = requests.get(
                summary_url,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            summary_resp.raise_for_status()
            extract = summary_resp.json().get("extract", "")

            if extract:
                logger.info("Wikipedia (%s) found bio for: %s", lang, name)
                return extract[:_MAX_BIO_LENGTH]

        except Exception:
            logger.warning("Wikipedia search failed for '%s' (lang=%s)", name, lang)

    return None


def search_duckduckgo(query: str) -> str | None:
    """Search DuckDuckGo Instant Answer API for biographical information.

    Returns the abstract and first few related topics as a single text,
    or None if no useful data is found.

    Args:
        query: Search query (typically "Name biography").
    """
    try:
        resp = requests.get(
            _DUCKDUCKGO_API_URL,
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers={"User-Agent": _USER_AGENT},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        parts = []
        abstract = data.get("Abstract", "")
        if abstract:
            parts.append(abstract)

        for topic in data.get("RelatedTopics", [])[:5]:
            text = topic.get("Text", "")
            if text:
                parts.append(text)

        if not parts:
            return None

        result = "\n".join(parts)
        logger.info("DuckDuckGo found bio for: %s", query)
        return result[:_MAX_BIO_LENGTH]

    except Exception:
        logger.warning("DuckDuckGo search failed for '%s'", query)
        return None


def research_person(name: str, language: str = "en") -> str | None:
    """Research a person using Wikipedia first, DuckDuckGo as fallback.

    Args:
        name: Full name of the person.
        language: Preferred Wikipedia language for the initial search.

    Returns:
        Biographical text or None if nothing found.
    """
    result = search_wikipedia(name, language=language)
    if result:
        return result

    return search_duckduckgo(f"{name} biography")
