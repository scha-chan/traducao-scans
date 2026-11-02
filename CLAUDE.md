# Instruções para Claude Code

## Board do projeto

O board de acompanhamento fica no projeto GitHub **"Especificação"** (id `PVT_kwHOAViRX84Bkl56`, owner `scha-chan`).

### IDs dos status

| Status      | option-id    |
|-------------|--------------|
| Backlog     | `f75ad846`   |
| Ready       | `61e4505c`   |
| In progress | `47fc9ee4`   |
| In review   | `df73e18b`   |
| Done        | `98236657`   |

Campo Status: `PVTSSF_lAHOAViRX84Bkl56zhjV9TE`

### Regra obrigatória

**Sempre que declarar que um card mudou de status** (iniciado, em revisão, concluído etc.), execute imediatamente o comando abaixo antes de encerrar o turno:

```bash
gh project item-edit \
  --project-id PVT_kwHOAViRX84Bkl56 \
  --id <PVTI_...> \
  --field-id PVTSSF_lAHOAViRX84Bkl56zhjV9TE \
  --single-select-option-id <option-id>
```

Para descobrir o `--id` do item, use:

```bash
gh project item-list 3 --owner scha-chan --format json \
  | python -X utf8 -c "import sys,json; [print(i['id'],'|',i['title']) for i in json.load(sys.stdin)['items'] if 'CARD' in i['title']]"
```

Substitua `'CARD'` pelo identificador do card (ex.: `'F1-FE-01'`).

## Regras de tipagem Python (mypy strict)

### `str | None or str` não estreita para `str`

Quando um parâmetro é `str | None` e há um fallback via `or`, o mypy **não** infere o resultado como `str` automaticamente. Sempre anote explicitamente:

```python
# ❌ mypy infere str | None → erro em funções que esperam str
self._model = model_arg or os.environ.get("MODEL", _DEFAULT)

# ✅ anotação explícita resolve
self._model: str = model_arg or os.environ.get("MODEL", _DEFAULT)
# ou como variável local:
model: str = model_arg or os.environ.get("MODEL", _DEFAULT)
```

Isso se aplica a qualquer expressão `X or Y` onde `X` é `T | None` e `Y` é `T` — o resultado é `T`, mas o mypy não estreita sem a anotação.

### `Any` em parâmetros de método (ANN401)

O ruff/flake8 bloqueia `typing.Any` em assinaturas de métodos públicos ou protegidos via a regra `ANN401`. Para parâmetros internos com tipos dinâmicos (ex.: objetos de bibliotecas não tipadas), use `# noqa: ANN401` na linha:

```python
def _run(self, tok: Any, mod: Any, text: str) -> str:  # noqa: ANN401
```

### Tipos dinâmicos de bibliotecas externas não tipadas

Ao armazenar objetos de bibliotecas sem stubs (ex.: `transformers`, `manga_ocr`), use `Any` com anotação explícita em vez de `object` — `object` impede chamadas de método e força `type: ignore` em cada uso:

```python
# ❌ object não permite .generate(), .decode() etc.
self._model: object = SomeLib.from_pretrained(name)

# ✅ Any permite chamadas sem ignore por linha
self._model: Any = SomeLib.from_pretrained(name)
```
