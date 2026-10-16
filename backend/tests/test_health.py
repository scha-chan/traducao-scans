from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_returns_ok() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_404_returns_error_envelope() -> None:
    r = client.get("/rota-inexistente")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["status"] == 404


def test_422_returns_error_envelope() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    tmp = FastAPI()

    class Body(BaseModel):
        name: str

    @tmp.post("/test")
    async def _endpoint(body: Body) -> dict[str, str]:
        return {"name": body.name}

    from fastapi.exceptions import RequestValidationError

    from app.errors import validation_exception_handler

    tmp.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

    c = TestClient(tmp, raise_server_exceptions=False)
    r = c.post("/test", json={})
    assert r.status_code == 422
    assert "error" in r.json()
