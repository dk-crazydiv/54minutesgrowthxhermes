"""Linkup web search plugin — user-installed (see docs/hermes/search-and-voice.md)."""

from __future__ import annotations

from .provider import LinkupWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(LinkupWebSearchProvider())
