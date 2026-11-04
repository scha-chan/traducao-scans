"""Testes: toggle de review_status do bloco (F6-FE-02 — endpoint backend)."""

import io

import pytest
from httpx import AsyncClient
from PIL import Image


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


_BLOCK_JSON = [
    {
        "ordem": 1,
        "tipo": "#",
        "original": "テスト",
        "localizacao": "Topo",
        "review_status": "PENDING",
        "source": "MANUAL",
        "traducoes": [{"traducao": "Teste", "observacao": "", "relevancia": 1, "source": "MANUAL"}],
    }
]


async def _setup_page_with_block(client: AsyncClient) -> tuple[str, str]:
    """Cria pasta → página → bloco. Retorna (page_id, block_id)."""
    r = await client.post("/api/folders", json={"name": "Vol. Toggle"})
    assert r.status_code == 201
    folder_id = r.json()["id"]

    r = await client.post(
        f"/api/folders/{folder_id}/pages",
        files=[("files", ("p1.png", _png(), "image/png"))],
    )
    assert r.status_code == 201
    page_id = r.json()[0]["id"]

    r = await client.put(f"/api/pages/{page_id}/json", json=_BLOCK_JSON)
    assert r.status_code == 200

    r = await client.get(f"/api/pages/{page_id}/blocks")
    assert r.status_code == 200
    block_id = r.json()[0]["id"]

    return page_id, block_id


@pytest.mark.asyncio
async def test_toggle_reviewed_once(client: AsyncClient) -> None:
    """Primeira chamada inverte o status (save_page_json cria blocos como REVIEWED)."""
    _, block_id = await _setup_page_with_block(client)

    initial_status = (await client.get(f"/api/blocks/{block_id}")).json()["review_status"]

    r = await client.post(f"/api/blocks/{block_id}/toggle-reviewed")
    assert r.status_code == 200
    expected = "PENDING" if initial_status == "REVIEWED" else "REVIEWED"
    assert r.json()["review_status"] == expected


@pytest.mark.asyncio
async def test_toggle_reviewed_twice_restores_initial(client: AsyncClient) -> None:
    _, block_id = await _setup_page_with_block(client)

    initial_status = (await client.get(f"/api/blocks/{block_id}")).json()["review_status"]
    await client.post(f"/api/blocks/{block_id}/toggle-reviewed")
    r = await client.post(f"/api/blocks/{block_id}/toggle-reviewed")
    assert r.status_code == 200
    assert r.json()["review_status"] == initial_status


@pytest.mark.asyncio
async def test_toggle_reviewed_404(client: AsyncClient) -> None:
    from uuid import uuid4

    r = await client.post(f"/api/blocks/{uuid4()}/toggle-reviewed")
    assert r.status_code == 404
