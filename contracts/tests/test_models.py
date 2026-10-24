"""Testes dos modelos Pydantic do contrato de exportação."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.models import PageExport, TextBlockExport, TranslationSuggestionExport

_SUGGESTION = {
    "traducao": "Decidi!",
    "observacao": "よ dá tom enfático.",
    "relevancia": 1,
}
_BLOCK = {
    "ordem": 1,
    "tipo": "#",
    "original": "きめたよ!",
    "localizacao": "Topo direita",
    "traducoes": [_SUGGESTION],
}


# --- TranslationSuggestionExport ---


def test_suggestion_valid() -> None:
    s = TranslationSuggestionExport(**_SUGGESTION)
    assert s.relevancia == 1


def test_suggestion_relevancia_min() -> None:
    with pytest.raises(ValidationError):
        TranslationSuggestionExport(traducao="x", observacao="", relevancia=0)


def test_suggestion_relevancia_max() -> None:
    with pytest.raises(ValidationError):
        TranslationSuggestionExport(traducao="x", observacao="", relevancia=6)


# --- TextBlockExport ---


def test_block_valid_hash() -> None:
    b = TextBlockExport(**_BLOCK)
    assert b.tipo == "#"


def test_block_valid_dollar() -> None:
    b = TextBlockExport(**{**_BLOCK, "tipo": "$"})
    assert b.tipo == "$"


def test_block_tipo_invalido() -> None:
    with pytest.raises(ValidationError):
        TextBlockExport(**{**_BLOCK, "tipo": "X"})


def test_block_ordem_zero() -> None:
    with pytest.raises(ValidationError):
        TextBlockExport(**{**_BLOCK, "ordem": 0})


def test_block_traducoes_vazia() -> None:
    with pytest.raises(ValidationError):
        TextBlockExport(**{**_BLOCK, "traducoes": []})


def test_block_traducoes_mais_de_cinco() -> None:
    with pytest.raises(ValidationError):
        TextBlockExport(**{**_BLOCK, "traducoes": [_SUGGESTION] * 6})


# --- PageExport ---


def test_page_export_valido() -> None:
    page = PageExport.model_validate([_BLOCK])
    assert len(page.root) == 1
    assert page.root[0].ordem == 1


def test_page_export_vazia() -> None:
    page = PageExport.model_validate([])
    assert page.root == []


def test_page_export_json_roundtrip() -> None:
    page = PageExport.model_validate([_BLOCK])
    dumped = page.model_dump_json()
    restored = PageExport.model_validate_json(dumped)
    assert restored.root[0].original == "きめたよ!"


# --- Geração do schema ---


def test_schema_file_existe_e_e_valido_json() -> None:
    schema_path = Path(__file__).parent.parent / "page-export.schema.json"
    assert schema_path.exists(), "page-export.schema.json não foi gerado"
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert data["type"] == "array"
    assert "$defs" in data


def test_schema_consistente_com_modelo() -> None:
    schema_path = Path(__file__).parent.parent / "page-export.schema.json"
    on_disk = json.loads(schema_path.read_text(encoding="utf-8"))
    from_model = PageExport.model_json_schema()
    assert on_disk == from_model, (
        "page-export.schema.json está desatualizado. Rode: python -m contracts.generate"
    )
