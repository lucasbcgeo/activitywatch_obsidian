"""Recalcula médias em notas periódicas a partir das diárias do período."""

import logging
import os
import re
from calendar import monthrange
from datetime import date, timedelta

from util.paths import daily_note_path
from util.yaml_helpers import deep_merge, parse_note, rebuild_note

logger = logging.getLogger("aw-sync.periodic")

_ISO_DURATION_RE = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")

# (destino, fonte): caminho-tupla; elemento único com ponto é chave YAML plana
# literal (ex.: 'exercicio.media' nas semanais reais), nunca dict aninhado.
MEDIA_FIELDS = [
    (("pc", "tempo_ativo_media"), ("pc", "tempo_ativo")),
    (("pc", "tempo_total_media"), ("pc", "tempo_total")),
    (("cel", "tempo_total_media"), ("cel", "tempo_total")),
    (("tempo_tela_media",), ("tempo_tela",)),
    (("redesSociais_media",), ("redesSociais",)),
]

NUMERIC_FIELDS = [
    (("exercicio.media",), ("exercicio",)),
    (("lazer.media",), ("lazer",)),
    (("leitura.media",), ("leitura",)),
    (("procrastinacao.media",), ("procrastinacao",)),
]

_TRUE_STRINGS = {"true", "1", "sim", "yes", "y"}
_FALSE_STRINGS = {"false", "0", "nao", "não", "no", "n"}


def parse_iso_duration(value) -> int | None:
    """Duração ISO 'PT{n}H{n}M{n}S' -> segundos; None se não casar."""
    if value is None:
        return None
    match = _ISO_DURATION_RE.match(str(value).strip())
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def format_iso_duration(seconds: int) -> str:
    """Segundos -> 'PT{n}H{n}M{n}S' omitindo partes zero; zero -> 'PT0S'."""
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    parts = ""
    if hours:
        parts += f"{hours}H"
    if minutes:
        parts += f"{minutes}M"
    if secs:
        parts += f"{secs}S"
    return f"PT{parts}" if parts else "PT0S"


def numeric_value(raw) -> float | None:
    """Bool/int/float/string-numérica -> float (bool true=1.0); senão None."""
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in _TRUE_STRINGS:
            return 1.0
        if text in _FALSE_STRINGS:
            return 0.0
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None
    return None


def nested_get(fm: dict, path: tuple[str, ...]):
    node = fm
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def nested_set(fm: dict, path: tuple[str, ...], value) -> None:
    node = fm
    for key in path[:-1]:
        child = node.get(key)
        if not isinstance(child, dict):
            child = {}
            node[key] = child
        node = child
    node[path[-1]] = value
