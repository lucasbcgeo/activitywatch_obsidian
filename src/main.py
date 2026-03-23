import argparse
import os
import sys
from datetime import date

from dotenv import load_dotenv
from aw_client import ActivityWatchClient

from handlers.fetch import fetch_daily
from handlers.formatter import format_body, format_frontmatter
from handlers.writer import update_note
from log import setup_logging
from util.paths import daily_note_path


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    logger = setup_logging()

    parser = argparse.ArgumentParser(
        description="Sync ActivityWatch → Obsidian daily note"
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        help="Data alvo no formato YYYY-MM-DD (padrão: hoje)",
    )
    args = parser.parse_args()

    target_date: date = args.date
    vault_path = os.environ.get("VAULT_PATH", "/path/to/vault")
    aw_host = os.environ.get("AW_HOST", "localhost")
    aw_port = int(os.environ.get("AW_PORT", "5600"))

    note_path = daily_note_path(vault_path, target_date)
    if not os.path.isfile(note_path):
        logger.error("Nota diária não encontrada: %s", note_path)
        sys.exit(1)

    logger.info("Sincronizando %s → %s", target_date.isoformat(), note_path)

    # Fetch
    client = ActivityWatchClient(
        "aw-obsidian-sync", testing=False, host=aw_host, port=aw_port
    )

    try:
        activity = fetch_daily(client, target_date)
    except Exception:
        logger.exception("Erro ao buscar dados do ActivityWatch")
        sys.exit(1)

    # Format
    fm_data = format_frontmatter(activity)
    body_block = format_body(activity)

    # Write
    try:
        update_note(note_path, fm_data, body_block)
    except Exception:
        logger.exception("Erro ao atualizar nota")
        sys.exit(1)

    logger.info("Sync concluído com sucesso!")


if __name__ == "__main__":
    main()
