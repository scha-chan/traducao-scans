"""Gera contracts/page-export.schema.json a partir dos modelos Pydantic.

Uso:
    python -m contracts.generate
"""

import json
from pathlib import Path

from contracts.models import PageExport

_OUT = Path(__file__).parent / "page-export.schema.json"


def main() -> None:
    schema = PageExport.model_json_schema()
    _OUT.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Schema gerado em {_OUT}")


if __name__ == "__main__":
    main()
