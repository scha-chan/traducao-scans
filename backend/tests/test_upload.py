"""Testes de upload de páginas."""

import pytest
from httpx import AsyncClient


async def _create_folder(client: AsyncClient, name: str = "Vol. 1") -> str:
    r = await client.post("/api/folders", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_upload_valid_png(client: AsyncClient, png_bytes: bytes) -> None:
    fid = await _create_folder(client)
    r = await client.post(
        f"/api/folders/{fid}/pages",
        files=[("files", ("page1.png", png_bytes, "image/png"))],
    )
    assert r.status_code == 201
    pages = r.json()
    assert len(pages) == 1
    assert pages[0]["file_name"] == "page1.png"
    assert pages[0]["page_number"] == 1


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient) -> None:
    fid = await _create_folder(client)
    r = await client.post(
        f"/api/folders/{fid}/pages",
        files=[("files", ("doc.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_non_image_with_png_extension(client: AsyncClient) -> None:
    fid = await _create_folder(client)
    r = await client.post(
        f"/api/folders/{fid}/pages",
        files=[("files", ("fake.png", b"not an image at all", "image/png"))],
    )
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_multiple_pages_sequential_numbers(
    client: AsyncClient, png_bytes: bytes
) -> None:
    fid = await _create_folder(client)
    r = await client.post(
        f"/api/folders/{fid}/pages",
        files=[
            ("files", ("p1.png", png_bytes, "image/png")),
            ("files", ("p2.png", png_bytes, "image/png")),
            ("files", ("p3.png", png_bytes, "image/png")),
        ],
    )
    assert r.status_code == 201
    pages = r.json()
    assert len(pages) == 3
    numbers = sorted(p["page_number"] for p in pages)
    assert numbers == [1, 2, 3]


@pytest.mark.asyncio
async def test_upload_folder_not_found(client: AsyncClient, png_bytes: bytes) -> None:
    r = await client.post(
        "/api/folders/00000000-0000-0000-0000-000000000000/pages",
        files=[("files", ("p1.png", png_bytes, "image/png"))],
    )
    assert r.status_code == 404
