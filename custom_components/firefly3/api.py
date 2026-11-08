"""Kleine async client voor de Firefly III API."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import aiohttp


class FireflyError(Exception):
    """Basisfout."""


class FireflyAuthError(FireflyError):
    """Token ongeldig of geen rechten."""


class FireflyConnectionError(FireflyError):
    """Firefly III niet bereikbaar of onverwacht antwoord."""


class FireflyApi:
    """Leest data uit Firefly III via /api/v1."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self._base = url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.api+json",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        try:
            async with asyncio.timeout(30):
                async with self._session.get(
                    f"{self._base}/api/v1{path}", headers=self._headers, params=params
                ) as resp:
                    if resp.status in (401, 403):
                        raise FireflyAuthError(f"HTTP {resp.status}")
                    if resp.status >= 400:
                        raise FireflyConnectionError(f"HTTP {resp.status} op {path}")
                    return await resp.json(content_type=None)
        except FireflyError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise FireflyConnectionError(str(err) or type(err).__name__) from err

    async def _get_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Haal alle pagina's op."""
        items: list[dict] = []
        page = 1
        while True:
            data = await self._get(path, {**(params or {}), "page": page, "limit": 100})
            items.extend(data.get("data", []))
            total = data.get("meta", {}).get("pagination", {}).get("total_pages", 1) or 1
            if page >= total:
                return items
            page += 1

    async def about(self) -> dict:
        return (await self._get("/about")).get("data", {})

    async def asset_accounts(self) -> list[dict]:
        items = await self._get_all("/accounts", {"type": "asset"})
        # extra vangnet: alleen echte betaal-/spaarrekeningen, geen
        # winkels/begunstigden (expense/revenue-rekeningen)
        return [i for i in items if i.get("attributes", {}).get("type") == "asset"]

    async def piggy_banks(self) -> list[dict]:
        return await self._get_all("/piggy-banks")

    async def bills(self, start: date, end: date) -> list[dict]:
        """Abonnementen (in de API nog 'bills') met pay_dates/paid_dates voor de periode."""
        return await self._get_all(
            "/bills", {"start": start.isoformat(), "end": end.isoformat()}
        )

    async def transaction_group(self, group_id: str) -> dict:
        return (await self._get(f"/transactions/{group_id}")).get("data", {})
