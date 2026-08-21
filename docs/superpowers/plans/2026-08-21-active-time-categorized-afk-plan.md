# Tempo Ativo Inclui AFK Categorizado — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AFK que coincide com janelas das categorias `COUNT_AFK_CATEGORIES` passa a somar no `active_seconds`, via interseção precisa afk×janela classificada pelas regras regex do ActivityWatch.

**Architecture:** Novo helper puro `_compute_active_seconds(afk_events, window_events, classes)` em `src/handlers/fetch.py` (pré-classifica janelas com cache, soma not-afk integral + interseções de eventos afk com janelas categorizadas). `fetch_daily` busca as classes 1x e injeta no helper e em `_build_categories`. Formatter/writer/main intocados.

**Tech Stack:** Python 3.10+, stdlib (`datetime`, `re`), unittest. Spec: `docs/superpowers/specs/2026-08-21-active-time-includes-categorized-afk-design.md`.

**Regra de ambiente (worktree):** código no worktree `G:\Projetos\Worktrees-Proj\aw-active-afk`; testes com o interpretador absoluto `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe` (deps já instaladas lá), sempre com workdir = raiz do worktree. Copiar `.env` do repo principal para o worktree na Task 1 (arquivo local não-commitado; necessário para o sync real da Task 4).

---

### Task 1: Worktree

**Files:** nenhum (setup)

- [ ] **Step 1: Criar worktree**

```powershell
git worktree add "G:\Projetos\Worktrees-Proj\aw-active-afk" -b feat/active-time-categorized-afk
```

Expected: branch `feat/active-time-categorized-afk` a partir de `main`.

- [ ] **Step 2: Copiar .env local**

```powershell
Copy-Item "G:\Projetos\activitywatch_obsidian\.env" "G:\Projetos\Worktrees-Proj\aw-active-afk\.env"
```

Expected: arquivo copiado; `git status --porcelain` no worktree continua vazio (.env ignorado).

- [ ] **Step 3: Verificar interpretador**

```powershell
G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe --version
```

Expected: `Python 3.10+`.

---

### Task 2: Helper `_compute_active_seconds` (TDD)

**Files:**
- Modify: `src/handlers/fetch.py` (adicionar constante + helpers após `_get_duration`)
- Modify: `tests/test_fetch.py` (nova classe de testes)

- [ ] **Step 1: Escrever os testes falhando**

Em `tests/test_fetch.py`, adicionar imports (após os existentes no topo):

```python
from datetime import datetime, timedelta, timezone

from handlers.fetch import COUNT_AFK_CATEGORIES, _compute_active_seconds
```

E a nova classe antes do bloco `if __name__ == "__main__":`:

```python
class ComputeActiveSecondsTests(unittest.TestCase):
    BASE = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

    CLASSES = [
        {
            "name": ["Intervalo", "Café da manhã"],
            "rule": {"type": "regex", "regex": "caf"},
        },
        {
            "name": ["Estudando", "TogglTrack"],
            "rule": {"type": "regex", "regex": "toggl"},
        },
    ]

    def afk(self, status, minutes, offset=0):
        return {
            "timestamp": self.BASE + timedelta(minutes=offset),
            "duration": timedelta(minutes=minutes),
            "data": {"status": status},
        }

    def win(self, app, title, minutes, offset=0):
        return {
            "timestamp": self.BASE + timedelta(minutes=offset),
            "duration": timedelta(minutes=minutes),
            "data": {"app": app, "title": title},
        }

    def test_constante_tem_as_oito_categorias(self):
        self.assertEqual(
            COUNT_AFK_CATEGORIES,
            {
                "Intervalo > Pausa Rápida",
                "Intervalo > Café da manhã",
                "Intervalo > Almoço",
                "Intervalo > Jantar",
                "Intervalo > Pausa Longa",
                "Estudando > TogglTrack",
                "Exercício",
                "X",
            },
        )

    def test_afk_em_categoria_da_lista_conta_ativo(self):
        active = _compute_active_seconds(
            [self.afk("afk", 30)],
            [self.win("Café da manhã.exe", "", 30)],
            self.CLASSES,
        )
        self.assertEqual(active, 1800.0)

    def test_afk_fora_da_lista_nao_conta(self):
        active = _compute_active_seconds(
            [self.afk("afk", 30)],
            [self.win("chrome.exe", "Qualquer site", 30)],
            self.CLASSES,
        )
        self.assertEqual(active, 0.0)

    def test_intersecao_parcial(self):
        # janela de 60min cobre afk de 10min -> só 10min entram
        active = _compute_active_seconds(
            [self.afk("afk", 10)],
            [self.win("Café da manhã.exe", "", 60)],
            self.CLASSES,
        )
        self.assertEqual(active, 600.0)

    def test_multiplas_janelas_num_mesmo_afk(self):
        active = _compute_active_seconds(
            [self.afk("afk", 30)],
            [
                self.win("Café da manhã.exe", "", 20, offset=0),
                self.win("chrome.exe", "site", 10, offset=20),
            ],
            self.CLASSES,
        )
        self.assertEqual(active, 1200.0)

    def test_not_afk_soma_integral(self):
        active = _compute_active_seconds(
            [self.afk("not-afk", 45), self.afk("not-afk", 15, offset=45)],
            [],
            self.CLASSES,
        )
        self.assertEqual(active, 3600.0)

    def test_misto_not_afk_e_afk_categorizado(self):
        active = _compute_active_seconds(
            [self.afk("not-afk", 30), self.afk("afk", 30, offset=30)],
            [self.win("TogglTrack.exe", "toggl", 60)],
            self.CLASSES,
        )
        self.assertEqual(active, 3600.0)

    def test_sem_classes_fallback_not_afk(self):
        active = _compute_active_seconds(
            [self.afk("not-afk", 10), self.afk("afk", 20, offset=10)],
            [self.win("Café da manhã.exe", "", 30)],
            [],
        )
        self.assertEqual(active, 600.0)
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -k ComputeActiveSeconds -v` (workdir: raiz do worktree)

Expected: FAIL — `ImportError: cannot import name 'COUNT_AFK_CATEGORIES'`

- [ ] **Step 3: Implementar**

Em `src/handlers/fetch.py`:

3a. Adicionar ao topo do arquivo (após os imports existentes):

```python
import os
```

(remover o `import os` interno de `_build_categories` na Task 3 — por agora só adiciona o de nível de módulo se ainda não existir)

3b. Adicionar após `INTERVALO_ORDER`:

```python
COUNT_AFK_CATEGORIES = {
    "Intervalo > Pausa Rápida",
    "Intervalo > Café da manhã",
    "Intervalo > Almoço",
    "Intervalo > Jantar",
    "Intervalo > Pausa Longa",
    "Estudando > TogglTrack",
    "Exercício",
    "X",
}
```

3c. Adicionar após `_get_duration`:

```python
def _event_bounds(event) -> tuple[datetime, datetime]:
    """Converte evento AW em (start, end) absolutos."""
    ts = event["timestamp"]
    return ts, ts + timedelta(seconds=_get_duration(event))


def _compute_active_seconds(
    afk_events: list,
    window_events: list,
    classes: list[dict],
) -> float:
    """Tempo ativo = not-afk integral + AFK que coincide com janelas de COUNT_AFK_CATEGORIES.

    Sem janelas ou sem classes do AW, cai para not-afk puro (comportamento antigo).
    """
    window_slices: list[tuple[datetime, datetime, str]] = []
    if window_events and classes:
        cache: dict[tuple[str, str], str] = {}
        for w in window_events:
            data = w.get("data", {})
            key = (data.get("app", ""), data.get("title", ""))
            if key not in cache:
                cache[key] = _classify_event(w, classes)
            ws, we = _event_bounds(w)
            window_slices.append((ws, we, cache[key]))
    else:
        logger.warning(
            "Sem janelas ou classes do AW; tempo ativo cai para not-afk puro"
        )

    active = 0.0
    for e in afk_events:
        status = e.get("data", {}).get("status", "")
        if status == "not-afk":
            active += _get_duration(e)
            continue
        if status != "afk":
            continue
        es, ee = _event_bounds(e)
        for ws, we, cat in window_slices:
            if cat not in COUNT_AFK_CATEGORIES:
                continue
            overlap_start = max(es, ws)
            overlap_end = min(ee, we)
            if overlap_end > overlap_start:
                active += (overlap_end - overlap_start).total_seconds()
    return active
```

Nota: `timedelta` já está importado no módulo (`from datetime import date, datetime, timedelta, timezone`). Não duplicar.

- [ ] **Step 4: Rodar suíte completa**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v` (workdir: raiz do worktree)

Expected: PASS (35 testes: 27 anteriores + 8 novos).

- [ ] **Step 5: Commit**

```powershell
git add src/handlers/fetch.py tests/test_fetch.py
git commit -m "feat: helper calcula tempo ativo com afk categorizado"
```

---

### Task 3: Wiring no `fetch_daily` + `_build_categories`

**Files:**
- Modify: `src/handlers/fetch.py` (seção Window/AFK de `fetch_daily`; assinatura e corpo de `_build_categories`)

- [ ] **Step 1: Refatorar `fetch_daily`**

No início do corpo de `fetch_daily`, logo após `buckets = client.get_buckets()`:

```python
    host = os.environ.get("AW_HOST", "localhost")
    port = int(os.environ.get("AW_PORT", "5600"))
    classes = _fetch_categories(host, port)
```

Seção Window — trocar `events = client.get_events(window_bid, ...)` por variável dedicada e reutilizar:

```python
    window_events: list = []
    if window_bid:
        window_events = client.get_events(window_bid, limit=-1, start=start, end=end)
        raw_totals = _aggregate_events(window_events, lambda e: e.get("data", {}).get("app", ""))
```

(manter o restante da seção igual; o `len(events)` do log vira `len(window_events)`)

Seção AFK — substituir o loop atual:

```python
    afk_bid = _find_bucket(buckets, "aw-watcher-afk")
    active_seconds = 0.0
    if afk_bid:
        afk_events = client.get_events(afk_bid, limit=-1, start=start, end=end)
        active_seconds = _compute_active_seconds(afk_events, window_events, classes)
        logger.info("AFK: tempo ativo %.0fs", active_seconds)
```

Chamada de `_build_categories` no fim:

```python
    categories = _build_categories(client, window_bid, start, end, classes)
```

- [ ] **Step 2: Refatorar `_build_categories`**

Nova assinatura e corpo inicial (remover `import os` interno e chamada a `_fetch_categories`):

```python
def _build_categories(
    client: ActivityWatchClient,
    window_bid: str | None,
    start: datetime,
    end: datetime,
    classes: list[dict],
) -> list[Category]:
    """Classifica eventos do dia nas categorias configuradas no AW."""
    if not window_bid:
        return []

    events = client.get_events(window_bid, limit=-1, start=start, end=end)
```

(resto idêntico; remover as linhas `import os` / `host = ...` / `port = ...` / `classes = _fetch_categories(host, port)` internas)

- [ ] **Step 3: Verificar sintaxe e suíte**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import fetch"` (workdir: raiz do worktree)

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: sem erro de import; 35 testes OK.

- [ ] **Step 4: Commit**

```powershell
git add src/handlers/fetch.py
git commit -m "feat: fetch_daily usa afk categorizado no tempo ativo"
```

---

### Task 4: Verificação real + push

- [ ] **Step 1: Suíte completa**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v` (workdir: raiz do worktree)

Expected: 35 OK.

- [ ] **Step 2: Sync real comparativo (requer ActivityWatch rodando)**

Rodar duas vezes apontando o mesmo dia — uma com código novo, uma forçando fallback — NÃO é possível via flag; em vez disso, validar direto:

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe src/main.py --date <hoje>` (workdir: raiz do worktree)

Expected: log `AFK: tempo ativo <N>s` com N **maior ou igual** ao valor anterior (café/almoço de hoje agora contam). Conferir frontmatter `pc.tempo_ativo` na nota de hoje. Se AW offline: pular e marcar pendente para o usuário.

- [ ] **Step 3: Push**

```powershell
git push -u origin feat/active-time-categorized-afk
```
