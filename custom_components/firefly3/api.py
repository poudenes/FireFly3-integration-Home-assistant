"""Kleine async client voor de Firefly III REST API (alleen lezen)."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import aiohttp

ACCOUNT_TYPES = ("asset", "liabilities")
PAGE_LIMIT = 100
TIMEOUT = 30


class FireflyError(Exception):
    """Algemene fout bij het praten met Firefly III."""


class FireflyConnectionError(FireflyError):
    """Firefly III is niet bereikbaar of gaf een onverwacht antwoord."""


class FireflyAuthError(FireflyError):
    """Het access token is ongeldig of verlopen."""


def normalize_url(url: str) -> str:
    """Maak van wat de gebruiker invult een nette basis-URL."""
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    for suffix in ("/api/v1", "/api"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url.rstrip("/")


class FireflyClient:
    """Leest rekeningen, spaarpotjes en abonnementen (bills) uit Firefly III."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self.base_url = normalize_url(url)
        self._token = token.strip()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.api+json",
        }
        url = f"{self.base_url}/api/v1{path}"
        try:
            async with asyncio.timeout(TIMEOUT):
                async with self._session.get(
                    url, headers=headers, params=params, allow_redirects=False
                ) as resp:
                    if resp.status in (401, 403):
                        raise FireflyAuthError(f"HTTP {resp.status}")
                    if 300 <= resp.status < 400:
                        # Firefly stuurt zonder geldige auth soms door naar /login
                        raise FireflyAuthError(f"Redirect ({resp.status}) naar inlogpagina")
                    if resp.status >= 400:
                        raise FireflyConnectionError(f"HTTP {resp.status} op {path}")
                    try:
                        return await resp.json(content_type=None)
                    except ValueError as err:
                        raise FireflyConnectionError(
                            "Antwoord is geen JSON; klopt de URL?"
                        ) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FireflyConnectionError(str(err) or type(err).__name__) from err

    async def _get_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Haal alle pagina's van een lijst-endpoint op."""
        items: list[dict] = []
        page = 1
        while True:
            query = {**(params or {}), "page": page, "limit": PAGE_LIMIT}
            body = await self._get(path, query)
            items.extend(body.get("data") or [])
            pagination = (body.get("meta") or {}).get("pagination") or {}
            total_pages = int(pagination.get("total_pages") or 1)
            if page >= total_pages:
                return items
            page += 1

    @staticmethod
    def _by_id(items: list[dict], **extra: Any) -> dict[str, dict[str, Any]]:
        return {
            str(item["id"]): {**(item.get("attributes") or {}), **extra}
            for item in items
            if "id" in item
        }

    async def about(self) -> dict[str, Any]:
        """Controleer de verbinding en het token. Geeft versie + gebruiker terug."""
        about = await self._get("/about")
        user = await self._get("/about/user")
        return {
            "version": (about.get("data") or {}).get("version"),
            "api_version": (about.get("data") or {}).get("api_version"),
            "email": ((user.get("data") or {}).get("attributes") or {}).get("email"),
        }

    async def accounts(self) -> dict[str, dict[str, Any]]:
        """Betaal-/spaarrekeningen (asset) en schulden (liabilities)."""
        result: dict[str, dict[str, Any]] = {}
        for acc_type in ACCOUNT_TYPES:
            items = await self._get_all("/accounts", {"type": acc_type})
            result.update(self._by_id(items))
        return result

    async def piggy_banks(self) -> dict[str, dict[str, Any]]:
        """Alle spaarpotjes."""
        return self._by_id(await self._get_all("/piggy-banks"))

    async def bills(self) -> dict[str, dict[str, Any]]:
        """Alle abonnementen (in de API heten ze 'bills').

        Met start/end berekent Firefly de volgende verwachte betaling.
        """
        today = date.today()
        params = {
            "start": today.isoformat(),
            "end": (today + timedelta(days=366)).isoformat(),
        }
        return self._by_id(await self._get_all("/bills", params))
