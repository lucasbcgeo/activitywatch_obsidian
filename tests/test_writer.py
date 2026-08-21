import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from handlers.writer import AW_END, AW_START, update_note


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


if __name__ == "__main__":
    unittest.main()
