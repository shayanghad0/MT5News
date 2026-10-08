import json
import os
from datetime import datetime
from html import escape

# --------------------------------------------------------------------
# 1. Free live fetch via biquote — fetches ALL events now
#    pip install biquote
# --------------------------------------------------------------------
def _get(obj, *names, default=None):
    """Try multiple attribute/key names on an object or dict."""
    for n in names:
        if isinstance(obj, dict) and n in obj and obj[n] not in (None, ""):
            return obj[n]
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v not in (None, ""):
                return v
    return default

def fetch_free_news():
    try:
        from biquote import Biquote
        bq = Biquote()

        # ✅ Fetch ALL news — no importance filter
        events = bq.calendar()

        # If your biquote version requires a date range, uncomment below:
        # from datetime import date, timedelta
        # today = date.today()
        # events = bq.calendar(from_date=today, to_date=today + timedelta(days=7))

        print(f"[i] biquote returned {len(events)} raw events (ALL importance).")
        if events:
            sample = events[0]
            fields = sample.keys() if isinstance(sample, dict) else vars(sample)
            print(f"[i] Sample fields: {list(fields)}")
            print(f"[i] Sample object: {sample}")

        converted = []
        for e in events:
            converted.append({
                'id':             str(_get(e, 'id', 'event_id', 'eventId', default='')),
                'eventId':        str(_get(e, 'event_id', 'eventId', 'id', default='')),
                'time':           str(_get(e, 'date', 'datetime', 'time', 'timestamp', default='')),
                'period':         _get(e, 'period'),
                'countryCode':    _get(e, 'country', 'country_code', 'countryCode', default=''),
                'currency':       _get(e, 'currency', 'currency_code', 'ccy', default=''),
                'name':           _get(e, 'name', 'title', 'event', 'event_name', default=''),
                'importance':     str(_get(e, 'importance', 'impact', 'priority', default='low')).lower(),
                'type':           _get(e, 'type', default='event'),
                'sector':         _get(e, 'sector', 'category', default=''),
                'unit':           _get(e, 'unit', default='none'),
                'multiplier':     _get(e, 'multiplier', default='none'),
                'digits':         _get(e, 'digits', default=2) or 2,
                'actual':         _get(e, 'actual'),
                'forecast':       _get(e, 'forecast'),
                'previous':       _get(e, 'previous'),
                'revisedPrevious': _get(e, 'revisedPrevious'),
                'revision':       _get(e, 'revision', default=0),
                'timeMode':       _get(e, 'timeMode', default='exact'),
                'sourceUrl':      _get(e, 'sourceUrl', 'url', default=''),
                'source':         'biquote',
            })
        return converted
    except Exception as ex:
        print(f"[!] biquote fetch failed: {ex}")
        return None


# --------------------------------------------------------------------
# 2. Data loading: news.json → biquote → inline list
# --------------------------------------------------------------------
LOCAL_NEWS = []

def load_news():
    # Priority 1: your exported MQL5 data
    if os.path.exists("news.json"):
        try:
            with open("news.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                print(f"[✓] Loaded {len(data)} events from news.json.")
                return data
        except Exception as ex:
            print(f"[!] news.json parse error: {ex}")

    # Priority 2: free live fetch (ALL news)
    data = fetch_free_news()
    if data:
        print(f"[✓] Using {len(data)} events from biquote (ALL importance).")
        return data

    # Priority 3: inline list
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
    "holiday":("#7e57c2", "#ede7f6"),
    "speech": ("#0288d1", "#e1f5fe"),
}

def fmt_value(v, digits=2):
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):.{int(digits)}f}"
    except (ValueError, TypeError):
        return escape(str(v))

def build_row(ev):
    imp = (ev.get("importance") or "low").lower()
    color, bg = IMPORTANCE_COLORS.get(imp, ("#757575", "#f5f5f5"))

    t = ev.get("time") or ""
    if t:
        try:
            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            t = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass

    digits = ev.get("digits") or 2
    actual   = fmt_value(ev.get("actual"),   digits)
    forecast = fmt_value(ev.get("forecast"), digits)
    previous = fmt_value(ev.get("previous"), digits)

    actual_cls = ""
    try:
        a, f = float(ev.get("actual")), float(ev.get("forecast"))
        actual_cls = "beat" if a > f else ("miss" if a < f else "inline")
    except (TypeError, ValueError):
        pass

    return f"""
    <tr data-importance="{imp}" data-currency="{escape(str(ev.get('currency','')))}">
      <td>{escape(str(t))}</td>
      <td><span class="ccy">{escape(str(ev.get('currency','')))}</span></td>
      <td><span class="badge" style="background:{bg};color:{color};border:1px solid {color}">{imp.upper()}</span></td>
      <td class="name">{escape(str(ev.get('name','')))}</td>
      <td class="num {actual_cls}">{actual}</td>
      <td class="num">{forecast}</td>
      <td class="num">{previous}</td>
      <td>{escape(str(ev.get('sector') or '—'))}</td>
      <td>{escape(str(ev.get('source') or '—'))}</td>
    </tr>"""


def generate_html(news, output="news_report.html"):
    # Sort by time ascending
    def sort_key(e):
        t = e.get("time") or ""
        try:
            return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        except Exception:
            return datetime.max

    news = sorted(news, key=sort_key)
    rows = "\n".join(build_row(e) for e in news)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total = len(news)

    # Stats
    highs = sum(1 for e in news if (e.get("importance") or "").lower() == "high")
    mediums = sum(1 for e in news if (e.get("importance") or "").lower() == "medium")
    lows = sum(1 for e in news if (e.get("importance") or "").lower() == "low")

    currencies = sorted({str(e.get("currency","")) for e in news if e.get("currency")})
    ccy_options = "".join(f'<option value="{c}">{c}</option>' for c in currencies)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MQL5 Economic News Report — ALL Events</title>
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
  .stats {{
    display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px;
  }}
  .stat {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 16px; min-width: 90px;
  }}
  .stat .num {{ font-size: 22px; font-weight: 700; }}
  .stat .lbl {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
  .stat.high .num {{ color: #e53935; }}
  .stat.medium .num {{ color: #fb8c00; }}
  .stat.low .num {{ color: #43a047; }}
  .controls {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
  input, select {{
    background: var(--panel); border: 1px solid var(--border);
    color: var(--text); padding: 8px 10px; border-radius: 6px; font-size: 13px;
  }}
  input:focus, select:focus {{ outline: none; border-color: var(--accent); }}
  table {{
    width: 100%; border-collapse: collapse; background: var(--panel);
    border-radius: 10px; overflow: hidden; font-size: 13px;
  }}
  thead {{ background: #0b1220; position: sticky; top: 0; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
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
    <h1>📊 MQL5 Economic News Report — ALL Events</h1>
    <div class="meta">Generated: {generated_at} &nbsp;•&nbsp; {total} events</div>
  </header>

  <div class="stats">
    <div class="stat high"><div class="num">{highs}</div><div class="lbl">High</div></div>
    <div class="stat medium"><div class="num">{mediums}</div><div class="lbl">Medium</div></div>
    <div class="stat low"><div class="num">{lows}</div><div class="lbl">Low</div></div>
    <div class="stat"><div class="num">{total}</div><div class="lbl">Total</div></div>
  </div>

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
      {ccy_options}
    </select>
    <span id="visibleCount" class="meta" style="align-self:center"></span>
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
  let visible = 0;
  document.querySelectorAll('#newsTable tbody tr').forEach(tr => {{
    const name = tr.querySelector('.name').textContent.toLowerCase();
    const ok = (!q || name.includes(q)) &&
               (!imp || tr.dataset.importance === imp) &&
               (!ccy || tr.dataset.currency === ccy);
    tr.style.display = ok ? '' : 'none';
    if (ok) visible++;
  }});
  document.getElementById('visibleCount').textContent = `Showing ${{visible}} of {total}`;
}}
filterRows();
</script>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[✓] HTML report written → {os.path.abspath(output)}")
    print(f"[i] Breakdown — High: {highs} | Medium: {mediums} | Low: {lows} | Total: {total}")


if __name__ == "__main__":
    news = load_news()
    if not news:
        print("[!] Nothing to export.")
    else:
        generate_html(news, output="news_report.html")