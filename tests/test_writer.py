import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from handlers.writer import AW_END, AW_END_INTERVALO, AW_START, AW_START_INTERVALO, update_note


class UpdateNoteTests(unittest.TestCase):
    def test_creates_missing_daily_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "Lucas" / "01_Arquivos" / "Jornada" / "2026" / "07" / "2026-07-02.md"

            update_note(str(note), {"pc": {"total": "PT1H"}}, f"{AW_START}\nbody\n{AW_END}")

            content = note.read_text(encoding="utf-8")
            self.assertIn("pc:", content)
            self.assertIn(f"{AW_START}\nbody\n{AW_END}", content)

    def test_creates_missing_daily_note_from_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.md"
            template.write_text("<%* templater code %>\n\n# Planejamento\n", encoding="utf-8")
            note = Path(tmp) / "2026" / "07" / "2026-07-02.md"

            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\nbody\n{AW_END}",
                str(template),
            )

            content = note.read_text(encoding="utf-8")
            self.assertIn("journal-date: 2026-07-02", content)
            self.assertIn("uri: obsidian://open?vault=Lucas&file=2026-07-02", content)
            self.assertIn("# Planejamento", content)
            self.assertNotIn("templater code", content)


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
                f"{AW_START_INTERVALO}\n> [!pause]+  Intervalo\n> - Jantar (36m)\n{AW_END_INTERVALO}"
            )
            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\npc\n{AW_END}",
                None,
                intervalo_block,
            )
            content = note.read_text(encoding="utf-8")
            self.assertIn("Jantar (36m)", content)
            self.assertIn(AW_START_INTERVALO, content)
            self.assertIn(AW_END_INTERVALO, content)

    def test_insere_bloco_intervalos_em_secao_se_sem_marcadores(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "2026-08-20.md"
            note.write_text(self._base_note(with_markers=False), encoding="utf-8")
            intervalo_block = (
                f"{AW_START_INTERVALO}\n> [!pause]+  Intervalo\n> - Jantar (36m)\n{AW_END_INTERVALO}"
            )
            update_note(
                str(note),
                {"pc": {"total": "PT1H"}},
                f"{AW_START}\npc\n{AW_END}",
                None,
                intervalo_block,
            )
            content = note.read_text(encoding="utf-8")
            self.assertIn("Jantar (36m)", content)
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


if __name__ == "__main__":
    unittest.main()
