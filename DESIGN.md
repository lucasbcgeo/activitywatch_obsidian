# ActivityWatch → Obsidian Daily Notes

## Resumo

Script Python que puxa dados do ActivityWatch via API e insere nas notas diárias do Obsidian.

## Estrutura

```
.activitywatch/
├── main.py                  # Entry point CLI
├── .env                     # AW_HOST, AW_PORT, VAULT_PATH
├── .env.example             # Template
├── config.yaml              # Formato duração, seção da nota, overrides
├── requirements.txt         # aw-client, pyyaml, python-dotenv
├── run.bat                  # Task Scheduler
│
├── handlers/
│   ├── __init__.py
│   ├── fetch.py             # Consulta API do ActivityWatch
│   ├── formatter.py         # Transforma dados → YAML + MD
│   └── writer.py            # Lê nota, faz merge frontmatter+corpo
│
├── data/
│   ├── __init__.py
│   └── models.py            # Dataclasses (DailyActivity, Category, etc.)
│
├── util/
│   ├── __init__.py
│   ├── time_fmt.py          # Formatação de durações (s → "2h15")
│   ├── yaml_helpers.py      # Merge/parse YAML frontmatter
│   └── paths.py             # Resolve caminho da nota diária
│
└── log/
    ├── __init__.py           # Config logging (console + arquivo)
    └── .gitkeep
```

## Watchers

1. **aw-watcher-window** — apps/janelas ativas
2. **aw-watcher-afk** — tempo ativo vs idle
3. **aw-watcher-web** — sites visitados no Chrome
4. **aw-watcher-obsidian** — arquivos editados no Obsidian

## Models

```python
@dataclass
class AppUsage:
    name: str
    duration_seconds: float

@dataclass
class WebVisit:
    domain: str
    duration_seconds: float

@dataclass
class ObsidianFile:
    filename: str
    duration_seconds: float
    is_study: bool  # flag para lógica futura

@dataclass
class Category:
    name: str
    total_seconds: float
    apps: list[AppUsage]

@dataclass
class DailyActivity:
    date: str
    total_seconds: float
    active_seconds: float
    categories: list[Category]
    uncategorized: list[AppUsage]
    web: list[WebVisit]
    obsidian: list[ObsidianFile]
```

## Frontmatter

Dados sob chave raiz `pc:` com objetos YAML aninhados:

```yaml
pc:
  tempo_total: "8h30"
  tempo_ativo: "6h15"
  apps:
    - vscode: "2h00"
    - anki: "1h30"
  web:
    - youtube.com: "1h00"
    - google.com: "0h30"
  obsidian:
    - "Direito Constitucional.md": "0h45"
  categorias:
    estudo:
      total: "3h00"
    lazer:
      total: "1h30"
```

Notas de estudo do Obsidian: lógica própria a definir depois.

## Corpo da Nota

Inserido em `## Dados` usando callouts multi-column, delimitado por `<!-- aw:start -->` / `<!-- aw:end -->`:

```markdown
<!-- aw:start -->
> [!multi-column]
>
>> [!abstract]+  PC - Atividade
>> **Tempo ativo:** 6h15 / **Total:** 8h30
>> **Top Apps:** VS Code (2h00) • Anki (1h30) • Chrome (1h00)
>
>> [!globe]+  Web
>> youtube.com (1h00) • google.com (0h30) • github.com (0h20)
>
>> [!folder]+  Obsidian
>> Direito Constitucional.md (0h45) • 2026-03-09.md (0h20)
<!-- aw:end -->
```

## Merge

- **Frontmatter:** deep merge da chave `pc` (atualiza valores, preserva resto)
- **Corpo:** substitui conteúdo entre `<!-- aw:start -->` e `<!-- aw:end -->`
- Só funciona em notas já criadas

## Execução

- Manual: `python main.py [--date YYYY-MM-DD]`
- Agendada: `run.bat` via Task Scheduler

## Configuração

**.env:**
```
AW_HOST=localhost
AW_PORT=5600
VAULT_PATH=G:/Lucas
```

**config.yaml:**
```yaml
duration_format: "Xh Xm"
note_section: "## Dados"
category_overrides:
  - app: "anki"
    category: "Estudo"
```

## Decision Log

| Decisão | Alternativas | Motivo |
|---------|-------------|--------|
| Modular (handlers/data/util/log) | Script único | Preferência do usuário por organização |
| .env + config.yaml | Só config.yaml | Separar ambiente de lógica |
| Tudo dentro de `pc:` no frontmatter | Chaves raiz separadas | Organização coesa |
| Notas de estudo Obsidian → lógica futura | Incluir agora | Requisito ainda não definido |
| Merge com deep merge + aw:start/end | Sobrescrever / Pular | Atualiza sem perder dados manuais |
| Multi-column callouts no corpo | Texto simples | Consistência com estilo existente |
| Só notas existentes | Criar nota se ausente | Usuário cria pelo Obsidian |
| 4 watchers (window, afk, web, obsidian) | Só window+afk | Dados mais completos |
