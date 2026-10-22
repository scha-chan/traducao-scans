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

## Estrutura de componentes Angular (frontend)

**Todo componente Angular deve ter três arquivos separados:**

```
meu-componente.component.ts
meu-componente.component.html
meu-componente.component.scss
```

**Regras:**

- Nunca use `template: \`...\`` inline no decorador `@Component`. Sempre use `templateUrl: './meu-componente.component.html'`.
- Nunca use `styles: [...]` ou `styleUrls` com CSS puro inline. Sempre use `styleUrl: './meu-componente.component.scss'` (singular, Angular 17+).
- No arquivo `.html`, evite estilos inline (`style="..."`). Prefira classes Tailwind ou classes definidas no `.scss`.
- Exceção permitida: utilitários puros sem template visual (services, guards, pipes simples) continuam em arquivo `.ts` único.
