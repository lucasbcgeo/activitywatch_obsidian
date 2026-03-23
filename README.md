# activitywatch-obsidian

Syncs [ActivityWatch](https://activitywatch.net) data into Obsidian daily notes.

## What it does

Queries the ActivityWatch API (window, AFK, web, and study watchers), extracts daily activity, and writes it to the `<!-- aw:start --><!-- aw:end -->` block and `pc:` frontmatter key of the matching daily note.

## Requirements

- Python 3.10+
- ActivityWatch running with `aw-watcher-window`, `aw-watcher-afk`, and `aw-watcher-web`
- Obsidian vault with daily notes (expected path: `VAULT/Diario/YYYY/MM/YYYY-MM-DD.md`)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
```

### Environment Variables

```env
AW_HOST=localhost
AW_PORT=5600
VAULT_PATH=/path/to/vault

IGNORE_APPS=ActivityWatch,System Settings
IGNORE_WEB=localhost
MIN_MINUTES_APPS=5
MIN_MINUTES_WEB=1
```

## Usage

```bash
# Sync today
python src/main.py

# Sync specific date
python src/main.py --date 2026-03-22
```

## Architecture

Layered pattern: `fetch → format → write`

```
src/
├── main.py                # CLI entry point
├── handlers/
│   ├── fetch.py          # Query ActivityWatch API (apps, AFK, web, categories)
│   ├── formatter.py      # Build frontmatter + body block
│   └── writer.py         # Merge into daily note
├── data/
│   └── models.py         # Dataclasses (DailyActivity, Category, AppUsage, etc.)
├── util/
│   ├── paths.py          # Daily note path resolution
│   ├── time_fmt.py       # seconds → ISO 8601 / display
│   ├── yaml_helpers.py   # Frontmatter parse/merge/rebuild
│   └── clean.py          # App name and domain cleaning
└── log/
    └── __init__.py       # Logging setup
```

## Output

**Frontmatter** — under `pc:`:
```yaml
pc:
  tempo_total: "PT8H30M"
  tempo_ativo: "PT6H15M"
  apps:
    - VS Code: "PT2H00M"
    - Chrome: "PT1H30M"
  web:
    - youtube.com: "PT1H00M"
```

**Body** — inside `<!-- aw:start --><!-- aw:end -->`:
```markdown
### PC  **Tempo ativo:** 6h15 / **Total:** 8h30

> [!multi-column]
>> [!abstract]+  Apps
>> **Tempo ativo:** 4h30
>> - VS Code (2h00)
>> - Chrome (1h30)
>>
>> [!example]+  Web
>> **Tempo ativo:** 1h30
>> - youtube.com (1h00)
```

---

## activitywatch-obsidian (Português)

Sincroniza dados do [ActivityWatch](https://activitywatch.net) para notas diárias do Obsidian.

## O que faz

Consulta a API do ActivityWatch (window, AFK, web e estudo), extrai a atividade diária e escreve no bloco `<!-- aw:start --><!-- aw:end -->` e chave `pc:` do frontmatter da nota diária correspondente.

## Requisitos

- Python 3.10+
- ActivityWatch rodando com `aw-watcher-window`, `aw-watcher-afk` e `aw-watcher-web`
- Vault do Obsidian com notas diárias

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edite o .env com suas configurações
```

### Variáveis de Ambiente

```env
AW_HOST=localhost
AW_PORT=5600
VAULT_PATH=/path/to/vault

IGNORE_APPS=ActivityWatch,System Settings
IGNORE_WEB=localhost
MIN_MINUTES_APPS=5
MIN_MINUTES_WEB=1
```

## Uso

```bash
# Sincronizar hoje
python src/main.py

# Sincronizar data específica
python src/main.py --date 2026-03-22
```

## Arquitetura

Padrão em camadas: `fetch → format → write`

```
src/
├── main.py                # Ponto de entrada CLI
├── handlers/
│   ├── fetch.py          # Consulta API do ActivityWatch
│   ├── formatter.py      # Monta frontmatter + bloco body
│   └── writer.py         # Faz merge na nota diária
├── data/
│   └── models.py         # Dataclasses (DailyActivity, Category, etc.)
├── util/
│   ├── paths.py          # Resolução de caminho da nota
│   ├── time_fmt.py       # segundos → ISO 8601 / display
│   ├── yaml_helpers.py   # Parse/merge/rebuild do frontmatter
│   └── clean.py          # Limpeza de nome de app e domínio
└── log/
    └── __init__.py       # Configuração de logging
```
