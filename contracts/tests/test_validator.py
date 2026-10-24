"""Testes do validador de exportação — uma regra da seção 22 por teste."""

from typing import Any

import pytest

from contracts.validator import ValidationIssue, validate_page_export

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SUGG: dict[str, Any] = {"traducao": "Decidi!", "observacao": "obs.", "relevancia": 1}

_BLOCK: dict[str, Any] = {
    "ordem": 1,
    "tipo": "#",
    "original": "きめたよ!",
    "localizacao": "Topo direita",
    "traducoes": [_SUGG],
}


def _page(*overrides: dict[str, Any]) -> list[dict[str, Any]]:
    """Monta uma página com N blocos sequenciais, opcionalmente sobrescrevendo campos."""
    blocks = []
    for i, ov in enumerate(overrides, start=1):
        blocks.append({**_BLOCK, "ordem": i, **ov})
    return blocks


def _valid() -> list[dict[str, Any]]:
    return _page({}, {})


def _issues(data: Any) -> list[ValidationIssue]:
    return validate_page_export(data)


def _fields(data: Any) -> list[str]:
    return [i.field for i in _issues(data)]


# ---------------------------------------------------------------------------
# Raiz deve ser um array
# ---------------------------------------------------------------------------


def test_raiz_array_valido() -> None:
    assert _issues(_valid()) == []


def test_raiz_nao_array() -> None:
    issues = _issues({"ordem": 1})
    assert issues
    assert any("root" in i.field or i.field == "" for i in issues)


# ---------------------------------------------------------------------------
# ordem — inteiro positivo
# ---------------------------------------------------------------------------


def test_ordem_positivo_valido() -> None:
    assert _issues(_page({})) == []


def test_ordem_zero_invalido() -> None:
    assert _fields(_page({"ordem": 0}))


def test_ordem_negativo_invalido() -> None:
    assert _fields(_page({"ordem": -1}))


# ---------------------------------------------------------------------------
# ordem — não repetido
# ---------------------------------------------------------------------------


def test_ordem_duplicado() -> None:
    data = [_BLOCK, {**_BLOCK, "ordem": 1}]
    issues = _issues(data)
    assert any("duplicado" in i.message for i in issues)


def test_ordem_unico_valido() -> None:
    data = [_BLOCK, {**_BLOCK, "ordem": 2}]
    assert _issues(data) == []


# ---------------------------------------------------------------------------
# ordem — sequencial de 1 a N sem lacunas
# ---------------------------------------------------------------------------


def test_ordem_sequencial_valido() -> None:
    data = [_BLOCK, {**_BLOCK, "ordem": 2}, {**_BLOCK, "ordem": 3}]
    assert _issues(data) == []


def test_ordem_com_lacuna() -> None:
    data = [_BLOCK, {**_BLOCK, "ordem": 3}]
    issues = _issues(data)
    assert any("sequencial" in i.message for i in issues)
    assert any("faltando" in i.message for i in issues)


def test_ordem_fora_do_intervalo() -> None:
    data = [_BLOCK, {**_BLOCK, "ordem": 5}]
    issues = _issues(data)
    assert any("sequencial" in i.message for i in issues)


# ---------------------------------------------------------------------------
# tipo
# ---------------------------------------------------------------------------


def test_tipo_hash_valido() -> None:
    assert _issues(_page({"tipo": "#"})) == []


def test_tipo_dollar_valido() -> None:
    assert _issues(_page({"tipo": "$"})) == []


def test_tipo_invalido() -> None:
    assert _fields(_page({"tipo": "X"}))


# ---------------------------------------------------------------------------
# original
# ---------------------------------------------------------------------------


def test_original_presente_valido() -> None:
    assert _issues(_page({"original": "テキスト"})) == []


def test_original_nulo_invalido() -> None:
    assert _fields(_page({"original": None}))


def test_original_ausente_invalido() -> None:
    block = {k: v for k, v in {**_BLOCK, "ordem": 1}.items() if k != "original"}
    assert _fields([block])


# ---------------------------------------------------------------------------
# localizacao
# ---------------------------------------------------------------------------


def test_localizacao_presente_valido() -> None:
    assert _issues(_page({"localizacao": "Topo esquerda"})) == []


def test_localizacao_nula_invalida() -> None:
    assert _fields(_page({"localizacao": None}))


def test_localizacao_ausente_invalida() -> None:
    block = {k: v for k, v in {**_BLOCK, "ordem": 1}.items() if k != "localizacao"}
    assert _fields([block])


# ---------------------------------------------------------------------------
# traducoes — array com 1..5 itens
# ---------------------------------------------------------------------------


def test_traducoes_um_item_valido() -> None:
    assert _issues(_page({"traducoes": [_SUGG]})) == []


def test_traducoes_cinco_itens_valido() -> None:
    assert _issues(_page({"traducoes": [_SUGG] * 5})) == []


def test_traducoes_vazia_invalida() -> None:
    assert _fields(_page({"traducoes": []}))


def test_traducoes_seis_itens_invalida() -> None:
    assert _fields(_page({"traducoes": [_SUGG] * 6}))


def test_traducoes_ausente_invalida() -> None:
    block = {k: v for k, v in {**_BLOCK, "ordem": 1}.items() if k != "traducoes"}
    assert _fields([block])


# ---------------------------------------------------------------------------
# relevancia — inteiro de 1 a 5
# ---------------------------------------------------------------------------


def test_relevancia_1_valida() -> None:
    assert _issues(_page({"traducoes": [{**_SUGG, "relevancia": 1}]})) == []


def test_relevancia_5_valida() -> None:
    assert _issues(_page({"traducoes": [{**_SUGG, "relevancia": 5}]})) == []


def test_relevancia_zero_invalida() -> None:
    assert _fields(_page({"traducoes": [{**_SUGG, "relevancia": 0}]}))


def test_relevancia_seis_invalida() -> None:
    assert _fields(_page({"traducoes": [{**_SUGG, "relevancia": 6}]}))


# ---------------------------------------------------------------------------
# Mensagens de erro — campo identificado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data,expected_fragment",
    [
        (_page({"tipo": "X"}), "tipo"),
        (_page({"original": None}), "original"),
        (_page({"localizacao": None}), "localizacao"),
        (_page({"traducoes": []}), "traducoes"),
        (_page({"traducoes": [{**_SUGG, "relevancia": 0}]}), "relevancia"),
    ],
)
def test_mensagem_identifica_campo(
    data: list[dict[str, Any]], expected_fragment: str
) -> None:
    issues = _issues(data)
    assert issues, "esperava pelo menos um erro"
    assert any(expected_fragment in i.field for i in issues), (
        f"campo '{expected_fragment}' não identificado nas issues: {issues}"
    )
