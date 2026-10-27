"""Testes de CRUD de pastas."""

import pytest
from httpx import AsyncClient


async def _create(client: AsyncClient, name: str = "Vol. 1") -> dict:
    r = await client.post("/api/folders", json={"name": name})
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient) -> None:
    r = await client.get("/api/folders")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create(client: AsyncClient) -> None:
    data = await _create(client, "Vol. 1")
    assert data["name"] == "Vol. 1"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_returns_409(client: AsyncClient) -> None:
    await _create(client, "Vol. 1")
    r = await client.post("/api/folders", json={"name": "Vol. 1"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_get(client: AsyncClient) -> None:
    created = await _create(client)
    r = await client.get(f"/api/folders/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/folders/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rename(client: AsyncClient) -> None:
    created = await _create(client, "Vol. 1")
    r = await client.patch(f"/api/folders/{created['id']}", json={"name": "Volume 1"})
    assert r.status_code == 200
    assert r.json()["name"] == "Volume 1"


@pytest.mark.asyncio
async def test_rename_to_existing_name_returns_409(client: AsyncClient) -> None:
    await _create(client, "Vol. 1")
    created2 = await _create(client, "Vol. 2")
    r = await client.patch(f"/api/folders/{created2['id']}", json={"name": "Vol. 1"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete(client: AsyncClient) -> None:
    created = await _create(client)
    r = await client.delete(f"/api/folders/{created['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/folders/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_list_after_create(client: AsyncClient) -> None:
    await _create(client, "Vol. 1")
    await _create(client, "Vol. 2")
    r = await client.get("/api/folders")
    assert r.status_code == 200
    names = {f["name"] for f in r.json()}
    assert names == {"Vol. 1", "Vol. 2"}
