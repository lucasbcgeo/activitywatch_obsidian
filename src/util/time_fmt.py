def seconds_to_iso(seconds: float) -> str:
    """Converte segundos para duração ISO 8601 (ex: PT2H15M)."""
    total = int(round(seconds))
    if total <= 0:
        return "PT0M"
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    parts = "PT"
    if h:
        parts += f"{h}H"
    if m:
        parts += f"{m}M"
    if not h and not m:
        parts += f"{s}S"
    return parts


def seconds_to_display(seconds: float) -> str:
    """Converte segundos para formato legível (ex: 2h15)."""
    total = int(round(seconds))
    if total <= 0:
        return "0m"
    h, remainder = divmod(total, 3600)
    m = remainder // 60
    if h <= 0:
        return f"{m}m"
    return f"{h}h{m:02d}"
