"""Tests for POST /folders/{id}/batch-process (V2-BE-02)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


async def _create_folder(client: AsyncClient) -> dict:
    r = await client.post("/api/folders", json={"name": "Cap. 1"})
    assert r.status_code == 201
    return r.json()


async def _upload_page(client: AsyncClient, folder_id: str, page_number: int = 1) -> dict:
    png = _png()
    r = await client.post(
        f"/api/folders/{folder_id}/pages",
        files=[("files", ("page.png", png, "image/png"))],
    )
    assert r.status_code == 201
    pages = r.json()
    return pages[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_process_empty_folder(client: AsyncClient) -> None:
    folder = await _create_folder(client)
    r = await client.post(f"/api/folders/{folder['id']}/batch-process", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["succeeded"] == 0
    assert data["failed"] == 0
    assert data["results"] == []


@pytest.mark.asyncio
async def test_batch_process_404_unknown_folder(client: AsyncClient) -> None:
    r = await client.post(f"/api/folders/{uuid4()}/batch-process", json={})
    assert r.status_code == 404


def _patch_processing():
    """Context manager that mocks queue.get_pool so no Redis is needed."""
    return patch("app.api.folders.queue.get_pool", new_callable=AsyncMock, return_value=None)


@pytest.mark.asyncio
async def test_batch_process_all_pending_pages(client: AsyncClient) -> None:
    folder = await _create_folder(client)
    page = await _upload_page(client, folder["id"])

    with (
        _patch_processing(),
        patch(
            "app.api.folders._dispatch_and_wait",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        r = await client.post(f"/api/folders/{folder['id']}/batch-process", json={})

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0
    assert data["results"][0]["page_id"] == page["id"]
    assert data["results"][0]["success"] is True


@pytest.mark.asyncio
async def test_batch_process_specific_page_ids(client: AsyncClient) -> None:
    folder = await _create_folder(client)
    page1 = await _upload_page(client, folder["id"], page_number=1)
    page2 = await _upload_page(client, folder["id"], page_number=2)

    with (
        _patch_processing(),
        patch(
            "app.api.folders._dispatch_and_wait",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        r = await client.post(
            f"/api/folders/{folder['id']}/batch-process",
            json={"page_ids": [page1["id"]]},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    ids = [res["page_id"] for res in data["results"]]
    assert page1["id"] in ids
    assert page2["id"] not in ids


@pytest.mark.asyncio
async def test_batch_process_records_failed_pages(client: AsyncClient) -> None:
    folder = await _create_folder(client)
    await _upload_page(client, folder["id"])

    with (
        _patch_processing(),
        patch(
            "app.api.folders._dispatch_and_wait",
            new_callable=AsyncMock,
            side_effect=RuntimeError("OCR failed"),
        ),
    ):
        r = await client.post(f"/api/folders/{folder['id']}/batch-process", json={})

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["succeeded"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["success"] is False
    assert "OCR failed" in data["results"][0]["error"]


@pytest.mark.asyncio
async def test_batch_process_concurrency_validation(client: AsyncClient) -> None:
    folder = await _create_folder(client)
    r = await client.post(f"/api/folders/{folder['id']}/batch-process", json={"concurrency": 0})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_batch_process_concurrency_max_validation(client: AsyncClient) -> None:
    folder = await _create_folder(client)
    r = await client.post(f"/api/folders/{folder['id']}/batch-process", json={"concurrency": 9})
    assert r.status_code == 422
