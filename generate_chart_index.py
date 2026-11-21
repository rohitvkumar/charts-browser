#!/usr/bin/env python3
"""Generate styled index pages grouping chart files by date (newest first)."""
import re
from datetime import datetime
from pathlib import Path

CHART_DIRS = [
    Path("/usr/share/nginx/html/weekly_charts"),
    Path("/usr/share/nginx/html/daily_charts"),
]

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def parse_date(filename: str) -> str:
    """Extract YYYY-MM-DD from a chart filename."""
    m = DATE_RE.match(filename)
    if m:
        return m.group(1)
    return "unknown"


def sort_key(path: Path):
    """Sort by date desc, then filename asc."""
    d = parse_date(path.name)
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        dt = datetime.min
    return (-dt.toordinal(), path.name.lower())


for chart_dir in CHART_DIRS:
    if not chart_dir.exists():
        continue

    files = sorted(
        f for f in chart_dir.iterdir()
        if f.suffix.lower() == ".html" and f.name != "index.html"
    )
    if not files:
        index_path = chart_dir / "index.html"
        if index_path.exists():
            index_path.unlink()
        continue

    # Group by date, newest first
    groups = {}
    for f in files:
        d = parse_date(f.name)
        groups.setdefault(d, []).append(f)

    ordered_dates = sorted(groups.keys(), key=lambda d: (
        datetime.strptime(d, "%Y-%m-%d").toordinal()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", d) else 0
    ), reverse=True)

    title = chart_dir.name.replace("_", " ").title()
    subtitle = f"View your {chart_dir.name.replace('_', ' ').title()} chart files here"

    sections = []
    for d in ordered_dates:
        group_files = sorted(groups[d], key=lambda f: f.name.lower())
        try:
            label = datetime.strptime(d, "%Y-%m-%d").strftime("%A, %B %d, %Y")
        except ValueError:
            label = d

        cards = "\n".join(
            f'<a href="/{chart_dir.name}/{f.name}" class="file-card">{f.name}</a>'
            for f in group_files
        )

        sections.append(f"""<section class="date-group">
<h2 class="date-header">{label}</h2>
<div class="file-grid">
{cards}
</div>
</section>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="/styles.css">
</head>
<body>
<div class="container">
<header class="site-header">
<h1>{title}</h1>
<p class="subtitle">{subtitle}</p>
</header>
<main class="content">
{"".join(sections)}
</main>
<footer class="site-footer">
<a href="/">← Home</a>
</footer>
</div>
</body>
</html>"""

    (chart_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Generated index for {chart_dir.name} ({len(files)} files, {len(ordered_dates)} dates)")