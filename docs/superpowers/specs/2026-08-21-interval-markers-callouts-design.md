# Durações de intervalo dentro dos callouts de Horários

## Objetivo

Substituir o bloco dinâmico `<!-- aw:start-intervalos -->`...`<!-- aw:end-intervalos -->` (callout gerado pelo sync) por atualização cirúrgica de durações **dentro** dos callouts já existentes na seção `## ⏰ Horários`, preservando queries dataview e conteúdo manual. Métricas sem callout correspondente (Pausa Longa / Pausa Curta) ganham dois callouts novos lado a lado no skeleton estático da seção.

## Contexto

- Hoje `format_intervalos_block` (src/handlers/formatter.py) gera um bloco inteiro e `_merge_body_block` substitui tudo entre os marcadores — apaga qualquer edição manual feita ali.
- Callouts de Horários no template `Nota Diária 2_ISO.md` mostram horários via dataview lendo frontmatter (`alimentacao[0..2]`, etc.). Nenhum tem marcação AW hoje.
- 6 métricas fora-do-PC vindas do fetch (`IntervaloEntry`): Pausa Longa, Pausa Rápida, Café da manhã, Almoço, Jantar, Exercícios.
- Vault `G:\Lucas` é repositório git → migração reversível; sem necessidade de `.bak`.
- 170 notas diárias em `G:\Lucas\01_Arquivos\Jornada`; 4 têm `aw:start-intervalos`; 167 têm os callouts-alvo + seção Eventos. Notas estruturalmente diferentes: `2026-03-31.md`, `2026-05-03.md`, `2026-07-29.md`.

## Mapeamento métrica → marcador → alvo

| Rótulo AW (`IntervaloEntry.rotulo`) | Slug marcador | Callout alvo | Posição |
|---|---|---|---|
| Café da manhã | `café` | `[!alimentacao-fato] Café` | inline, fim da linha da query |
| Almoço | `almoço` | `[!alimentacao-fato] Almoço` | inline, fim da linha da query |
| Jantar | `jantar` | `[!alimentacao-fato] Jantar` | inline, fim da linha da query |
| Exercícios | `exercícios` | `[!exercicios-fato] Exercícios` | inline, fim da linha da query |
| Pausa Longa | `pausa-longa` | `[!sumário]+ Pausa Longa` | linha própria no skeleton |
| Pausa Rápida | `pausa-curta` | `[!sumário]+ Pausa Curta` | linha própria no skeleton |

Nota: rótulo interno "Pausa Rápida" vira "Pausa Curta" só no texto visível/marcador; fetch não muda.

## Formato na nota

### Callouts existentes (query intocada, marcadores anexados)

```markdown
>> [!alimentacao-fato] Café
>> `$= dv.current().alimentacao?.[0] ? dv.luxon.DateTime.fromISO(dv.current().alimentacao[0], { zone: "utc" }).toLocal().toFormat("HH:mm") : "—" ` <!-- café-start --><!-- café-end -->
```

- Com dados do dia: interior = `· {duração}` → `<!-- café-start -->· 31m<!-- café-end -->`.
- Sem dados (≤0s ou AW offline): interior vazio → nada renderiza além da query.
- Duração em formato `seconds_to_display` (`31m`, `2h15`).

### Skeleton novo (posição atual do bloco, estático)

```markdown
<div style="margin-bottom: 40px;"></div>

<!-- aw:start-intervalos -->

> [!multi-column]
>> [!sumário]+  Pausa Longa 
>> <!-- pausa-longa-start --><!-- pausa-longa-end -->
>>
>
>> [!sumário]+  Pausa Curta
>> <!-- pausa-curta-start --><!-- pausa-curta-end -->
>>

<!-- aw:end-intervalos -->

<div style="margin-bottom: 20px;"></div>
```

- `aw:start-intervalos` / `aw:end-intervalos` permanecem como delimitadores visuais; o writer **não** substitui mais esse bloco inteiro.
- Posição: entre a última linha multi-column de Horários e `<div style="margin-bottom: 20px;"></div>` que antecede `## Eventos` (âncora de inserção: header contendo `Eventos`).

## Comportamento

### Formatter (`src/handlers/formatter.py`)

- Remover `format_intervalos_block`.
- Nova constante de mapeamento:

```python
INTERVALO_MARKERS = {
    "Pausa Longa": "pausa-longa",
    "Pausa Rápida": "pausa-curta",
    "Café da manhã": "café",
    "Almoço": "almoço",
    "Jantar": "jantar",
    "Exercícios": "exercícios",
}
```

- Nova função `format_intervalo_contents(activity: DailyActivity) -> dict[str, str]`:
  - Chaves: os 6 slugs (sempre presentes).
  - Valor: `f"· {seconds_to_display(iv.duration_seconds)}"` para a entrada correspondente com duração > 0; `""` caso contrário (ou ausência na lista).

### Writer (`src/handlers/writer.py`)

- `update_note(..., intervalo_contents: dict[str, str] | None = None)` substitui o parâmetro `intervalo_block`.
- Nova `_merge_intervalo_markers(body: str, contents: dict[str, str]) -> str`:
  - Para cada slug, regex `<!-- {slug}-start -->.*?<!-- {slug}-end -->` (DOTALL); substitui apenas o interior, preservando os comentários e quebras ao redor.
  - Par de marcadores ausente → `logger.warning` com o slug, segue sem alterar (sem crash).
- Remover a chamada wholesale a `_merge_body_block` com os marcadores `-intervalos`.
- Caminho PC (`aw:start`/`aw:end`) e frontmatter inalterados.

### `src/main.py`

```python
intervalo_contents = format_intervalo_contents(activity)
update_note(note_path, fm_data, body_block, template_path, intervalo_contents)
```

### Migração (`scripts/migrate_interval_markers.py`, commitado)

- Flags: `--dry-run`, `--vault-root` (default de `VAULT_PATH` no `.env`), caminho do template default fixo (`99_Sistema/_templates/Nota Inteira/Jornada/Nota Diária 2_ISO.md` relativo ao vault).
- Para cada nota em `{vault}/01_Arquivos/Jornada/**.md` + template:
  1. **Callouts existentes**: localizar par título do callout + linha de query seguinte (`` >> `` `$= `` ou `` >> `` `= ``) e anexar ` <!-- {slug}-start --><!-- {slug}-end -->`. Idempotente: pula se marcador já existe.
  2. **Skeleton**: se nota já tem `aw:start-intervalos`, trocar conteúdo entre marcadores pelo skeleton estático; senão inserir bloco completo (com divs 40px/20px) imediatamente antes da linha de header que contém `Eventos`. Não duplicar div idêntico já presente adjacente ao ponto de inserção (ex: nota que já tem `<div style="margin-bottom: 20px;"></div>` antes de Eventos recebe só o bloco + espaçamento faltante). Idempotente: skeleton presente → pula.
  3. Nota sem âncoras (as 3 conhecidas) → warning com nome do arquivo, pula.
- Reversibilidade: `git -C G:\Lucas checkout/restore` desfaz.
- Saída final: resumo `X notas migradas, Y puladas`.

## Testes

### `tests/test_formatter.py`

1. `test_conteudos_tem_seis_slugs` — dict sempre com as 6 chaves.
2. `test_zero_ou_ausente_vazio` — duração 0/ausente → `""`.
3. `test_positivo_formato_separador` — 1860s → `"· 31m"`.

### `tests/test_writer.py`

1. `test_interior_substituido_preserva_marcadores_e_resto` — query dataview, títulos e linhas vizinhas intactos; interior atualizado.
2. `test_slug_ausente_skip_sem_crash` — nota sem `pausa-longa-start` → warning, resto atualizado.
3. `test_idempotencia` — rodar duas vezes = mesma saída.
4. `test_bloco_intervalos_nao_mais_substituido_wholesale` — texto manual entre `aw:start-intervalos/end` sobrevive ao update.

### Verificação

```powershell
python -m unittest discover -s tests -v
python scripts/migrate_interval_markers.py --dry-run   # revisar diff proposto
python scripts/migrate_interval_markers.py             # aplica (vault é git)
git -C G:\Lucas status                                  # conferir escopo das mudanças
python src/main.py                                      # sync real do dia
```

Checagem visual no Obsidian: callouts Café/Almoço/Jantar/Exercícios mostram `HH:mm · 31m`; Pausa Longa/Curta mostram duração quando houver.

## Decision Log

| Decisão | Alternativas | Motivo |
|---------|-------------|--------|
| Marcadores HTML por métrica dentro dos callouts | Frontmatter+dataview (B); bloco dinâmico mantido (C) | Preserva query/conteúdo manual; update cirúrgico pedido pelo usuário |
| Interior `· {duração}` ou vazio | Só duração; `(duração)`; `· 0m` | Escolha do usuário; vazio evita ruído em dia sem atividade |
| Slugs com acento (`café`, `almoço`) | Slug ASCII | Bate com rótulo visível; HTML comment aceita unicode |
| Skeleton estático no template/nota; writer não toca bloco inteiro | Continuar gerando skeleton dinâmico | Edições manuais sobrevivem ao sync |
| `[!sumário]+` para os callouts novos | Família `-fato`; `[!pause]+` | Modelo fornecido pelo usuário; tipo já existe no CSS do vault |
| "Pausa Rápida" → callout "Pausa Curta"/slug `pausa-curta` | Manter "Rápida" | Modelo fornecido pelo usuário |
| Script de migração commitado + idempotente | Edição manual; script descartável | 170 notas; re-execução segura; reversível via git do vault |
| Notas 2026-03-31, 2026-05-03, 2026-07-29 puladas | Tratamento especial | Estrutura diferente (sem callouts/Eventos); decidir caso a caso depois |
