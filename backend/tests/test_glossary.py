"""V2-BE-01: testes do CRUD de glossário."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_work(client: AsyncClient) -> dict:
    r = await client.post("/api/works", json={"title": "Test Work"})
    assert r.status_code == 201
    return r.json()


async def _create_folder(client: AsyncClient, work_id: str) -> dict:
    r = await client.post("/api/folders", json={"name": "Vol. 1", "work_id": work_id})
    assert r.status_code == 201
    return r.json()


class TestGlossaryCRUD:
    async def test_list_empty(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        r = await client.get(f"/api/works/{work['id']}/glossary")
        assert r.status_code == 200
        assert r.json() == []

    async def test_create_entry(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        r = await client.post(
            f"/api/works/{work['id']}/glossary",
            json={
                "source_term": "先生",
                "preferred_translation": "Sensei",
                "category": "honorífico",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["source_term"] == "先生"
        assert data["preferred_translation"] == "Sensei"
        assert data["work_id"] == work["id"]

    async def test_duplicate_term_conflict(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        await client.post(f"/api/works/{work['id']}/glossary", json={"source_term": "先生"})
        r = await client.post(f"/api/works/{work['id']}/glossary", json={"source_term": "先生"})
        assert r.status_code == 409

    async def test_get_entry(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        created = (
            await client.post(f"/api/works/{work['id']}/glossary", json={"source_term": "先生"})
        ).json()
        r = await client.get(f"/api/works/{work['id']}/glossary/{created['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    async def test_update_entry(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        created = (
            await client.post(f"/api/works/{work['id']}/glossary", json={"source_term": "先生"})
        ).json()
        r = await client.patch(
            f"/api/works/{work['id']}/glossary/{created['id']}",
            json={"preferred_translation": "Mestre"},
        )
        assert r.status_code == 200
        assert r.json()["preferred_translation"] == "Mestre"

    async def test_delete_entry(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        created = (
            await client.post(f"/api/works/{work['id']}/glossary", json={"source_term": "先生"})
        ).json()
        r = await client.delete(f"/api/works/{work['id']}/glossary/{created['id']}")
        assert r.status_code == 204
        r2 = await client.get(f"/api/works/{work['id']}/glossary/{created['id']}")
        assert r2.status_code == 404

    async def test_404_wrong_work(self, client: AsyncClient) -> None:
        work1 = await _create_work(client)
        work2 = await _create_work(client)
        created = (
            await client.post(f"/api/works/{work1['id']}/glossary", json={"source_term": "先生"})
        ).json()
        r = await client.get(f"/api/works/{work2['id']}/glossary/{created['id']}")
        assert r.status_code == 404

    async def test_list_ordered_alphabetically(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        for term in ["先生", "あ", "山田"]:
            await client.post(f"/api/works/{work['id']}/glossary", json={"source_term": term})
        r = await client.get(f"/api/works/{work['id']}/glossary")
        terms = [e["source_term"] for e in r.json()]
        assert terms == sorted(terms)

    async def test_search_by_term(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        await client.post(
            f"/api/works/{work['id']}/glossary",
            json={"source_term": "先生", "preferred_translation": "Sensei"},
        )
        await client.post(
            f"/api/works/{work['id']}/glossary",
            json={"source_term": "先輩", "preferred_translation": "Senpai"},
        )
        r = await client.get(f"/api/works/{work['id']}/glossary-search?q=先")
        assert r.status_code == 200
        assert len(r.json()) == 2

    async def test_search_by_translation(self, client: AsyncClient) -> None:
        work = await _create_work(client)
        await client.post(
            f"/api/works/{work['id']}/glossary",
            json={"source_term": "先生", "preferred_translation": "Sensei"},
        )
        r = await client.get(f"/api/works/{work['id']}/glossary-search?q=Sensei")
        assert r.status_code == 200
        assert len(r.json()) == 1
