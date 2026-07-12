"""Linkup web search provider for Hermes.

Modeled on the bundled Tavily plugin (plugins/web/tavily/provider.py).
Search-only (``supports_extract() -> False``); extract falls through to
whatever ``web.backend`` names (ddgs by default).

Config wiring (done by scripts/setup-hermes-search-voice.sh)::

    web:
      search_backend: "linkup"
    plugins:
      enabled: [web-linkup]

Env vars::

    LINKUP_API_KEY=...      # https://app.linkup.so — required for Linkup itself
    LINKUP_BASE_URL=...     # optional override of https://api.linkup.so

Graceful degradation: while LINKUP_API_KEY is unset, ``search()`` delegates
to the registered ``ddgs`` provider instead of erroring, so web search keeps
working and flips to Linkup the moment the key lands in ~/.hermes/.env
(gateway restart required — env is read at call time but the plugin loads at
startup).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider, get_provider_env

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.linkup.so"


def _linkup_search_request(query: str, limit: int) -> Dict[str, Any]:
    import httpx

    api_key = get_provider_env("LINKUP_API_KEY")
    if not api_key:
        raise ValueError(
            "LINKUP_API_KEY environment variable not set. "
            "Get a key at https://app.linkup.so"
        )
    base_url = get_provider_env("LINKUP_BASE_URL") or DEFAULT_BASE_URL
    response = httpx.post(
        f"{base_url}/v1/search",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "q": query,
            "depth": "standard",
            "outputType": "searchResults",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _normalize_results(response: Dict[str, Any], limit: int) -> Dict[str, Any]:
    """Map Linkup searchResults to Hermes' ``{success, data: {web: [...]}}``."""
    web_results: List[Dict[str, Any]] = []
    for i, result in enumerate(response.get("results", [])[:limit]):
        web_results.append(
            {
                "title": result.get("name", "") or result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("content", ""),
                "position": i + 1,
            }
        )
    return {"success": True, "data": {"web": web_results}}


class LinkupWebSearchProvider(WebSearchProvider):
    @property
    def name(self) -> str:
        return "linkup"

    @property
    def display_name(self) -> str:
        return "Linkup"

    def is_available(self) -> bool:
        return bool(get_provider_env("LINKUP_API_KEY"))

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def _fallback_search(self, query: str, limit: int) -> Dict[str, Any]:
        """No LINKUP_API_KEY yet — keep search alive via the bundled ddgs provider."""
        try:
            from agent.web_search_registry import get_provider

            ddgs = get_provider("ddgs")
            if ddgs is not None and ddgs.is_available():
                logger.info("LINKUP_API_KEY unset; falling back to ddgs for: %s", query)
                return ddgs.search(query, limit=limit)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ddgs fallback unavailable: %s", exc)
        return {
            "success": False,
            "error": "LINKUP_API_KEY not set and no ddgs fallback available. "
            "Add LINKUP_API_KEY to ~/.hermes/.env (https://app.linkup.so).",
        }

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return {"success": False, "error": "Interrupted"}
        except Exception:  # noqa: BLE001 — interrupt helper optional
            pass

        if not self.is_available():
            return self._fallback_search(query, limit)

        try:
            logger.info("Linkup search: '%s' (limit=%d)", query, limit)
            raw = _linkup_search_request(query, limit)
            return _normalize_results(raw, limit)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — including httpx errors
            logger.warning("Linkup search error: %s", exc)
            return {"success": False, "error": f"Linkup search failed: {exc}"}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        return [
            {"url": u, "title": "", "content": "", "error": "Linkup provider is search-only"}
            for u in urls
        ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Linkup",
            "badge": "paid",
            "tag": "Linkup grounded web search (search-only).",
            "env_vars": [
                {
                    "key": "LINKUP_API_KEY",
                    "prompt": "Linkup API key",
                    "url": "https://app.linkup.so",
                },
            ],
        }
