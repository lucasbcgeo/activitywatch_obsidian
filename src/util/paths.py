import os
from datetime import date


def daily_note_path(vault_path: str, target_date: date) -> str:
    """Resolve caminho da nota diária: 02_Notas/Jornada/YYYY/MM/YYYY-MM-DD.md"""
    return os.path.join(
        vault_path,
        "02_Notas",
        "Jornada",
        target_date.strftime("%Y"),
        target_date.strftime("%m"),
        f"{target_date.isoformat()}.md",
    )
