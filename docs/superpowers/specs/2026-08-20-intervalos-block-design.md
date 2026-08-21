# Bloco de Intervalos no corpo da nota

## Objetivo

Registrar 6 atividades fora-do-PC marcadas via .exe dummy em `G:\Snippets\CLI` (truque: .exe vazio rouba o foco da janela e o `aw-watcher-window` grava a duração enquanto o usuário está afastado). Renderizar essas durações em um bloco próprio delimitado por `<!-- aw:start-intervalos -->` / `<!-- aw:end-intervalos -->` dentro de `## ⏰ Horários`, sem misturar com os dados de PC (`<!-- aw:start -->` / `<!-- aw:end -->` + frontmatter `pc:`).

## Contexto

- `aw-watcher-window_LucasLap` registra eventos com `app`+`title`+`duration` para a janela em foreground.
- .exe dummy ao abrir vira foreground; ao trocar de janela o AW fecha o evento com duração = tempo em foco.
- API confirmada retorna `app` com `.exe` (ex: `Jantar.exe`, `Intervalo.exe`).
- `clean_app_name` em `src/util/clean.py` já remove `.exe` e capitaliza → `Jantar`, `Café da manhã`, etc.
- Marcadores `<!-- aw:start-intervalos -->` / `<!-- aw:end-intervalos -->` já presentes no template `Nota Diária 2_ISO.md` (linha 210-212) e na nota de hoje (linha 231-233), dentro de `## ⏰ Horários`.

## Mapeamento .exe → rótulo → grupo

Hardcode em `src/handlers/fetch.py` (chaves = nome limpo pós-`clean_app_name`):

```python
INTERVALO_APPS = {
    "Intervalo": "Pausa Longa",
    "Pausa Rápida": "Pausa Rápida",
    "Café da manhã": "Café da manhã",
    "Almoço": "Almoço",
    "Jantar": "Jantar",
    "Exercícios": "Exercícios",
}
INTERVALO_GROUP = {
    "Pausa Longa": "Intervalo",
    "Pausa Rápida": "Intervalo",
    "Café da manhã": "Intervalo",
    "Almoço": "Intervalo",
    "Jantar": "Intervalo",
    "Exercícios": "Exercícios",
}
```

## Comportamento

### Fetch (`src/handlers/fetch.py`)

1. Agregar `app_totals` normalmente.
2. Antes de montar `uncategorized` e `total_seconds`:
   - Para cada `app_name` em `app_totals`, se estiver em `INTERVALO_APPS`, criar `IntervaloEntry(rotulo, group, secs)` e **remover** de `app_totals`.
   - Apps de intervalo **não entram** em `uncategorized` (não viram `pc.apps`) nem em `total_seconds` (não inflam tempo de PC).
3. `intervalos.sort(key=lambda x: (x.group, INTERVALO_ORDER.index(x.rotulo)))` onde `INTERVALO_ORDER = ["Pausa Longa", "Pausa Rápida", "Café da manhã", "Almoço", "Jantar", "Exercícios"]` garante ordem fixa por rótulo dentro do grupo.

### Modelo (`src/data/models.py`)

Novo dataclass + campo em `DailyActivity`:

```python
@dataclass
class IntervaloEntry:
    rotulo: str
    group: str
    duration_seconds: float

# em DailyActivity:
intervalos: list[IntervaloEntry] = field(default_factory=list)
```

### Formatter (`src/handlers/formatter.py`)

Nova função `format_intervalos_block(activity: DailyActivity) -> str`:

- Só duração legível (`seconds_to_display`), **sem `%`**.
- Agrupado: callout `Intervalo` com subs, callout `Exercícios` separado.
- **Item só aparece se `duration_seconds > 0`.**
- **Grupo só aparece se tiver ≥1 item com duração.**
- Ordem fixa entre itens mostrados: Pausa Longa → Pausa Rápida → Café da manhã → Almoço → Jantar → Exercícios.
- Se `activity.intervalos` vazio ou todos com 0s → bloco só com marcadores (vazio entre eles).

Saída exemplo (hoje, só Jantar com duração):
```markdown
<!-- aw:start-intervalos -->
> [!multi-column]
>
>> [!pause]+  Intervalo
>> - Jantar (0h36)
<!-- aw:end-intervalos -->
```

Saída exemplo (dia com Jantar + Exercícios):
```markdown
<!-- aw:start-intervalos -->
> [!multi-column]
>
>> [!pause]+  Intervalo
>> - Jantar (0h36)
>
>> [!fitness]+  Exercícios
>> - Exercícios (0h45)
<!-- aw:end-intervalos -->
```

### Writer (`src/handlers/writer.py`)

- Novas constantes `AW_INTERVALO_START` / `AW_INTERVALO_END`.
- Generalizar `_merge_body_block` para aceitar marcadores custom (`start`, `end` params).
- `update_note` recebe 2 blocos: `body_block` (PC) + `intervalo_block` (intervalos).
  - Merge PC primeiro (`aw:start`/`aw:end`, fallback `## Dados`).
  - Merge intervalos depois (`aw:start-intervalos`/`aw:end-intervalos`, fallback `## ⏰ Horários`).
- Bloco PC (`<!-- aw:start -->`) e frontmatter `pc:` continuam intactos — só dados de PC reais. Apps de intervalo já foram removidos em fetch, então não aparecem em `pc.apps` nem inflam `tempo_total`/`tempo_ativo`.

### `src/main.py`

```python
fm_data = format_frontmatter(activity)
body_block = format_body(activity)
intervalo_block = format_intervalos_block(activity)
update_note(note_path, fm_data, body_block, template_path, intervalo_block)
```

## Testes

### `tests/test_formatter.py` (extender)

Nova classe `FormatIntervalosTests`:

1. `test_so_itens_positivos_aparecem` — item com 0s omitido, item com >0 aparece.
2. `test_grupo_so_aparece_se_tem_item` — `intervalos=[]` → bloco vazio entre marcadores, sem callouts.
3. `test_ordenacao_fixa_dentro_do_grupo` — Pausa Rápida aparece antes de Jantar independente da duração.

### `tests/test_writer.py` (extender)

1. Nota com `## ⏰ Horários` + marcadores vazios → `update_note` com intervalo_block substitui conteúdo entre marcadores.
2. Nota sem marcadores mas com seção `## ⏰ Horários` → insere após a seção.

### Verificação

```powershell
python -m unittest discover -s tests -v
```

## Decision Log

| Decisão | Alternativas | Motivo |
|---------|-------------|--------|
| Hardcode do mapping .exe→rótulo | config.yaml | 6 nomes estáveis, diretório do truque fixo |
| Apps de intervalo fora de `total_seconds`/`uncategorized` | Contar como PC | Não é tempo de PC, inflaria métricas |
| Item só se `duration_seconds > 0` | Mostrar 0h00 | Evita ruído visual |
| Grupo só se ≥1 item | Sempre mostrar callout | Mesmo motivo |
| Bloco próprio `aw:start-intervalos` | Misturar em `aw:start` | Separação clara PC vs afastamento |
| Ordem fixa por rótulo | Ordem por duração | Consistência visual diária |
| Fallback `## ⏰ Horários` no writer | Só `## Dados` | Marcadores já no template dentro de Horários |
