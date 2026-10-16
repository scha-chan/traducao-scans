from app.db import Base, get_db
from app.db.engine import AsyncSessionLocal


def test_base_metadata_exists() -> None:
    assert Base.metadata is not None


def test_async_session_local_is_callable() -> None:
    assert callable(AsyncSessionLocal)


def test_get_db_is_async_generator() -> None:
    import inspect

    assert inspect.isasyncgenfunction(get_db)
