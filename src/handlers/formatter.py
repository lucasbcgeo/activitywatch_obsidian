import logging

from data.models import DailyActivity
from util.time_fmt import seconds_to_display, seconds_to_iso

logger = logging.getLogger("aw-sync.formatter")

TOP_N = 5


def format_frontmatter(activity: DailyActivity) -> dict:
    """Gera dict para merge no frontmatter sob chave 'pc'. Durações em ISO 8601."""
    import os
    min_apps = int(os.environ.get("MIN_MINUTES_APPS", "1")) * 60
    min_web = int(os.environ.get("MIN_MINUTES_WEB", "1")) * 60
    min_estudo = int(os.environ.get("MIN_MINUTES_ESTUDO", "1")) * 60
    
    ignore_apps = [x.strip().lower() for x in os.environ.get("IGNORE_APPS", "").split(",") if x.strip()]
    ignore_web = [x.strip().lower() for x in os.environ.get("IGNORE_WEB", "").split(",") if x.strip()]

    pc = {
        "tempo_total": seconds_to_iso(activity.total_seconds),
        "tempo_ativo": seconds_to_iso(activity.active_seconds),
    }

    if activity.uncategorized:
        pc["apps"] = [
            {app.name: seconds_to_iso(app.duration_seconds)}
            for app in activity.uncategorized
            if app.duration_seconds >= min_apps and app.name.lower() not in ignore_apps
        ]

    if activity.web:
        pc["web"] = [
            {w.domain: seconds_to_iso(w.duration_seconds)}
            for w in activity.web
            if w.duration_seconds >= min_web and w.domain.lower() not in ignore_web
        ]

    return {"pc": pc}


def format_body(activity: DailyActivity) -> str:
    """Gera bloco Markdown com callouts multi-column. Durações em formato legível."""
    lines = []
    ativo = seconds_to_display(activity.active_seconds)
    total = seconds_to_display(activity.total_seconds)

    lines.append("<!-- aw:start -->")
    lines.append(f"### PC  **Tempo ativo:** {ativo} / **Total:** {total}")
    lines.append("")
    lines.append("> [!multi-column]")

    # Apps
    apps = activity.uncategorized[:TOP_N]
    apps_total = seconds_to_display(sum(a.duration_seconds for a in apps))
    lines.append(">> [!abstract]+  Apps")
    lines.append(f">> **Tempo ativo:** {apps_total}")
    for a in apps:
        lines.append(f">> - {a.name} ({seconds_to_display(a.duration_seconds)})")
    lines.append(">")

    # Web
    if activity.web:
        web_items = activity.web[:TOP_N]
        web_total = seconds_to_display(sum(w.duration_seconds for w in web_items))
        lines.append(">> [!example]+  Web")
        lines.append(f">> **Tempo ativo:** {web_total}")
        for w in web_items:
            lines.append(f">> - {w.domain} ({seconds_to_display(w.duration_seconds)})")
        lines.append(">")

    # Estudo
    if activity.study:
        study_items = activity.study[:TOP_N]
        study_total = seconds_to_display(sum(s.duration_seconds for s in study_items))
        lines.append(">> [!info]+  Estudo")
        lines.append(f">> **Tempo ativo:** {study_total}")
        for s in study_items:
            lines.append(f">> - {s.name} ({seconds_to_display(s.duration_seconds)})")
        lines.append(">")

    # Resumo por categorias (lista com subseções agrupadas)
    if activity.categories and activity.total_seconds > 0:
        lines.append("")
        lines.append("No geral, podemos resumir em:")

        # Agrupar: "Programando > Visual" → parent "Programando", child "Visual"
        groups: dict[str, list[tuple[str, float, float]]] = {}
        standalone: list[tuple[str, float, float]] = []

        for c in activity.categories:
            pct = (c.total_seconds / activity.total_seconds) * 100
            if pct < 1 or c.name == "Uncategorized":
                continue
            if " > " in c.name:
                parent, child = c.name.split(" > ", 1)
                groups.setdefault(parent, []).append((child, pct, c.total_seconds))
            else:
                standalone.append((c.name, pct, c.total_seconds))

        # Standalone items
        for name, pct, _ in standalone:
            lines.append(f"- {name} **{pct:.0f}%**")

        # Grouped items
        for parent, children in groups.items():
            parent_pct = sum(p for _, p, _ in children)
            lines.append(f"- {parent} **{parent_pct:.0f}%**")
            for child, pct, _ in children:
                lines.append(f"    - {child} **{pct:.0f}%**")

    lines.append("")
    lines.append("<!-- aw:end -->")
    return "\n".join(lines)
