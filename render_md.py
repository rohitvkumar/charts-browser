#!/usr/bin/env python3
"""Render styled markdown files from /md_src into HTML served at /md/."""
from pathlib import Path

SRC = Path("/md_src")
DST = Path("/usr/share/nginx/html/md")

try:
    import markdown
except ImportError:
    print("markdown package not installed; please install it in the Dockerfile.")
    raise

DST.mkdir(parents=True, exist_ok=True)

for md_file in sorted(SRC.glob("*.md")):
    html_name = md_file.stem + ".html"
    text = md_file.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["extra", "codehilite", "toc"],
        output_format="html5",
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{md_file.name}</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <div class="container">
    <header class="site-header">
      <h1>{md_file.name}</h1>
      <p class="subtitle">{md_file.name}</p>
    </header>
    <main class="content">
      {body}
    </main>
    <footer class="site-footer">
      <a href="/">← Home</a>
    </footer>
  </div>
</body>
</html>"""
    (DST / html_name).write_text(html, encoding="utf-8")
print(f"Rendered {len(list(SRC.glob('*.md')))} markdown files to {DST}")