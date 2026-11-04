"""Testes: transição automática APPROVED → REVIEW ao editar blocos (F6-BE-02)."""

import io

import pytest
from httpx import AsyncClient
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


_BLOCK_JSON = [
    {
        "ordem": 1,
        "tipo": "#",
        "original": "テスト",
        "localizacao": "Topo direita",
        "review_status": "PENDING",
        "source": "MANUAL",
        "traducoes": [{"traducao": "Teste", "observacao": "", "relevancia": 1, "source": "MANUAL"}],
    }
]


async def _setup_approved_page(client: AsyncClient) -> tuple[str, str, str]:
    """Cria pasta → página → bloco → aprova. Retorna (page_id, block_id, suggestion_id)."""
    r = await client.post("/api/folders", json={"name": "Vol. Test"})
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
    blocks = r.json()
    block_id = blocks[0]["id"]
    suggestion_id = blocks[0]["suggestions"][0]["id"]

    r = await client.post(f"/api/pages/{page_id}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"

    return page_id, block_id, suggestion_id


async def _get_status(client: AsyncClient, page_id: str) -> str:
    r = await client.get(f"/api/pages/{page_id}")
    assert r.status_code == 200
    return r.json()["status"]


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_block_resets_approved_to_review(client: AsyncClient) -> None:
    page_id, block_id, _ = await _setup_approved_page(client)

    r = await client.patch(f"/api/blocks/{block_id}", json={"original": "変更"})
    assert r.status_code == 200

    assert await _get_status(client, page_id) == "REVIEW"


@pytest.mark.asyncio
async def test_create_suggestion_resets_approved_to_review(client: AsyncClient) -> None:
    page_id, block_id, _ = await _setup_approved_page(client)

    r = await client.post(
        f"/api/blocks/{block_id}/suggestions",
        json={"traducao": "Nova sugestão", "observacao": "", "relevancia": 2},
    )
    assert r.status_code == 201

    assert await _get_status(client, page_id) == "REVIEW"


@pytest.mark.asyncio
async def test_update_suggestion_resets_approved_to_review(client: AsyncClient) -> None:
    page_id, block_id, suggestion_id = await _setup_approved_page(client)

    r = await client.patch(
        f"/api/blocks/{block_id}/suggestions/{suggestion_id}",
        json={"traducao": "Tradução editada"},
    )
    assert r.status_code == 200

    assert await _get_status(client, page_id) == "REVIEW"


@pytest.mark.asyncio
async def test_delete_suggestion_resets_approved_to_review(client: AsyncClient) -> None:
    page_id, block_id, suggestion_id = await _setup_approved_page(client)

    # Adiciona segunda sugestão para poder deletar sem violar a constraint de mínimo 1
    r = await client.post(
        f"/api/blocks/{block_id}/suggestions",
        json={"traducao": "Segunda", "observacao": "", "relevancia": 2},
    )
    assert r.status_code == 201

    # Reapprova para garantir estado APPROVED antes do delete
    r = await client.post(f"/api/pages/{page_id}/approve")
    assert r.status_code == 200

    r = await client.delete(f"/api/blocks/{block_id}/suggestions/{suggestion_id}")
    assert r.status_code == 204

    assert await _get_status(client, page_id) == "REVIEW"


@pytest.mark.asyncio
async def test_reorder_blocks_resets_approved_to_review(client: AsyncClient) -> None:
    page_id, block_id, _ = await _setup_approved_page(client)

    r = await client.put(
        f"/api/pages/{page_id}/blocks/order",
        json={"block_ids": [block_id]},
    )
    assert r.status_code == 200

    assert await _get_status(client, page_id) == "REVIEW"


@pytest.mark.asyncio
async def test_patch_block_non_approved_page_keeps_status(client: AsyncClient) -> None:
    """Editar bloco de página não-APPROVED não altera o status."""
    r = await client.post("/api/folders", json={"name": "Vol. Keep"})
    folder_id = r.json()["id"]

    r = await client.post(
        f"/api/folders/{folder_id}/pages",
        files=[("files", ("p1.png", _png(), "image/png"))],
    )
    page_id = r.json()[0]["id"]

    r = await client.put(f"/api/pages/{page_id}/json", json=_BLOCK_JSON)
    assert r.status_code == 200

    r = await client.get(f"/api/pages/{page_id}/blocks")
    block_id = r.json()[0]["id"]

    original_status = await _get_status(client, page_id)
    assert original_status != "APPROVED"

    r = await client.patch(f"/api/blocks/{block_id}", json={"original": "変更"})
    assert r.status_code == 200

    assert await _get_status(client, page_id) == original_status
