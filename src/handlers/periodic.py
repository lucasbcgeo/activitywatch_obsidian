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


def period_bounds(target: date) -> list[tuple[str, date, date]]:
    """Períodos que contêm target: semana ISO, mês, trimestre e ano.

    Slugs seguem os títulos reais das periódicas: {ano}-Www, {ano}-{mm},
    {ano}-Q{n}, {ano}. Semana usa ano/semana ISO (pode virar o ano civil).
    """
    iso_year, iso_week, _ = target.isocalendar()
    monday = target - timedelta(days=target.isoweekday() - 1)

    month_start = target.replace(day=1)
    month_end = target.replace(day=monthrange(target.year, target.month)[1])

    quarter = (target.month - 1) // 3 + 1
    first_month = 3 * quarter - 2
    last_month = 3 * quarter
    quarter_start = date(target.year, first_month, 1)
    quarter_end = date(target.year, last_month, monthrange(target.year, last_month)[1])

    return [
        (f"{iso_year}-W{iso_week:02d}", monday, monday + timedelta(days=6)),
        (f"{target.year}-{target.month:02d}", month_start, month_end),
        (f"{target.year}-Q{quarter}", quarter_start, quarter_end),
        (str(target.year), date(target.year, 1, 1), date(target.year, 12, 31)),
    ]


def candidate_paths(vault: str, slug: str) -> list[str]:
    """Caminhos possíveis da periódica do slug; atualizar todos que existirem."""
    base = os.path.join(vault, "01_Arquivos", "Jornada")
    if re.fullmatch(r"\d{4}-W\d{2}", slug):
        year = slug[:4]
        return [os.path.join(base, year, "Semanas", f"{slug}.md")]
    if re.fullmatch(r"\d{4}-Q\d", slug):
        year = slug[:4]
        return [os.path.join(base, year, f"{slug}.md")]
    if re.fullmatch(r"\d{4}-\d{2}", slug):
        year = slug[:4]
        return [os.path.join(base, year, f"{slug}.md"), os.path.join(base, f"{slug}.md")]
    return [os.path.join(base, f"{slug}.md"), os.path.join(base, slug, f"{slug}.md")]


def _source_values(raw) -> list:
    """Normaliza valor-fonte em lista de escalares (redesSociais pode ser lista)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item for item in raw if item is not None]
    return [raw]


def _compute_medias(frontmatters: list[dict]) -> dict:
    """Médias escalares das diárias do período.

    Denominador = dias com valor parseável (mesma regra dos *_TP_media.js).
    Campo sem nenhum dia válido não gera chave (periódica mantém valor atual).
    """
    medias: dict = {}

    for dest, source in MEDIA_FIELDS:
        seconds = [
            parsed
            for fm in frontmatters
            for raw in _source_values(nested_get(fm, source))
            if (parsed := parse_iso_duration(raw)) is not None
        ]
        if seconds:
            media = round(sum(seconds) / len(seconds))
            nested_set(medias, dest, format_iso_duration(media))

    for dest, source in NUMERIC_FIELDS:
        values = [
            number
            for fm in frontmatters
            if (number := numeric_value(nested_get(fm, source))) is not None
        ]
        if values:
            nested_set(medias, dest, round(sum(values) / len(values), 2))

    return medias


def _collect_daily_frontmatters(vault: str, start: date, end: date) -> list[dict]:
    """Frontmatters das diárias de start..end; ausentes ou ilegíveis são ignoradas."""
    frontmatters = []
    day = start
    while day <= end:
        path = daily_note_path(vault, day)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    frontmatter, _body = parse_note(fh.read())
            except Exception:
                logger.warning("Diária ilegível, ignorada: %s", path)
                day += timedelta(days=1)
                continue
            if frontmatter:
                frontmatters.append(frontmatter)
        day += timedelta(days=1)
    return frontmatters


def _rewrite_with_medias(note_path: str, medias: dict) -> bool:
    """Merge das médias no frontmatter preservando corpo. False = nada mudou."""
    with open(note_path, encoding="utf-8") as fh:
        content = fh.read()
    frontmatter, body = parse_note(content)
    merged = deep_merge(frontmatter, medias)
    result = rebuild_note(merged, body)
    if result == content:
        return False
    with open(note_path, "w", encoding="utf-8") as fh:
        fh.write(result)
    return True


def update_periodic_notes(target_date: date, vault: str) -> list[str]:
    """Atualiza periódicas EXISTENTES contendo target_date; retorna as alteradas.

    Nunca cria arquivo novo; ausente = pula silenciosamente. Sem diárias com
    valores no período, nenhuma média é gerada e nada é escrito.
    """
    updated = []
    seen: set[str] = set()
    for slug, start, end in period_bounds(target_date):
        medias = _compute_medias(_collect_daily_frontmatters(vault, start, end))
        if not medias:
            continue
        for path in candidate_paths(vault, slug):
            normalized = os.path.normpath(path)
            if normalized in seen or not os.path.isfile(path):
                continue
            seen.add(normalized)
            if _rewrite_with_medias(path, medias):
                updated.append(path)
                logger.info("Periódica atualizada: %s", path)
    return updated
