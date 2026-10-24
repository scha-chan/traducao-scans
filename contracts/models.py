"""Contrato de exportação de uma página — única fonte da verdade.

Gera ``contracts/page-export.schema.json`` via ``python -m contracts.generate``.
O frontend deriva os tipos TypeScript a partir desse schema.
"""

from typing import Literal

from pydantic import BaseModel, Field, RootModel


class TranslationSuggestionExport(BaseModel):
    """Uma sugestão de tradução para um bloco de texto."""

    traducao: str
    observacao: str
    relevancia: int = Field(ge=1, le=5)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "traducao": "Decidi!",
                    "observacao": "よ dá tom de anúncio.",
                    "relevancia": 1,
                }
            ]
        }
    }


class TextBlockExport(BaseModel):
    """Um bloco de texto detectado na página."""

    ordem: int = Field(ge=1, description="Posição na ordem de leitura, a partir de 1.")
    tipo: Literal["#", "$"]
    original: str
    localizacao: str
    traducoes: list[TranslationSuggestionExport] = Field(min_length=1, max_length=5)


PageExport = RootModel[list[TextBlockExport]]
