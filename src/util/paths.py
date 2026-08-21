import os
from datetime import date


def daily_note_path(vault_path: str, target_date: date) -> str:
    """Resolve caminho da nota diária: 01_Arquivos/Jornada/YYYY/MM/YYYY-MM-DD.md"""
    return os.path.join(
        vault_path,
        "01_Arquivos",
        "Jornada",
        target_date.strftime("%Y"),
        target_date.strftime("%m"),
        f"{target_date.isoformat()}.md",
    )
