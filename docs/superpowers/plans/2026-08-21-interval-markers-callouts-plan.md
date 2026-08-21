# Marcadores de Intervalo nos Callouts de Horários — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atualizar durações de intervalos dentro dos callouts existentes de `## ⏰ Horários` via marcadores `<!-- slug-start -->/<!-- slug-end -->`, com skeleton estático para Pausa Longa/Curta e migração das notas existentes.

**Architecture:** Formatter passa a gerar um dict `{slug → interior}`; writer substitui cirurgicamente o interior de cada par de marcadores HTML na nota (não substitui mais bloco inteiro). Script idempotente migra template + 167 notas diárias. Spec: `docs/superpowers/specs/2026-08-21-interval-markers-callouts-design.md`.

**Tech Stack:** Python 3.10+, stdlib (`re`, `argparse`, `pathlib`), `unittest`, `python-dotenv`. Vault `G:\Lucas` é git (migração reversível).

**Regra de ambiente (worktree):** Todo o código é desenvolvido no worktree `G:\Projetos\Worktrees-Proj\aw-interval-markers` (Task 0). Como deps já estão instaladas no venv principal, todos os comandos usam o interpretador absoluto `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe` (desvio consciente da instrução de reinstalar deps — não há `package.json` neste repo).

---

### Task 0: Worktree

**Files:** nenhum (setup)

- [ ] **Step 1: Criar worktree**

```powershell
git worktree add "G:\Projetos\Worktrees-Proj\aw-interval-markers" -b feat/interval-markers-callouts
```

Expected: diretório criado, branch `feat/interval-markers-callouts` a partir de `main`.

- [ ] **Step 2: Verificar interpretador**

```powershell
G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe --version
```

Expected: `Python 3.10+`. Todos os comandos abaixo usam esse caminho com `workdir` = raiz do worktree.

---

### Task 1: Formatter — `format_intervalo_contents`

**Files:**
- Modify: `src/handlers/formatter.py` (remover `format_intervalos_block`, linhas 127–154)
- Modify: `tests/test_formatter.py` (substituir classe `FormatIntervalosTests`, linhas 34–114)

- [ ] **Step 1: Substituir testes antigos pelos novos**

Em `tests/test_formatter.py`, apagar a classe `FormatIntervalosTests` inteira (do comentário de import na linha 34 até a linha 113) e colar no lugar:

```python
from data.models import IntervaloEntry
from handlers.formatter import INTERVALO_MARKERS, format_intervalo_contents


class FormatIntervaloContentsTests(unittest.TestCase):
    def _activity(self, intervalos):
        return DailyActivity(
            date=date(2026, 8, 21).isoformat(),
            total_seconds=0,
            active_seconds=0,
            intervalos=intervalos,
        )

    def test_seis_slugs_sempre_presentes(self):
        contents = format_intervalo_contents(self._activity([]))
        self.assertEqual(
            set(contents),
            {"pausa-longa", "pausa-curta", "café", "almoço", "jantar", "exercícios"},
        )

    def test_zero_ou_ausente_vazio(self):
        activity = self._activity([
            IntervaloEntry("Jantar", "Intervalo", 0),
            IntervaloEntry("Pausa Longa", "Intervalo", 30),  # < 60s -> "0m"
        ])
        contents = format_intervalo_contents(activity)
        self.assertEqual(contents["jantar"], "")
        self.assertEqual(contents["pausa-longa"], "")

    def test_positivo_minutos_formato_separador(self):
        activity = self._activity([
            IntervaloEntry("Café da manhã", "Intervalo", 1860),  # 31m
        ])
        self.assertEqual(format_intervalo_contents(activity)["café"], "· 31m")

    def test_positivo_horas_formato_separador(self):
        activity = self._activity([
            IntervaloEntry("Exercícios", "Exercícios", 8100),  # 2h15
        ])
        self.assertEqual(format_intervalo_contents(activity)["exercícios"], "· 2h15")

    def test_mapeamento_pausa_rapida_vira_pausa_curta(self):
        activity = self._activity([
            IntervaloEntry("Pausa Rápida", "Intervalo", 300),
        ])
        contents = format_intervalo_contents(activity)
        self.assertEqual(contents["pausa-curta"], "· 5m")
        self.assertNotIn("pausa-rápida", contents)
```

- [ ] **Step 2: Rodar teste para ver falhar**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -k FormatIntervaloContents -v` (workdir: raiz do worktree)

Expected: FAIL — `ImportError: cannot import name 'INTERVALO_MARKERS'`

- [ ] **Step 3: Implementar no formatter**

Em `src/handlers/formatter.py`:

3a. Trocar a linha de import (linha 3):

```python
from data.models import DailyActivity
```

3b. Adicionar após `TOP_N = 5`:

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

3c. Apagar a função `format_intervalos_block` inteira (linhas 127–154) e colocar no lugar:

```python
def format_intervalo_contents(activity: DailyActivity) -> dict[str, str]:
    """Slug de marcador -> conteúdo interior ('· XhYY' ou '' sem dados do dia)."""
    contents = {slug: "" for slug in INTERVALO_MARKERS.values()}
    for iv in activity.intervalos:
        slug = INTERVALO_MARKERS.get(iv.rotulo)
        if slug and seconds_to_display(iv.duration_seconds) != "0m":
            contents[slug] = f"· {seconds_to_display(iv.duration_seconds)}"
    return contents
```

- [ ] **Step 4: Rodar suíte completa**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v` (workdir: raiz do worktree)

Expected: PASS em tudo (formatter novo + demais suítes intactas).

- [ ] **Step 5: Commit**

```powershell
git add src/handlers/formatter.py tests/test_formatter.py
git commit -m "feat: format_intervalo_contents gera interior por slug de marcador"
```

---

### Task 2: Writer — `_merge_intervalo_markers`

**Files:**
- Modify: `src/handlers/writer.py`
- Modify: `tests/test_writer.py` (substituir classe `UpdateIntervalosTests`, linhas 42–174)

- [ ] **Step 1: Substituir testes de intervalos**

Em `tests/test_writer.py`: atualizar os imports (linha 8) para:

```python
from handlers.writer import (
    AW_END,
    AW_END_INTERVALO,
    AW_START,
    AW_START_INTERVALO,
    update_note,
)
```

Apagar a classe `UpdateIntervalosTests` inteira (linhas 42–174) e colar no lugar:

```python
class UpdateIntervaloMarkersTests(unittest.TestCase):
    def _note(self):
        return (
            "---\nnota: x\n---\n\n"
            "## ⏰ Horários\n\n"
            ">> [!alimentacao-fato] Café\n"
            ">> `$= dv.current().alimentacao?.[0] ? \"t\" : \"—\" ` <!-- café-start --><!-- café-end -->\n"
            "\n"
            "<div style=\"margin-bottom: 40px;\"></div>\n"
            "\n"
            f"{AW_START_INTERVALO}\n"
            "\n"
            "> [!multi-column]\n"
            ">> [!sumário]+  Pausa Longa \n"
            ">> <!-- pausa-longa-start --><!-- pausa-longa-end -->\n"
            ">>\n"
            ">\n"
            ">> [!sumário]+  Pausa Curta\n"
            ">> <!-- pausa-curta-start --><!-- pausa-curta-end -->\n"
            ">>\n"
            "\n"
            f"{AW_END_INTERVALO}\n"
            "\n"
            '<div style="margin-bottom: 20px;"></div>\n'
            "\n"
            "## 🗓️ Eventos\n\nconteudo manual\n"
        )

    def _update(self, note, contents):
        update_note(str(note), {"pc": {"total": "PT1H"}}, f"{AW_START}\npc\n{AW_END}", None, contents)

    def test_interior_substituido_preserva_marcadores_e_resto(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": "· 31m"})
            content = note.read_text(encoding="utf-8")
            self.assertIn("<!-- café-start -->· 31m<!-- café-end -->", content)
            self.assertIn("dv.current().alimentacao?.[0]", content)
            self.assertIn("conteudo manual", content)
            self.assertIn(">> [!sumário]+  Pausa Longa ", content)

    def test_slug_ausente_skip_sem_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": "· 31m", "pausa-longa": "· 12m"})  # nota tem pausa-longa
            content = note.read_text(encoding="utf-8")
            self.assertIn("<!-- pausa-longa-start -->· 12m<!-- pausa-longa-end -->", content)

    def test_todos_slugs_ausentes_nao_altera_horarios(self):
        # update_note sempre mexe em frontmatter/bloco PC; o que não pode
        # acontecer é criação de marcadores ou interior em nota sem eles.
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(
                "---\nnota: x\npc:\n  total: PT1H\n---\n\n## ⏰ Horários\n\nsem marcadores\n",
                encoding="utf-8",
            )
            self._update(note, {"café": "· 31m", "jantar": "· 5m"})
            content = note.read_text(encoding="utf-8")
            self.assertNotIn("café-start", content)
            self.assertNotIn("· 31m", content)
            self.assertIn("sem marcadores", content)

    def test_idempotencia(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": "· 31m"})
            primeira = note.read_text(encoding="utf-8")
            self._update(note, {"café": "· 31m"})
            self.assertEqual(note.read_text(encoding="utf-8"), primeira)

    def test_bloco_intervalos_nao_mais_substituido_wholesale(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {})
            content = note.read_text(encoding="utf-8")
            # skeleton estático sobrevive intacto quando não há dados
            self.assertIn(">> [!sumário]+  Pausa Curta", content)
            self.assertIn("<!-- pausa-curta-start --><!-- pausa-curta-end -->", content)

    def test_conteudo_vazio_mantem_marcadores_adjacentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-21.md"
            note.write_text(self._note(), encoding="utf-8")
            self._update(note, {"café": ""})
            content = note.read_text(encoding="utf-8")
            self.assertIn("<!-- café-start --><!-- café-end -->", content)
```

- [ ] **Step 2: Rodar teste para ver falhar**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -k UpdateIntervaloMarkers -v` (workdir: raiz do worktree)

Expected: FAIL/ERROR — `TypeError: update_note() takes ... positional argument` ou interior não substituído (comportamento antigo ignora dict).

- [ ] **Step 3: Implementar no writer**

Em `src/handlers/writer.py`:

3a. Trocar assinatura e docstring de `update_note` (linhas 17–30):

```python
def update_note(
    note_path: str,
    fm_data: dict,
    body_block: str,
    template_path: str | None = None,
    intervalo_contents: dict[str, str] | None = None,
) -> None:
    """Atualiza nota diária com dados do ActivityWatch.

    - Frontmatter: deep merge da chave 'pc'
    - Corpo (PC): insere/substitui bloco entre aw:start e aw:end em ## Dados
    - Corpo (Intervalos): substitui o interior de cada par
      <!-- slug-start -->/<!-- slug-end --> (se intervalo_contents fornecido).
      O bloco aw:start-intervalos/end-intervalos NÃO é mais tocado wholesale.
    """
```

3b. Substituir o merge de intervalos (linhas 50–58):

```python
    # Merge corpo (Intervalos): interior por métrica
    if intervalo_contents is not None:
        body = _merge_intervalo_markers(body, intervalo_contents)
```

3c. Adicionar ao final do arquivo:

```python
def _merge_intervalo_markers(body: str, contents: dict[str, str]) -> str:
    """Substitui apenas o interior de cada par de marcadores por métrica.

    Marcadores ausentes geram warning e são pulados (nota pode ser antiga
    ou métrica sem callout correspondente). Idempotente por construção.
    """
    for slug, inner in contents.items():
        pattern = re.compile(
            rf"(<!-- {re.escape(slug)}-start -->).*?(<!-- {re.escape(slug)}-end -->)",
            re.DOTALL,
        )
        body, count = pattern.subn(
            lambda m, inner=inner: f"{m.group(1)}{inner}{m.group(2)}", body
        )
        if count == 0:
            logger.warning("Marcadores de '%s' ausentes na nota", slug)
        elif inner:
            logger.info("Intervalo '%s' atualizado (%s)", slug, inner.strip())
    return body
```

Constantes `AW_START_INTERVALO`/`AW_END_INTERVALO` permanecem (export usada por testes; delimitam visualmente a seção).

- [ ] **Step 4: Rodar suíte completa**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v` (workdir: raiz do worktree)

Expected: PASS em tudo.

- [ ] **Step 5: Commit**

```powershell
git add src/handlers/writer.py tests/test_writer.py
git commit -m "feat: writer substitui interior de marcadores por métrica"
```

---

### Task 3: Wiring no `main.py`

**Files:**
- Modify: `src/main.py:10,63,67`

- [ ] **Step 1: Atualizar import (linha 10)**

```python
from handlers.formatter import format_body, format_frontmatter, format_intervalo_contents
```

- [ ] **Step 2: Atualizar chamadas (linhas 63 e 67)**

```python
    intervalo_contents = format_intervalo_contents(activity)
```

e

```python
        update_note(note_path, fm_data, body_block, template_path, intervalo_contents)
```

- [ ] **Step 3: Verificação sintática**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import main"` (workdir: raiz do worktree)

Expected: sem saída/erro.

- [ ] **Step 4: Commit**

```powershell
git add src/main.py
git commit -m "feat: main usa format_intervalo_contents no sync"
```

---

### Task 4: Script de migração

**Files:**
- Create: `scripts/migrate_interval_markers.py`
- Create: `tests/test_migrate_interval_markers.py`

- [ ] **Step 1: Escrever testes**

Criar `tests/test_migrate_interval_markers.py`:

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from migrate_interval_markers import migrate_content


NOTE_FIXTURE = (
    "---\nnota: x\n---\n\n"
    "## ⏰ Horários\n\n"
    ">> [!alimentacao-fato] Café\n"
    ">> `$= dv.current().alimentacao?.[0] ? \"t\" : \"—\" `\n"
    ">\n"
    ">> [!alimentacao-fato] Almoço\n"
    ">> `$= dv.current().alimentacao?.[1] ? \"t\" : \"—\" `\n"
    "\n"
    '<div style="margin-bottom: 40px;"></div>\n'
    "\n"
    "## 🗓️ Eventos\n\nconteudo\n"
)

OLD_BLOCK_FIXTURE = (
    "## ⏰ Horários\n\n"
    ">> [!alimentacao-fato] Café\n"
    ">> `$= q `\n"
    "\n"
    '<div style="margin-bottom: 40px;"></div>\n'
    "\n"
    "<!-- aw:start-intervalos -->\n"
    "> [!multi-column]\n"
    ">> [!pause]+  Intervalo\n"
    ">> - Café da manhã (31m)\n"
    ">\n"
    "<!-- aw:end-intervalos -->\n"
    "\n"
    '<div style="margin-bottom: 20px;"></div>\n'
    "\n"
    "## 🗓️ Eventos\n\nconteudo\n"
)


class MigrateContentTests(unittest.TestCase):
    def test_insere_inline_nos_callouts_e_skeleton_antes_de_eventos(self):
        new, warnings = migrate_content(NOTE_FIXTURE)
        self.assertEqual(warnings, [])
        self.assertIn('` <!-- café-start --><!-- café-end -->', new)
        self.assertIn('` <!-- almoço-start --><!-- almoço-end -->', new)
        idx_div40 = new.index('<div style="margin-bottom: 40px;"></div>')
        idx_start = new.index("<!-- aw:start-intervalos -->")
        idx_end = new.index("<!-- aw:end-intervalos -->")
        idx_div20 = new.index('<div style="margin-bottom: 20px;"></div>')
        idx_eventos = new.index("## 🗓️ Eventos")
        self.assertLess(idx_div40, idx_start)
        self.assertLess(idx_start, idx_end)
        self.assertLess(idx_end, idx_div20)
        self.assertLess(idx_div20, idx_eventos)
        self.assertEqual(new.count("pausa-longa-start"), 1)
        self.assertIn("[!sumário]+  Pausa Longa", new)
        self.assertIn("[!sumário]+  Pausa Curta", new)
        # div40 não duplicado
        self.assertEqual(new.count('<div style="margin-bottom: 40px;"></div>'), 1)

    def test_idempotente(self):
        once, _ = migrate_content(NOTE_FIXTURE)
        twice, warnings = migrate_content(once)
        self.assertEqual(twice, once)
        self.assertEqual(warnings, [])

    def test_substitui_bloco_antigo_pelo_skeleton(self):
        new, warnings = migrate_content(OLD_BLOCK_FIXTURE)
        self.assertEqual(warnings, [])
        self.assertNotIn("- Café da manhã (31m)", new)
        self.assertNotIn("[!pause]", new)
        self.assertIn("pausa-longa-start", new)
        self.assertEqual(new.count('<div style="margin-bottom: 40px;"></div>'), 1)
        self.assertEqual(new.count('<div style="margin-bottom: 20px;"></div>'), 1)

    def test_nota_sem_ancoras_avisa_e_nao_altera(self):
        texto = "# Dia\n\nconteudo solto\n"
        new, warnings = migrate_content(texto)
        self.assertEqual(new, texto)
        self.assertTrue(any("Eventos" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar teste para ver falhar**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -k MigrateContent -v` (workdir: raiz do worktree)

Expected: FAIL — `ModuleNotFoundError: No module named 'migrate_interval_markers'`

- [ ] **Step 3: Criar o script**

Criar `scripts/migrate_interval_markers.py`:

```python
"""Migra notas diárias e o template para marcadores de intervalo por métrica.

Insere <!-- {slug}-start -->/<!-- {slug}-end --> nos callouts Café/Almoço/Jantar/
Exercícios de ## ⏰ Horários e o skeleton estático de Pausa Longa/Pausa Curta.
Idempotente. Reversível via git do vault (G:\Lucas).
"""
import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_REL = os.path.join(
    "99_Sistema", "_templates", "Nota Inteira", "Jornada", "Nota Diária 2_ISO.md"
)
NOTES_REL = os.path.join("01_Arquivos", "Jornada")

AW_START_INTERVALOS = "<!-- aw:start-intervalos -->"
AW_END_INTERVALOS = "<!-- aw:end-intervalos -->"

INLINE_TARGETS = [
    ("café", re.compile(r"^>> \[!alimentacao-fato\]\s*Café\b.*$", re.MULTILINE)),
    ("almoço", re.compile(r"^>> \[!alimentacao-fato\]\s*Almoço\b.*$", re.MULTILINE)),
    ("jantar", re.compile(r"^>> \[!alimentacao-fato\]\s*Jantar\b.*$", re.MULTILINE)),
    ("exercícios", re.compile(r"^>> \[!exercicios-fato\]\s*Exerc[ií]cios\b.*$", re.MULTILINE)),
]

SKELETON_INNER = (
    "> [!multi-column]\n"
    ">> [!sumário]+  Pausa Longa \n"
    ">> <!-- pausa-longa-start --><!-- pausa-longa-end -->\n"
    ">>\n"
    ">\n"
    ">> [!sumário]+  Pausa Curta\n"
    ">> <!-- pausa-curta-start --><!-- pausa-curta-end -->\n"
    ">>"
)

DIV20 = '<div style="margin-bottom: 20px;"></div>'
DIV40 = '<div style="margin-bottom: 40px;"></div>'
EVENTOS_RE = re.compile(r"^#{2,3} [^\n]*Eventos[^\n]*$", re.MULTILINE)
CALLOUT_LINE_RE = re.compile(r"^>>[^\n]*$", re.MULTILINE)


def _append_marker_after_query(text: str, title_match: re.Match, slug: str) -> str | None:
    """Acha a linha de query seguinte ao título do callout e anexa os marcadores."""
    for cand in CALLOUT_LINE_RE.finditer(text, title_match.end()):
        line = cand.group(0)
        if "[!" in line:
            return None  # chegou em outro callout sem achar query
        if "`" in line:
            abs_start, abs_end = cand.span()
            prefix = text[:abs_end].rstrip()
            suffix = text[abs_end:]
            return (
                prefix
                + f" <!-- {slug}-start --><!-- {slug}-end -->"
                + suffix
            )
    return None


def migrate_content(text: str) -> tuple[str, list[str]]:
    """Aplica a migração em um conteúdo. Retorna (novo_texto, avisos)."""
    warnings: list[str] = []
    original = text

    # 1) Marcadores inline nos callouts existentes
    for slug, title_re in INLINE_TARGETS:
        if f"<!-- {slug}-start -->" in text:
            continue
        m = title_re.search(text)
        if not m:
            warnings.append(f"callout '{slug}' não encontrado")
            continue
        new_text = _append_marker_after_query(text, m, slug)
        if new_text is None:
            warnings.append(f"linha de query do '{slug}' não encontrada")
            continue
        text = new_text

    # 2) Skeleton de Pausas
    block = f"{AW_START_INTERVALOS}\n\n{SKELETON_INNER}\n\n{AW_END_INTERVALOS}"
    if AW_START_INTERVALOS in text:
        if "pausa-longa-start" not in text:
            block_re = re.compile(
                rf"{re.escape(AW_START_INTERVALOS)}.*?{re.escape(AW_END_INTERVALOS)}",
                re.DOTALL,
            )
            # lambda => reposição literal (sem processar escapes de re.sub)
            text = block_re.sub(lambda _m: block, text)
    else:
        ev = EVENTOS_RE.search(text)
        if not ev:
            warnings.append("seção Eventos não encontrada")
        else:
            head = text[: ev.start()].rstrip()
            tail = text[ev.start():]
            pieces = []
            if not (head.endswith(DIV40) or head.endswith(DIV20)):
                pieces.append(DIV40)
            pieces.append(block)
            pieces.append(DIV20)
            text = head + "\n\n" + "\n\n".join(pieces) + "\n\n" + tail

    return text, warnings


def collect_files(vault: Path) -> list[Path]:
    files = [vault / TEMPLATE_REL]
    files.extend(sorted((vault / NOTES_REL).rglob("*.md")))
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", default=None, help="Raiz do vault (default: VAULT_PATH)")
    parser.add_argument("--dry-run", action="store_true", help="Não escreve, só lista")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    vault = Path(args.vault_root or os.environ.get("VAULT_PATH", "")).resolve()
    if not vault.is_dir():
        sys.exit(f"Vault não encontrado: {vault}")

    migrated = 0
    for path in collect_files(vault):
        rel = path.relative_to(vault).as_posix()
        original = path.read_text(encoding="utf-8")
        new_text, warnings = migrate_content(original)
        for w in warnings:
            print(f"[aviso] {rel}: {w}")
        if new_text == original:
            continue
        migrated += 1
        if args.dry_run:
            print(f"[seco ] {rel}")
        else:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            print(f"[ok   ] {rel}")

    acao = "seriam migrados" if args.dry_run else "migrados"
    print(f"\n{migrated} arquivo(s) {acao}")


if __name__ == "__main__":
    main()
```

Atenção: `block_re.sub(...)` com string de reposição contém `\n` literais que `re.sub` interpretaria como escapes se passados cru; por isso o `.replace("\\", "\\\\")` acima NÃO é suficiente para `\n` (que é newline real, não barra-n). Implementação correta da sub:

```python
            text = block_re.sub(lambda _m: block, text)
```

Use `lambda _m: block` (função ⇒ reposição literal, sem escape processing). Substitua a linha do `sub` pela versão com lambda.

- [ ] **Step 4: Rodar suíte completa**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v` (workdir: raiz do worktree)

Expected: PASS em tudo.

- [ ] **Step 5: Smoke do CLI com vault fake**

```powershell
New-Item -ItemType Directory -Force -Path "G:\Projetos\activitywatch_obsidian\.tmp-vault-fake\01_Arquivos\Jornada\2026\02", "G:\Projetos\activitywatch_obsidian\.tmp-vault-fake\99_Sistema\_templates\Nota Inteira\Jornada" | Out-Null
Copy-Item "G:\Lucas\01_Arquivos\Jornada\2026\02\2026-02-14.md" "G:\Lucas\01_Arquivos\Jornada\2026\02\2026-02-15.md" "G:\Projetos\activitywatch_obsidian\.tmp-vault-fake\01_Arquivos\Jornada\2026\02\"
Copy-Item "G:\Lucas\99_Sistema\_templates\Nota Inteira\Jornada\Nota Diária 2_ISO.md" "G:\Projetos\activitywatch_obsidian\.tmp-vault-fake\99_Sistema\_templates\Nota Inteira\Jornada\"
```

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe scripts/migrate_interval_markers.py --dry-run --vault-root G:\Projetos\activitywatch_obsidian\.tmp-vault-fake` (workdir: raiz do worktree)

Expected: 3 linhas `[seco ]` (template + 2 notas). Depois limpar:

```powershell
Remove-Item -Recurse -Force "G:\Projetos\activitywatch_obsidian\.tmp-vault-fake"
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/migrate_interval_markers.py tests/test_migrate_interval_markers.py
git commit -m "feat: script de migração para marcadores de intervalo"
```

---

### Task 5: Migração do vault real

**Files:** somente arquivos do vault `G:\Lucas` (fora do repo)

- [ ] **Step 1: Preflight — árvore do vault limpa**

```powershell
git -C G:\Lucas status --porcelain
```

Expected: saída vazia. Se NÃO vazia: PARAR e perguntar a Lucas se pode prosseguir (mudanças pendentes dele se misturariam com a migração no rollback).

- [ ] **Step 2: Dry-run completo**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe scripts/migrate_interval_markers.py --dry-run` (workdir: raiz do worktree)

Expected: ~168 linhas `[seco ]` (template + 167 notas); `[aviso]` apenas para `2026-03-31.md`, `2026-05-03.md`, `2026-07-29.md`; contagem final coerente.

- [ ] **Step 3: Aplicar**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe scripts/migrate_interval_markers.py` (workdir: raiz do worktree)

Expected: mesmos arquivos agora com `[ok   ]`.

- [ ] **Step 4: Spot-check**

```powershell
Select-String -Path "G:\Lucas\99_Sistema\_templates\Nota Inteira\Jornada\Nota Diária 2_ISO.md" -Pattern "café-start|pausa-longa-start|sumário" | Select-Object -First 5
Select-String -Path "G:\Lucas\01_Arquivos\Jornada\2026\02\2026-02-14.md" -Pattern "café-start|pausa-curta-start" 
Select-String -Path "G:\Lucas\01_Arquivos\Jornada\2026\08\2026-08-21.md" -Pattern "sumário|pause"
git -C G:\Lucas diff --stat | Select-Object -Last 3
```

Expected: template com marcadores + skeleton sumário; nota antiga com inline markers + skeleton; nota de hoje com `[!pause]` antigo trocado por `[!sumário]`; diff ~169 arquivos.

- [ ] **Step 5: Re-executar script (idempotência real)**

Run: `--dry-run` de novo.

Expected: `0 arquivo(s) seriam migrados`.

Rollback se algo errado: `git -C G:\Lucas restore .`

---

### Task 6: Verificação final

- [ ] **Step 1: Suíte completa no worktree**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe -m unittest discover -s tests -v` (workdir: raiz do worktree)

Expected: todas PASS.

- [ ] **Step 2: Sync real (requer ActivityWatch rodando)**

Run: `G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe src/main.py --date 2026-08-21` (workdir: raiz do worktree)

Expected: log `Sync concluído`. Nota de hoje mostra `· XhYY` dentro dos callouts Café/Jantar/etc. quando houver dados; Pausas com duração quando houver; nada apagado (queries dataview intactas).

Se AW estiver offline: pular e marcar como verificação pendente para o usuário.

- [ ] **Step 3: Push da branch**

```powershell
git push -u origin feat/interval-markers-callouts
```

(NÃO fazer merge nem copiar arquivos para `main` — PR/review fica a cargo de Lucas.)
