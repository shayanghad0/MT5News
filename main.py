import json
import os
from datetime import datetime
from html import escape

# --------------------------------------------------------------------
# 1. OPTIONAL: Free live fetch (no API key). Comment out if not needed.
#    pip install biquote
# --------------------------------------------------------------------
def fetch_free_news():
    try:
        from biquote import Biquote
        bq = Biquote()
        # High-impact events for the week
        events = bq.calendar(importance="high")
        # Convert biquote events into the MQL5-style dict format
        converted = []
        for e in events:
            converted.append({
                'id':            f"bq:{getattr(e, 'id', '')}",
                'eventId':       getattr(e, 'event_id', ''),
                'time':          str(getattr(e, 'date', '')),
                'period':        None,
                'countryCode':   getattr(e, 'country', ''),
                'currency':      getattr(e, 'currency', ''),
                'name':          getattr(e, 'name', ''),
                'importance':    getattr(e, 'importance', 'medium'),
                'type':          'event',
                'sector':        getattr(e, 'category', ''),
                'unit':          'none',
                'multiplier':    'none',
                'digits':        2,
                'actual':        getattr(e, 'actual', None),
                'forecast':      getattr(e, 'forecast', None),
                'previous':      getattr(e, 'previous', None),
                'revisedPrevious': None,
                'revision':      0,
                'timeMode':      'exact',
                'sourceUrl':     '',
                'source':        'biquote',
            })
        return converted
    except Exception as ex:
        print(f"[!] biquote fetch failed ({ex}). Falling back to local data.")
        return None


# --------------------------------------------------------------------
# 2. Load data — from live fetch, a JSON file, or an inline list.
#    Replace `LOCAL_NEWS` with your exported list if you don't want
#    to use biquote at all.
# --------------------------------------------------------------------
LOCAL_NEWS = [
    # 👇 Paste your exported MQL5 events here (as dicts) — the format you showed
]

def load_news():
    # Try live fetch first
    data = fetch_free_news()
    if data:
        print(f"[✓] Fetched {len(data)} events from biquote.")
        return data

    # Fall back to local JSON file
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[✓] Loaded {len(data)} events from news.json.")
        return data

    # Fall back to inline list
    if LOCAL_NEWS:
        print(f"[✓] Using {len(LOCAL_NEWS)} inline events.")
        return LOCAL_NEWS

    print("[!] No data source available.")
    return []


# --------------------------------------------------------------------
# 3. HTML generation
# --------------------------------------------------------------------
IMPORTANCE_COLORS = {
    "high":   ("#e53935", "#ffebee"),
    "medium": ("#fb8c00", "#fff3e0"),
    "low":    ("#43a047", "#e8f5e9"),
}

def fmt_value(v, digits=2):
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):.{digits}f}"
    except (ValueError, TypeError):
        return escape(str(v))

def build_row(ev):
    imp = (ev.get("importance") or "low").lower()
    color, bg = IMPORTANCE_COLORS.get(imp, ("#757575", "#f5f5f5"))

    t = ev.get("time") or ""
    if t:
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            t = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass

    digits = ev.get("digits") or 2
    actual   = fmt_value(ev.get("actual"),   digits)
    forecast = fmt_value(ev.get("forecast"), digits)
    previous = fmt_value(ev.get("previous"), digits)

    # Highlight actual vs forecast
    actual_cls = ""
    try:
        a, f = float(ev.get("actual")), float(ev.get("forecast"))
        actual_cls = "beat" if a > f else ("miss" if a < f else "inline")
    except (TypeError, ValueError):
        pass

    return f"""
    <tr data-importance="{imp}" data-currency="{escape(ev.get('currency',''))}">
      <td>{escape(t)}</td>
      <td><span class="ccy">{escape(ev.get('currency',''))}</span></td>
      <td><span class="badge" style="background:{bg};color:{color};border:1px solid {color}">{imp.upper()}</span></td>
      <td class="name">{escape(ev.get('name',''))}</td>
      <td class="num {actual_cls}">{actual}</td>
      <td class="num">{forecast}</td>
      <td class="num">{previous}</td>
      <td>{escape(ev.get('sector') or '—')}</td>
      <td>{escape(ev.get('source') or '—')}</td>
    </tr>"""


def generate_html(news, output="news_report.html"):
    rows = "\n".join(build_row(e) for e in news)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total = len(news)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MQL5 Economic News Report</title>
<style>
  :root {{
    --bg: #0f172a; --panel: #1e293b; --text: #e2e8f0;
    --muted: #94a3b8; --accent: #38bdf8; --border: #334155;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); padding: 24px;
  }}
  header {{
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
  }}
  h1 {{ font-size: 22px; margin: 0; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .controls {{
    display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px;
  }}
  input, select {{
    background: var(--panel); border: 1px solid var(--border);
    color: var(--text); padding: 8px 10px; border-radius: 6px; font-size: 13px;
  }}
  input:focus, select:focus {{ outline: none; border-color: var(--accent); }}
  table {{
    width: 100%; border-collapse: collapse; background: var(--panel);
    border-radius: 10px; overflow: hidden; font-size: 13px;
  }}
  thead {{
    background: #0b1220; position: sticky; top: 0;
  }}
  th, td {{
    padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border);
  }}
  th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
  tr:hover td {{ background: rgba(56,189,248,.05); }}
  .name {{ font-weight: 500; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .num.beat {{ color: #4ade80; font-weight: 600; }}
  .num.miss {{ color: #f87171; font-weight: 600; }}
  .ccy {{
    display: inline-block; background: #0b1220; border: 1px solid var(--border);
    padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;
  }}
  .badge {{
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 700; letter-spacing: .04em;
  }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 16px; text-align: center; }}
  @media (max-width: 720px) {{
    table, thead, tbody, th, td, tr {{ display: block; }}
    thead {{ display: none; }}
    tr {{ margin-bottom: 10px; border: 1px solid var(--border); border-radius: 8px; padding: 8px; }}
    td {{ border: none; padding: 4px 6px; }}
    td::before {{ content: attr(data-label); color: var(--muted); font-size: 11px; display: block; }}
  }}
</style>
</head>
<body>
  <header>
    <h1>📊 MQL5 Economic News Report</h1>
    <div class="meta">Generated: {generated_at} &nbsp;•&nbsp; {total} events</div>
  </header>

  <div class="controls">
    <input id="search" placeholder="🔍 Search event name…" oninput="filterRows()">
    <select id="impFilter" onchange="filterRows()">
      <option value="">All importance</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
    </select>
    <select id="ccyFilter" onchange="filterRows()">
      <option value="">All currencies</option>
      {''.join(f'<option value="{c}">{c}</option>' for c in sorted({e.get("currency","") for e in news if e.get("currency")}))}
    </select>
  </div>

  <table id="newsTable">
    <thead>
      <tr>
        <th>Time (UTC)</th><th>CCY</th><th>Impact</th><th>Event</th>
        <th style="text-align:right">Actual</th>
        <th style="text-align:right">Forecast</th>
        <th style="text-align:right">Previous</th>
        <th>Sector</th><th>Source</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <footer>Generated locally • No API credits used</footer>

<script>
function filterRows() {{
  const q   = document.getElementById('search').value.toLowerCase();
  const imp = document.getElementById('impFilter').value;
  const ccy = document.getElementById('ccyFilter').value;
  document.querySelectorAll('#newsTable tbody tr').forEach(tr => {{
    const name = tr.querySelector('.name').textContent.toLowerCase();
    const trImp = tr.dataset.importance;
    const trCcy = tr.dataset.currency;
    const ok = (!q || name.includes(q)) &&
               (!imp || trImp === imp) &&
               (!ccy || trCcy === ccy);
    tr.style.display = ok ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[✓] HTML report written → {os.path.abspath(output)}")


# --------------------------------------------------------------------
# 4. Main
# --------------------------------------------------------------------
if __name__ == "__main__":
    news = load_news()
    if not news:
        print("[!] Nothing to export. Paste your MQL5 events into LOCAL_NEWS or save as news.json.")
    else:
        generate_html(news, output="news_report.html")