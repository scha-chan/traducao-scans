"""Validador de exportação — seção 22 do PRD.

Combina a validação estrutural do Pydantic com regras semânticas de lista
(ordem único e sequencial). Retorna uma lista de ValidationIssue; lista
vazia significa exportação válida.

Uso::

    from contracts.validator import validate_page_export

    issues = validate_page_export(data)
    if issues:
        for issue in issues:
            print(issue.field, issue.message)
"""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from contracts.models import PageExport


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


def validate_page_export(data: Any) -> list[ValidationIssue]:  # noqa: ANN401
    """Valida dados de exportação de página.

    Retorna lista de ValidationIssue (vazia = válido).
    """
    issues: list[ValidationIssue] = []

    # --- Validação estrutural via Pydantic ---
    try:
        page = PageExport.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            issues.append(ValidationIssue(field=loc or "root", message=err["msg"]))
        return issues

    if not page.root:
        return issues

    # --- Regras semânticas de lista (seção 22) ---
    ordens = [b.ordem for b in page.root]
    n = len(ordens)

    # ordem não repetido
    seen: set[int] = set()
    for i, ordem in enumerate(ordens):
        if ordem in seen:
            issues.append(
                ValidationIssue(
                    field=f"[{i}].ordem", message=f"ordem {ordem} está duplicado"
                )
            )
        seen.add(ordem)

    if issues:
        return issues

    # ordem sequencial de 1 a N sem lacunas
    expected = set(range(1, n + 1))
    actual = set(ordens)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        parts: list[str] = []
        if missing:
            parts.append(f"faltando: {missing}")
        if extra:
            parts.append(f"fora do intervalo 1–{n}: {extra}")
        issues.append(
            ValidationIssue(
                field="ordem",
                message=f"deve ser sequencial de 1 a {n}; {'; '.join(parts)}",
            )
        )

    return issues
