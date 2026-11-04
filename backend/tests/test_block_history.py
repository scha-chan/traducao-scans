"""Tests for GET /blocks/{id}/history (V2-BE-03)."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from PIL import Image


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


_BLOCK_JSON = [
    {
        "ordem": 1,
        "tipo": "#",
        "original": "元のテキスト",
        "localizacao": "Topo",
        "review_status": "PENDING",
        "source": "MANUAL",
        "traducoes": [
            {"traducao": "Texto original", "observacao": "", "relevancia": 1, "source": "MANUAL"}
        ],
    }
]


async def _setup(client: AsyncClient) -> tuple[str, str]:
    """Create folder → page → block. Returns (page_id, block_id)."""
    r = await client.post("/api/folders", json={"name": "History Test"})
    assert r.status_code == 201
    folder_id = r.json()["id"]

    r = await client.post(
        f"/api/folders/{folder_id}/pages",
        files=[("files", ("page.png", _png(), "image/png"))],
    )
    assert r.status_code == 201
    page_id = r.json()[0]["id"]

    r = await client.put(f"/api/pages/{page_id}/json", json=_BLOCK_JSON)
    assert r.status_code == 200

    r = await client.get(f"/api/pages/{page_id}/blocks")
    assert r.status_code == 200
    block_id = r.json()[0]["id"]

    return page_id, block_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_empty_on_new_block(client: AsyncClient) -> None:
    _, block_id = await _setup(client)
    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_history_records_edit(client: AsyncClient) -> None:
    _, block_id = await _setup(client)

    r = await client.patch(f"/api/blocks/{block_id}", json={"original": "テスト"})
    assert r.status_code == 200

    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 1
    assert history[0]["change_type"] == "EDITED"
    assert history[0]["block_id"] == block_id


@pytest.mark.asyncio
async def test_history_edit_stores_previous_original(client: AsyncClient) -> None:
    _, block_id = await _setup(client)

    r = await client.patch(f"/api/blocks/{block_id}", json={"original": "新しいテキスト"})
    assert r.status_code == 200

    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 1
    # snapshot taken before the edit, so original is the value at time of recording
    assert history[0]["original"] == "元のテキスト"


@pytest.mark.asyncio
async def test_history_records_toggle(client: AsyncClient) -> None:
    # PUT /json creates blocks as REVIEWED; first toggle produces UNREVIEW
    _, block_id = await _setup(client)

    r = await client.post(f"/api/blocks/{block_id}/toggle-reviewed")
    assert r.status_code == 200

    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 1
    assert history[0]["change_type"] in {"REVIEWED", "UNREVIEW"}


@pytest.mark.asyncio
async def test_history_records_two_toggles(client: AsyncClient) -> None:
    # _BLOCK_JSON creates block as PENDING; two toggles: REVIEWED then UNREVIEW
    _, block_id = await _setup(client)

    await client.post(f"/api/blocks/{block_id}/toggle-reviewed")  # PENDING→REVIEWED (REVIEWED)
    await client.post(f"/api/blocks/{block_id}/toggle-reviewed")  # REVIEWED→PENDING (UNREVIEW)

    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 2
    # newest first
    assert history[0]["change_type"] == "UNREVIEW"
    assert history[1]["change_type"] == "REVIEWED"


@pytest.mark.asyncio
async def test_history_multiple_edits_newest_first(client: AsyncClient) -> None:
    _, block_id = await _setup(client)

    await client.patch(f"/api/blocks/{block_id}", json={"original": "最初"})
    await client.patch(f"/api/blocks/{block_id}", json={"original": "二回目"})

    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 2
    assert all(h["change_type"] == "EDITED" for h in history)
    # changed_at should be non-decreasing in reverse (newest is [0])
    assert history[0]["changed_at"] >= history[1]["changed_at"]


@pytest.mark.asyncio
async def test_history_mixed_operations(client: AsyncClient) -> None:
    _, block_id = await _setup(client)

    await client.patch(f"/api/blocks/{block_id}", json={"original": "編集済み"})
    await client.post(f"/api/blocks/{block_id}/toggle-reviewed")

    r = await client.get(f"/api/blocks/{block_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 2
    types = {h["change_type"] for h in history}
    assert "EDITED" in types
    assert len(types - {"EDITED"}) == 1  # one toggle type


@pytest.mark.asyncio
async def test_history_404_unknown_block(client: AsyncClient) -> None:
    r = await client.get("/api/blocks/00000000-0000-0000-0000-000000000000/history")
    assert r.status_code == 404
