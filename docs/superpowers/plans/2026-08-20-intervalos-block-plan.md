# Bloco de Intervalos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renderizar 6 atividades fora-do-PC (marcadas via .exe dummy) em um bloco próprio `<!-- aw:start-intervalos -->...<!-- aw:end-intervalos -->` dentro de `## ⏰ Horários`, sem misturar com dados de PC (`pc.apps`, `tempo_total`, `tempo_ativo`).

**Architecture:** Hardcode do mapping `.exe`→rótulo→grupo em `fetch.py`. Extrair apps de intervalo de `app_totals` antes de computar `total_seconds`/`uncategorized` via função pura `_extract_intervalos`. Novo campo `DailyActivity.intervalos: list[IntervaloEntry]`. Nova função `format_intervalos_block` em `formatter.py`. Writer generalizado para merge de múltiplos blocos por marcadores custom.

**Tech Stack:** Python 3.10+ stdlib, `unittest`, dataclasses existentes, `aw-client`, `pyyaml`.

---

### Task 1: Adicionar modelo IntervaloEntry e campo em DailyActivity

**Files:**
- Modify: `src/data/models.py`

- [ ] **Step 1: Adicionar IntervaloEntry e campo `intervalos` em DailyActivity**

Substituir o conteúdo de `src/data/models.py` por:

```python
from dataclasses import dataclass, field


@dataclass
class AppUsage:
    name: str
    duration_seconds: float


@dataclass
class WebVisit:
    domain: str
    duration_seconds: float


@dataclass
class StudyItem:
    name: str
    duration_seconds: float


@dataclass
class Category:
    name: str
    total_seconds: float
    apps: list[AppUsage] = field(default_factory=list)


@dataclass
class IntervaloEntry:
    rotulo: str
    group: str
    duration_seconds: float


@dataclass
class DailyActivity:
    date: str
    total_seconds: float
    active_seconds: float
    categories: list[Category] = field(default_factory=list)
    uncategorized: list[AppUsage] = field(default_factory=list)
    web: list[WebVisit] = field(default_factory=list)
    study: list[StudyItem] = field(default_factory=list)
    intervalos: list[IntervaloEntry] = field(default_factory=list)
```

- [ ] **Step 2: Verificar importação**

Run: `.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from data.models import IntervaloEntry, DailyActivity; e=IntervaloEntry('Jantar','Intervalo',100.0); d=DailyActivity(date='2026-08-20',total_seconds=0,active_seconds=0); d.intervalos.append(e); print(d.intervalos[0].rotulo)"`

Expected: imprime `Jantar`, exit code 0.

- [ ] **Step 3: Commit**

```powershell
git add src/data/models.py
git commit -m "feat: add IntervaloEntry model and DailyActivity.intervalos field"
```

---

### Task 2: Extrair apps de intervalo em fetch (pure helper + wiring)

**Files:**
- Modify: `src/handlers/fetch.py`
- Create: `tests/test_fetch.py`

- [ ] **Step 1: Escrever testes falhando para `_extract_intervalos`**

Criar `tests/test_fetch.py`:

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from data.models import IntervaloEntry
from handlers.fetch import INTERVALO_APPS, INTERVALO_GROUP, INTERVALO_ORDER, _extract_intervalos


class ExtractIntervalosTests(unittest.TestCase):
    def test_separa_intervalos_de_apps_normais(self):
        app_totals = {"Jantar": 973.0, "VS Code": 3600.0, "Exercícios": 45.0}
        intervalos, remaining = _extract_intervalos(app_totals)

        rotulos = {(i.rotulo, i.group) for i in intervalos}
        self.assertIn(("Jantar", "Intervalo"), rotulos)
        self.assertIn(("Exercícios", "Exercícios"), rotulos)
        self.assertEqual(remaining, {"VS Code": 3600.0})

    def test_ordem_fixa_por_rotulo_dentro_do_grupo(self):
        app_totals = {"Jantar": 100.0, "Pausa Rápida": 50.0, "Almoço": 30.0}
        intervalos, _ = _extract_intervalos(app_totals)
        rotulos = [i.rotulo for i in intervalos]
        self.assertEqual(rotulos, ["Pausa Rápida", "Almoço", "Jantar"])

    def test_sem_intervalos_retorna_lista_vazia_e_preserva_apps(self):
        app_totals = {"VS Code": 3600.0, "Chrome": 600.0}
        intervalos, remaining = _extract_intervalos(app_totals)
        self.assertEqual(intervalos, [])
        self.assertEqual(remaining, app_totals)

    def test_mapeamento_intervalo_exe_vira_pausa_longa(self):
        app_totals = {"Intervalo": 120.0}
        intervalos, remaining = _extract_intervalos(app_totals)
        self.assertEqual(intervalos[0].rotulo, "Pausa Longa")
        self.assertEqual(intervalos[0].group, "Intervalo")
        self.assertEqual(remaining, {})

    def test_constantes_cobrem_os_6_rotulos(self):
        self.assertEqual(
            set(INTERVALO_APPS.values()),
            {"Pausa Longa", "Pausa Rápida", "Café da manhã", "Almoço", "Jantar", "Exercícios"},
        )
        self.assertEqual(set(INTERVALO_GROUP.values()), {"Intervalo", "Exercícios"})
        self.assertEqual(len(INTERVALO_ORDER), 6)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e verificar falha**

Run: `.venv\Scripts\python.exe -m unittest tests.test_fetch -v`

Expected: ImportError ou AttributeError — `_extract_intervalos`, `INTERVALO_APPS`, `INTERVALO_GROUP`, `INTERVALO_ORDER` não existem em `fetch.py`.

- [ ] **Step 3: Adicionar constantes e helper em `fetch.py`**

No topo de `src/handlers/fetch.py`, após o bloco de imports (depois de `from util.clean import clean_app_name, clean_domain`), adicionar:

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
INTERVALO_ORDER = [
    "Pausa Longa",
    "Pausa Rápida",
    "Café da manhã",
    "Almoço",
    "Jantar",
    "Exercícios",
]


def _extract_intervalos(
    app_totals: dict[str, float],
) -> tuple[list[IntervaloEntry], dict[str, float]]:
    """Separa apps de intervalo (.exe dummy) dos apps normais de PC.

    Returns:
        (lista de IntervaloEntry ordenada por (group, ordem fixa),
         dict app_totals sem os apps de intervalo)
    """
    intervalos: list[IntervaloEntry] = []
    remaining: dict[str, float] = {}
    for app_name, secs in app_totals.items():
        rotulo = INTERVALO_APPS.get(app_name)
        if rotulo:
            intervalos.append(
                IntervaloEntry(rotulo, INTERVALO_GROUP[rotulo], secs)
            )
        else:
            remaining[app_name] = secs
    intervalos.sort(
        key=lambda x: (x.group, INTERVALO_ORDER.index(x.rotulo))
    )
    return intervalos, remaining
```

Adicionar `IntervaloEntry` ao import de `data.models` no topo de `fetch.py`:

```python
from data.models import AppUsage, Category, DailyActivity, IntervaloEntry, StudyItem, WebVisit
```

- [ ] **Step 4: Integrar `_extract_intervalos` em `fetch_daily`**

Em `src/handlers/fetch.py`, localizar o bloco (atualmente linhas 52-63):

```python
    # --- Window watcher (apps) ---
    window_bid = _find_bucket(buckets, "aw-watcher-window")
    app_totals: dict[str, float] = {}
    total_seconds = 0.0
    if window_bid:
        events = client.get_events(window_bid, limit=-1, start=start, end=end)
        raw_totals = _aggregate_events(events, lambda e: e.get("data", {}).get("app", ""))
        for raw_name, secs in raw_totals.items():
            clean = clean_app_name(raw_name)
            app_totals[clean] = app_totals.get(clean, 0.0) + secs
        total_seconds = sum(app_totals.values())
        logger.info("Window: %d eventos, %.0fs total", len(events), total_seconds)
```

Substituir por:

```python
    # --- Window watcher (apps) ---
    window_bid = _find_bucket(buckets, "aw-watcher-window")
    app_totals: dict[str, float] = {}
    total_seconds = 0.0
    intervalos: list[IntervaloEntry] = []
    if window_bid:
        events = client.get_events(window_bid, limit=-1, start=start, end=end)
        raw_totals = _aggregate_events(events, lambda e: e.get("data", {}).get("app", ""))
        for raw_name, secs in raw_totals.items():
            clean = clean_app_name(raw_name)
            app_totals[clean] = app_totals.get(clean, 0.0) + secs
        intervalos, app_totals = _extract_intervalos(app_totals)
        total_seconds = sum(app_totals.values())
        logger.info(
            "Window: %d eventos, %.0fs total PC, %d intervalos",
            len(events),
            total_seconds,
            len(intervalos),
        )
```

Localizar o bloco que monta `apps_sorted` e o `return DailyActivity(...)` (atualmente linhas 113-127):

```python
    apps_sorted = [
        AppUsage(name=name, duration_seconds=dur)
        for name, dur in sorted(app_totals.items(), key=lambda x: -x[1])
        if name
    ]

    return DailyActivity(
        date=target_date.isoformat(),
        total_seconds=total_seconds,
        active_seconds=active_seconds,
        categories=categories,
        uncategorized=apps_sorted,
        web=web_list,
        study=study_items,
    )
```

Substituir por:

```python
    apps_sorted = [
        AppUsage(name=name, duration_seconds=dur)
        for name, dur in sorted(app_totals.items(), key=lambda x: -x[1])
        if name
    ]

    return DailyActivity(
        date=target_date.isoformat(),
        total_seconds=total_seconds,
        active_seconds=active_seconds,
        categories=categories,
        uncategorized=apps_sorted,
        web=web_list,
        study=study_items,
        intervalos=intervalos,
    )
```

- [ ] **Step 5: Rodar testes focados e completos**

Run: `.venv\Scripts\python.exe -m unittest tests.test_fetch -v`

Expected: 5 testes passam, exit code 0.

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: todos os testes (test_fetch + test_formatter + test_writer) passam.

- [ ] **Step 6: Commit**

```powershell
git add src/handlers/fetch.py tests/test_fetch.py
git commit -m "feat: extract intervalo apps from PC totals in fetch"
```

---

### Task 3: Formatter — `format_intervalos_block`

**Files:**
- Modify: `src/handlers/formatter.py`
- Modify: `tests/test_formatter.py`

- [ ] **Step 1: Escrever testes falhando para `format_intervalos_block`**

Adicionar ao final de `tests/test_formatter.py` (antes de `if __name__ == "__main__":`):

```python
from data.models import IntervaloEntry
from handlers.formatter import format_intervalos_block


class FormatIntervalosTests(unittest.TestCase):
    def _activity(self, intervalos):
        return DailyActivity(
            date=date(2026, 8, 20).isoformat(),
            total_seconds=0,
            active_seconds=0,
            intervalos=intervalos,
        )

    def test_so_itens_positivos_aparecem(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),    # 0h36
            IntervaloEntry("Exercícios", "Exercícios", 0),  # omitido
        ])
        block = format_intervalos_block(activity)
        self.assertIn("Jantar (0h36)", block)
        self.assertNotIn("Exercícios", block)
        self.assertIn("<!-- aw:start-intervalos -->", block)
        self.assertIn("<!-- aw:end-intervalos -->", block)

    def test_grupo_so_aparece_se_tem_item_positivo(self):
        activity = self._activity([])
        block = format_intervalos_block(activity)
        self.assertNotIn("Intervalo", block)
        self.assertNotIn("Exercícios", block)
        self.assertIn("<!-- aw:start-intervalos -->", block)
        self.assertIn("<!-- aw:end-intervalos -->", block)

    def test_ordenacao_fixa_dentro_do_grupo(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 100),
            IntervaloEntry("Pausa Rápida", "Intervalo", 50),
        ])
        block = format_intervalos_block(activity)
        self.assertLess(block.index("Pausa Rápida"), block.index("Jantar"))

    def test_duas_secoes_intervalo_e_exercicios(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),
            IntervaloEntry("Exercícios", "Exercícios", 2700),
        ])
        block = format_intervalos_block(activity)
        self.assertIn("Intervalo", block)
        self.assertIn("Exercícios", block)
        self.assertIn("Jantar (0h36)", block)
        self.assertIn("Exercícios (0h45)", block)

    def test_sem_porcentagem_no_bloco(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 2160),
        ])
        block = format_intervalos_block(activity)
        self.assertNotIn("%", block)
```

- [ ] **Step 2: Rodar e verificar falha**

Run: `.venv\Scripts\python.exe -m unittest tests.test_formatter.FormatIntervalosTests -v`

Expected: ImportError — `format_intervalos_block` não existe.

- [ ] **Step 3: Implementar `format_intervalos_block` em `formatter.py`**

Adicionar import no topo de `src/handlers/formatter.py`:

```python
from data.models import DailyActivity, IntervaloEntry
```

(Localizar o import atual `from data.models import DailyActivity` e substituir pela linha acima.)

Adicionar ao final de `src/handlers/formatter.py` (após `format_body`):

```python
def format_intervalos_block(activity: DailyActivity) -> str:
    """Gera bloco Markdown com callouts multi-column para intervalos e exercicios.

    Soh itens com duration_seconds > 0 aparecem. Grupo soh aparece se tiver >=1 item.
    Ordem fixa por INTERVALO_ORDER (preservada pela ordenacao em fetch).
    """
    groups: dict[str, list[IntervaloEntry]] = {}
    for iv in activity.intervalos:
        if iv.duration_seconds > 0:
            groups.setdefault(iv.group, []).append(iv)

    lines = ["<!-- aw:start-intervalos -->"]
    if groups:
        lines.append("> [!multi-column]")
        for group_name in ("Intervalo", "Exercícios"):
            items = groups.get(group_name)
            if not items:
                continue
            icon = "pause" if group_name == "Intervalo" else "fitness"
            lines.append(">")
            lines.append(f">> [!{icon}]+  {group_name}")
            for iv in items:
                lines.append(
                    f">> - {iv.rotulo} ({seconds_to_display(iv.duration_seconds)})"
                )
    lines.append("<!-- aw:end-intervalos -->")
    return "\n".join(lines)
```

- [ ] **Step 4: Rodar testes focados e completos**

Run: `.venv\Scripts\python.exe -m unittest tests.test_formatter.FormatIntervalosTests -v`

Expected: 5 testes passam.

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: todos passam.

- [ ] **Step 5: Commit**

```powershell
git add src/handlers/formatter.py tests/test_formatter.py
git commit -m "feat: add format_intervalos_block for aw:start-intervalos section"
```

---

### Task 4: Writer — generalizar merge para múltiplos blocos

**Files:**
- Modify: `src/handlers/writer.py`
- Modify: `tests/test_writer.py`

- [ ] **Step 1: Escrever testes falhando para merge de intervalos**

Adicionar import no topo de `tests/test_writer.py`:

```python
from handlers.writer import AW_END, AW_END_INTERVALO, AW_START, AW_START_INTERVALO, update_note
```

(Localizar `from handlers.writer import AW_END, AW_START, update_note` e substituir pela linha acima.)

Adicionar ao final de `tests/test_writer.py` (antes de `if __name__ == "__main__":`):

```python
class UpdateIntervalosTests(unittest.TestCase):
    def _base_note(self, with_markers=True):
        markers = (
            f"{AW_START_INTERVALO}\n\n{AW_END_INTERVALO}\n"
            if with_markers
            else ""
        )
        return (
            "---\nnota: x\n---\n\n"
            "## ⏰ Horários\n\n"
            f"{markers}"
            "## 🗓️ Eventos\n\nconteudo\n"
        )

    def test_substitui_bloco_intervalos_existente(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-20.md"
            note.write_text(self._base_note(with_markers=True), encoding="utf-8")
            intervalo_block = (
                f"{AW_START_INTERVALO}\n> [!pause]+  Intervalo\n> - Jantar (0h36)\n{AW_END_INTERVALO}"
            )
            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\npc\n{AW_END}",
                None,
                intervalo_block,
            )
            content = note.read_text(encoding="utf-8")
            self.assertIn("Jantar (0h36)", content)
            self.assertIn(AW_START_INTERVALO, content)
            self.assertIn(AW_END_INTERVALO, content)

    def test_insere_bloco_intervalos_em_secao_se_sem_marcadores(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-20.md"
            note.write_text(self._base_note(with_markers=False), encoding="utf-8")
            intervalo_block = (
                f"{AW_START_INTERVALO}\n> [!pause]+  Intervalo\n> - Jantar (0h36)\n{AW_END_INTERVALO}"
            )
            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\npc\n{AW_END}",
                None,
                intervalo_block,
            )
            content = note.read_text(encoding="utf-8")
            self.assertIn("Jantar (0h36)", content)
            idx_horarios = content.index("## ⏰ Horários")
            idx_intervalo = content.index(AW_START_INTERVALO)
            idx_eventos = content.index("## 🗓️ Eventos")
            self.assertLess(idx_horarios, idx_intervalo)
            self.assertLess(idx_intervalo, idx_eventos)

    def test_sem_intervalo_block_nao_altera_secao_horarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-20.md"
            original = self._base_note(with_markers=True)
            note.write_text(original, encoding="utf-8")
            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\npc\n{AW_END}",
                None,
                None,
            )
            content = note.read_text(encoding="utf-8")
            self.assertIn(f"{AW_START_INTERVALO}\n\n{AW_END_INTERVALO}", content)
```

- [ ] **Step 2: Rodar e verificar falha**

Run: `.venv\Scripts\python.exe -m unittest tests.test_writer.UpdateIntervalosTests -v`

Expected: ImportError — `AW_START_INTERVALO`, `AW_END_INTERVALO` não existem; `update_note` não aceita 5º arg.

- [ ] **Step 3: Adicionar constantes e generalizar `_merge_body_block` em `writer.py`**

Em `src/handlers/writer.py`, localizar (atualmente linhas 11-12):

```python
AW_START = "<!-- aw:start -->"
AW_END = "<!-- aw:end -->"
```

Substituir por:

```python
AW_START = "<!-- aw:start -->"
AW_END = "<!-- aw:end -->"
AW_START_INTERVALO = "<!-- aw:start-intervalos -->"
AW_END_INTERVALO = "<!-- aw:end-intervalos -->"
```

Substituir a função `_merge_body_block` inteira (atualmente linhas 130-152) por:

```python
def _merge_body_block(
    body: str,
    block: str,
    start: str = AW_START,
    end: str = AW_END,
    section_fallback: str = "## Dados",
) -> str:
    """Insere ou substitui bloco delimitado por start/end.

    Se marcadores existem, substitui conteudo entre eles.
    Se nao, insere apos section_fallback (secao header). Fallback final: append.
    """
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)

    if pattern.search(body):
        body = pattern.sub(block, body)
        logger.info("Bloco %s atualizado (merge)", start)
    else:
        section_match = re.search(
            rf"({re.escape(section_fallback)}\b.*?)(\n## |\n# |\Z)",
            body,
            re.DOTALL,
        )
        if section_match:
            insert_pos = section_match.end(1)
            body = body[:insert_pos] + "\n" + block + "\n" + body[insert_pos:]
            logger.info("Bloco %s inserido em %s", start, section_fallback)
        else:
            body = body.rstrip() + "\n\n" + block + "\n"
            logger.warning(
                "%s nao encontrado, bloco %s inserido no final",
                section_fallback,
                start,
            )

    return body
```

Substituir a função `update_note` inteira (atualmente linhas 15-47) por:

```python
def update_note(
    note_path: str,
    fm_data: dict,
    body_block: str,
    template_path: str | None = None,
    intervalo_block: str | None = None,
) -> None:
    """Atualiza nota diaria com dados do ActivityWatch.

    - Frontmatter: deep merge da chave 'pc'
    - Corpo (PC): insere/substitui bloco entre aw:start e aw:end em ## Dados
    - Corpo (Intervalos): insere/substitui bloco entre aw:start-intervalos e
      aw:end-intervalos em ## Horarios (se intervalo_block fornecido)
    """
    if os.path.isfile(note_path):
        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        parent = os.path.dirname(note_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        content = _render_daily_template(note_path, template_path)
        logger.info("Nota diaria criada: %s", note_path)

    frontmatter, body = parse_note(content)

    frontmatter = deep_merge(frontmatter, fm_data)
    logger.info("Frontmatter atualizado com chave 'pc'")

    body = _merge_body_block(body, body_block)
    if intervalo_block is not None:
        body = _merge_body_block(
            body,
            intervalo_block,
            AW_START_INTERVALO,
            AW_END_INTERVALO,
            "## ⏰ Horários",
        )

    result = rebuild_note(frontmatter, body)

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Nota salva: %s", note_path)
```

- [ ] **Step 4: Rodar testes focados e completos**

Run: `.venv\Scripts\python.exe -m unittest tests.test_writer -v`

Expected: todos os testes (UpdateNoteTests + UpdateIntervalosTests) passam.

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: todos passam (test_fetch + test_formatter + test_writer).

- [ ] **Step 5: Commit**

```powershell
git add src/handlers/writer.py tests/test_writer.py
git commit -m "feat: generalize body merge for intervalos block in writer"
```

---

### Task 5: Wiring no main.py

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Importar e chamar `format_intervalos_block`**

Em `src/main.py`, localizar o import (atualmente linha 10):

```python
from handlers.formatter import format_body, format_frontmatter
```

Substituir por:

```python
from handlers.formatter import format_body, format_frontmatter, format_intervalos_block
```

Localizar o bloco (atualmente linhas 60-66):

```python
    # Format
    fm_data = format_frontmatter(activity)
    body_block = format_body(activity)

    # Write
    try:
        update_note(note_path, fm_data, body_block, template_path)
```

Substituir por:

```python
    # Format
    fm_data = format_frontmatter(activity)
    body_block = format_body(activity)
    intervalo_block = format_intervalos_block(activity)

    # Write
    try:
        update_note(note_path, fm_data, body_block, template_path, intervalo_block)
```

- [ ] **Step 2: Rodar suite completa**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

Expected: todos passam, exit code 0.

- [ ] **Step 3: Verificar importação do main**

Run: `.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); import main; print('ok')"`

Expected: imprime `ok`, exit code 0.

- [ ] **Step 4: Commit**

```powershell
git add src/main.py
git commit -m "feat: wire intervalos block into main sync flow"
```

---

### Task 6: Integração end-to-end (manual)

**Files:**
- Nenhum (verificação manual)

- [ ] **Step 1: Confirmar ActivityWatch rodando**

Run: `Invoke-RestMethod -Uri "http://localhost:5600/api/0/buckets" -TimeoutSec 5 | Select-Object -ExpandProperty Keys | Where-Object { $_ -like "*window*" }`

Expected: lista contém `aw-watcher-window_LucasLap`.

- [ ] **Step 2: Rodar sync para hoje**

Run: `.venv\Scripts\python.exe src\main.py`

Expected: log termina com `Sync concluído com sucesso!` e linha `Window: N eventos, Xs total PC, Y intervalos` com Y > 0 (se .exe abertos hoje).

- [ ] **Step 3: Verificar bloco intervalos na nota de hoje**

Abrir `G:\Lucas\01_Arquivos\Jornada\2026\08\2026-08-20.md` e localizar `## ⏰ Horários`.

Expected:
- Marcadores `<!-- aw:start-intervalos -->` / `<!-- aw:end-intervalos -->` presentes.
- Callout `> [!pause]+  Intervalo` com itens de duração > 0 (ex: `- Jantar (0h36)`).
- Se Exercícios com duração > 0, callout `> [!fitness]+  Exercícios` presente.
- Itens com 0s **não** aparecem.

- [ ] **Step 4: Verificar PC intacto**

Na mesma nota, localizar `<!-- aw:start -->` / `<!-- aw:end -->` e frontmatter `pc:`.

Expected:
- `pc.tempo_total` e `pc.tempo_ativo` **não** incluem tempo de Jantar/Exercícios/etc.
- `pc.apps` **não** lista Jantar, Exercícios, Intervalo, Pausa Rápida, Café da manhã, Almoço.
- Apps normais (VS Code, Chrome, etc.) presentes normalmente.
- Categorias, Games, web, estudo intactos.

- [ ] **Step 5: Rodar sync para data sem intervalos (opcional)**

Run: `.venv\Scripts\python.exe src\main.py --date 2026-08-01`

Expected: bloco `aw:start-intervalos`/`aw:end-intervalos` presente mas vazio entre marcadores (sem callouts).

---

## Self-Review

**Spec coverage:**
- Mapeamento .exe→rótulo→grupo hardcode → Task 2 (constantes).
- `IntervaloEntry` + `DailyActivity.intervalos` → Task 1.
- Extrair intervalos de `app_totals`, excluir de `total_seconds`/`uncategorized` → Task 2 (helper + wiring).
- `format_intervalos_block` (duração não-%, item só se >0, grupo só se ≥1, ordem fixa) → Task 3.
- Writer generalizado para 2 blocos, fallback `## ⏰ Horários` → Task 4.
- `main.py` wiring → Task 5.
- PC intacto (continua aparecendo, não mistura) → Task 2 (exclusão) + Task 4 (merge separado) + Task 6 Step 4 (verificação manual).
- Testes formatter + writer + fetch → Tasks 2/3/4.
- Verificação `python -m unittest discover -s tests -v` → Tasks 2/3/4/5.

**Placeholder scan:** nenhum TBD/TODO; todos os steps têm código completo ou comandos exatos.

**Type consistency:** `IntervaloEntry(rotulo, group, duration_seconds)` consistente em models.py, fetch.py, formatter.py, testes. `format_intervalos_block(activity) -> str` consistente. `update_note(note_path, fm_data, body_block, template_path, intervalo_block=None)` consistente em writer.py, main.py, testes. `AW_START_INTERVALO`/`AW_END_INTERVALO` consistentes.
