#!/bin/sh
set -e

# Render markdown files into HTML
python3 /app/render_md.py

# Generate simple index links for weekly and daily charts
python3 /app/generate_chart_index.py

# Simple top-level page with selector cards
cat > /usr/share/nginx/html/index.html <<'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Charts Browser</title>
<link rel="stylesheet" href="/styles.css">
</head>
<body>
<div class="container">
<header class="site-header" style="text-align:center; margin-top:3rem;">
<h1>📊 Charts Browser</h1>
<p class="subtitle">Browse weekly, daily, and analysis charts</p>
</header>
<main class="content" style="display:flex; flex-wrap:wrap; gap:1rem; justify-content:center; margin-top:2rem;">
<a class="file-card" href="/md/" style="max-width:280px;">
<h2>📝 Markdown Notes</h2>
<p>Rendered documentation & analysis</p>
</a>
<a class="file-card" href="/weekly_charts/" style="max-width:280px;">
<h2>📈 Weekly Charts</h2>
<p>Weekly technical analysis charts</p>
</a>
<a class="file-card" href="/daily_charts/" style="max-width:280px;">
<h2>📉 Daily Charts</h2>
<p>Daily technical analysis charts</p>
</a>
<a class="file-card" href="/stop-loss/" style="max-width:280px;">
<h2>🛑 Stop Loss Estimator</h2>
<p>Estimate a stop from weekly swing highs and ATR</p>
</a>
<a class="file-card" href="/daily-stop-loss/" style="max-width:280px;">
<h2>📉 Daily Stop Loss Estimator</h2>
<p>Estimate a stop 1% below the recent daily swing low</p>
</a>
</main>
<div style="text-align:center;margin-top:2rem;">
<button id="regen-btn" type="button" style="display:inline-block;background:var(--accent);color:#fff;border:0;border-radius:var(--radius);padding:0.75rem 2rem;font-size:1rem;font-weight:600;cursor:pointer;text-decoration:none;">
  🔄 Regenerate Charts
</button>
<div id="regen-status" class="subtitle" style="margin-top:0.75rem;"></div>
</div>
<script>
document.getElementById('regen-btn').addEventListener('click', async function () {
  var btn = document.getElementById('regen-btn');
  var status = document.getElementById('regen-status');
  btn.disabled = true;
  status.textContent = 'Regenerating…';
  try {
    var res = await fetch('/regenerate', {method: 'POST'});
    var data = await res.json();
    status.textContent = data.ok ? '✅ Regenerated OK' : '❌ Failed: ' + (data.error || '');
  } catch (e) {
    status.textContent = '❌ Error: ' + e;
  } finally {
    btn.disabled = false;
  }
});
</script>
<footer class="site-footer">
<a href="/">← Refresh</a>
</footer>
</div>
</body>
</html>
HTMLEOF

# Background watcher: re-render markdown and regenerate chart indexes whenever files change
(
    while true; do
        sleep 30
        python3 /app/render_md.py
        python3 /app/generate_chart_index.py
    done
) &

# Local regeneration endpoint server (proxied by nginx at /regenerate)
python3 /app/regenerate_server.py > /tmp/regenerate_server.log 2>&1 &

# Hand off to nginx
exec "$@"