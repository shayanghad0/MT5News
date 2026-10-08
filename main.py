import json
import os
from datetime import datetime, timezone, timedelta
from html import escape

# --------------------------------------------------------------------
# Tehran timezone (Iran Standard Time, UTC+3:30 — no DST since 2022)
# --------------------------------------------------------------------
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30), name="Tehran")


# --------------------------------------------------------------------
# 1. Free live fetch via biquote — fetches ALL events
#    pip install biquote
# --------------------------------------------------------------------
def _get(obj, *names, default=None):
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
        events = bq.calendar()   # ALL news

        print(f"[i] biquote returned {len(events)} raw events (ALL importance).")
        if events:
            sample = events[0]
            fields = sample.keys() if isinstance(sample, dict) else vars(sample)
            print(f"[i] Sample fields: {list(fields)}")

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
                'description':    _get(e, 'description', 'text', 'news_text', 'details', 'summary'),
                'source':         'biquote',
            })
        return converted
    except Exception as ex:
        print(f"[!] biquote fetch failed: {ex}")
        return None


# --------------------------------------------------------------------
# 2. Data loading
# --------------------------------------------------------------------
LOCAL_NEWS = []


def load_news():
    if os.path.exists("news.json"):
        try:
            with open("news.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                print(f"[✓] Loaded {len(data)} events from news.json.")
                return data
        except Exception as ex:
            print(f"[!] news.json parse error: {ex}")

    data = fetch_free_news()
    if data:
        print(f"[✓] Using {len(data)} events from biquote (ALL importance).")
        return data

    if LOCAL_NEWS:
        print(f"[✓] Using {len(LOCAL_NEWS)} inline events.")
        return LOCAL_NEWS

    print("[!] No data source available.")
    return []


# --------------------------------------------------------------------
# 3. Helpers
# --------------------------------------------------------------------
IMPORTANCE_COLORS = {
    "high":    ("#e53935", "#ffebee"),
    "medium":  ("#fb8c00", "#fff3e0"),
    "low":     ("#43a047", "#e8f5e9"),
    "holiday": ("#7e57c2", "#ede7f6"),
    "speech":  ("#0288d1", "#e1f5fe"),
}


def to_tehran(iso_str):
    if not iso_str:
        return ""
    s = str(iso_str).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def to_utc(iso_str):
    if not iso_str:
        return ""
    s = str(iso_str).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def fmt_value(v, digits=2):
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):.{int(digits)}f}"
    except (ValueError, TypeError):
        return escape(str(v))


def build_summary(ev):
    """Full news-style narrative paragraph."""
    name    = ev.get("name") or "Event"
    ccy     = ev.get("currency") or ""
    country = ev.get("countryCode") or ""
    imp     = (ev.get("importance") or "").lower()
    typ     = ev.get("type") or "indicator"
    sector  = ev.get("sector") or ""
    unit    = ev.get("unit") or "none"
    mult    = ev.get("multiplier") or "none"
    digits  = int(ev.get("digits") or 2)

    a  = ev.get("actual")
    f  = ev.get("forecast")
    p  = ev.get("previous")
    rp = ev.get("revisedPrevious")

    def n(x):
        if x is None or x == "":
            return None
        try:
            return f"{float(x):.{digits}f}"
        except (ValueError, TypeError):
            return str(x)

    # Unit description
    unit_txt = ""
    if unit not in ("none", "", None):
        unit_txt = f" measured in {unit}"
        if mult not in ("none", "", None):
            unit_txt += f" ({mult})"

    # Impact phrase
    impact_phrase = {
        "high":   "a high-impact release that frequently triggers sharp moves in related currency pairs",
        "medium": "a medium-impact release that can cause moderate volatility in related markets",
        "low":    "a low-impact release that typically produces limited market reaction",
    }.get(imp, "an economic release")

    parts = []

    # 1. Intro
    sector_txt = f" in the {sector} sector" if sector else ""
    parts.append(
        f"{name} is {impact_phrase}. "
        f"It is a {ccy} {typ}{sector_txt}, published by {country}{unit_txt}."
    )

    # 2. Numbers
    if n(a) is not None and n(f) is not None:
        try:
            a_f = float(a)
            f_f = float(f)
            diff = a_f - f_f
            pct = (abs(diff) / abs(f_f) * 100) if f_f != 0 else 0

            if diff > 0:
                verdict = (
                    f"The actual reading came in at {n(a)}, exceeding the forecast of {n(f)} "
                    f"by {abs(diff):.{digits}f} ({pct:.1f}%). This stronger-than-expected result "
                    f"is generally bullish for {ccy}."
                )
            elif diff < 0:
                verdict = (
                    f"The actual reading came in at {n(a)}, falling short of the forecast of {n(f)} "
                    f"by {abs(diff):.{digits}f} ({pct:.1f}%). This weaker-than-expected result "
                    f"is generally bearish for {ccy}."
                )
            else:
                verdict = (
                    f"The actual reading of {n(a)} matched the forecast exactly. "
                    f"Markets are unlikely to react strongly to this release."
                )
            parts.append(verdict)
        except (TypeError, ValueError):
            parts.append(f"Actual: {n(a)}, Forecast: {n(f)}, Previous: {n(p)}.")
    elif n(a) is not None:
        parts.append(f"The actual reading was released at {n(a)}.")
    elif n(f) is not None:
        parts.append(
            f"The event is scheduled for release. Analysts forecast a reading of {n(f)}. "
            f"Markets will watch closely for the actual figure."
        )
    else:
        parts.append(
            "The event has been scheduled but no forecast or actual values are available yet."
        )

    # 3. Previous context
    if n(p) is not None:
        prev_txt = f"The previous reading was {n(p)}"
        if n(rp) is not None and str(rp) != str(p):
            prev_txt += f", later revised to {n(rp)}"
        prev_txt += "."
        parts.append(prev_txt)

    # 4. Closing / market note
    if imp == "high":
        parts.append(
            "Traders should be prepared for increased volatility around the release time. "
            "Use appropriate risk management and consider spread widening on affected pairs."
        )
    elif imp == "medium":
        parts.append(
            "Traders may want to monitor the release for potential short-term opportunities."
        )

    return " ".join(parts)


# --------------------------------------------------------------------
# 4. HTML row + JSON payload
# --------------------------------------------------------------------
def build_row(ev, idx):
    imp = (ev.get("importance") or "low").lower()
    color, bg = IMPORTANCE_COLORS.get(imp, ("#757575", "#f5f5f5"))

    t = to_tehran(ev.get("time"))
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
    <tr class="row" data-idx="{idx}" data-importance="{imp}" data-currency="{escape(str(ev.get('currency','')))}">
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


def build_payload(news):
    out = []
    for ev in news:
        imp = (ev.get("importance") or "low").lower()
        color, bg = IMPORTANCE_COLORS.get(imp, ("#757575", "#f5f5f5"))
        text = ev.get("description")
        if not text:
            text = build_summary(ev)

        out.append({
            "name":        ev.get("name") or "—",
            "currency":    ev.get("currency") or "—",
            "country":     ev.get("countryCode") or "—",
            "importance":  imp,
            "impColor":    color,
            "impBg":       bg,
            "timeTehran":  to_tehran(ev.get("time")) or "—",
            "timeUtc":     to_utc(ev.get("time")) or "—",
            "period":      ev.get("period") or "—",
            "actual":      fmt_value(ev.get("actual"),   ev.get("digits") or 2),
            "forecast":    fmt_value(ev.get("forecast"), ev.get("digits") or 2),
            "previous":    fmt_value(ev.get("previous"), ev.get("digits") or 2),
            "revisedPrevious": fmt_value(ev.get("revisedPrevious"), ev.get("digits") or 2),
            "revision":    ev.get("revision", 0),
            "type":        ev.get("type") or "—",
            "sector":      ev.get("sector") or "—",
            "unit":        ev.get("unit") or "none",
            "multiplier":  ev.get("multiplier") or "none",
            "digits":      ev.get("digits") or 2,
            "timeMode":    ev.get("timeMode") or "—",
            "eventId":     ev.get("eventId") or "—",
            "id":          ev.get("id") or "—",
            "source":      ev.get("source") or "—",
            "sourceUrl":   ev.get("sourceUrl") or "",
            "text":        text,
        })
    return out


# --------------------------------------------------------------------
# 5. HTML generation
# --------------------------------------------------------------------
def generate_html(news, output="news_report.html"):
    def sort_key(e):
        t = e.get("time") or ""
        try:
            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.max.replace(tzinfo=timezone.utc)

    news = sorted(news, key=sort_key)
    rows = "\n".join(build_row(e, i) for i, e in enumerate(news))
    payload_json = json.dumps(build_payload(news), ensure_ascii=False)

    generated_at = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M Tehran")
    total = len(news)
    highs   = sum(1 for e in news if (e.get("importance") or "").lower() == "high")
    mediums = sum(1 for e in news if (e.get("importance") or "").lower() == "medium")
    lows    = sum(1 for e in news if (e.get("importance") or "").lower() == "low")

    currencies = sorted({str(e.get("currency", "")) for e in news if e.get("currency")})
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
  .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }}
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
  tbody tr {{ cursor: pointer; transition: background .15s; }}
  tbody tr:hover td {{ background: rgba(56,189,248,.08); }}
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

  /* ---------- Modal / Card ---------- */
  .backdrop {{
    position: fixed; inset: 0; background: rgba(2,6,23,.75);
    backdrop-filter: blur(4px);
    display: none; align-items: center; justify-content: center;
    padding: 20px; z-index: 1000;
  }}
  .backdrop.open {{ display: flex; }}
  .card {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 14px; max-width: 720px; width: 100%;
    max-height: 90vh; overflow-y: auto;
    box-shadow: 0 25px 60px rgba(0,0,0,.6);
    animation: pop .18s ease-out;
  }}
  @keyframes pop {{
    from {{ transform: translateY(12px) scale(.98); opacity: 0; }}
    to   {{ transform: translateY(0) scale(1); opacity: 1; }}
  }}
  .card-head {{
    padding: 18px 22px; border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
  }}
  .card-head h2 {{ margin: 0; font-size: 18px; }}
  .card-head .sub {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  .close {{
    background: transparent; border: 1px solid var(--border); color: var(--muted);
    border-radius: 6px; padding: 4px 10px; cursor: pointer; font-size: 14px;
  }}
  .close:hover {{ color: var(--text); border-color: var(--accent); }}
  .card-body {{ padding: 18px 22px 22px; }}

  .grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px; margin-bottom: 16px;
  }}
  .field {{
    background: #0b1220; border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 10px;
  }}
  .field .k {{
    color: var(--muted); font-size: 10px; text-transform: uppercase;
    letter-spacing: .05em; margin-bottom: 3px;
  }}
  .field .v {{ font-size: 14px; font-weight: 600; word-break: break-word; }}
  .field .v.big {{ font-size: 18px; }}
  .field .v.beat {{ color: #4ade80; }}
  .field .v.miss {{ color: #f87171; }}

  .news-text {{
    background: linear-gradient(135deg, #0b1220 0%, #162033 100%);
    border: 1px solid var(--border); border-left: 3px solid var(--accent);
    border-radius: 10px; padding: 14px 16px; margin-top: 6px;
  }}
  .news-text .lbl {{
    color: var(--accent); font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px;
  }}
  .news-text .body {{ line-height: 1.7; font-size: 14px; color: #cbd5e1; }}

  .src-link {{
    display: inline-block; margin-top: 14px; color: var(--accent);
    font-size: 13px; text-decoration: none; border-bottom: 1px dashed var(--accent);
  }}
  .src-link:hover {{ opacity: .8; }}

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
    <div class="meta">Generated: {generated_at} &nbsp;•&nbsp; {total} events &nbsp;•&nbsp; Click any row for details</div>
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
        <th>Time (Tehran)</th><th>CCY</th><th>Impact</th><th>Event</th>
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

  <footer>Generated locally • No API credits used • Times shown in Tehran (UTC+3:30)</footer>

  <!-- 🔔 News detail card -->
  <div class="backdrop" id="backdrop" onclick="if(event.target===this) closeCard()">
    <div class="card" id="card">
      <div class="card-head">
        <div>
          <h2 id="c-name">—</h2>
          <div class="sub" id="c-sub">—</div>
        </div>
        <button class="close" onclick="closeCard()">✕ Close</button>
      </div>
      <div class="card-body">
        <div class="grid" id="c-grid"></div>

        <div class="news-text">
          <div class="lbl">📰 News Text</div>
          <div class="body" id="c-text">—</div>
        </div>

        <a id="c-source" class="src-link" href="#" target="_blank" rel="noopener">🔗 Official source</a>
      </div>
    </div>
  </div>

<script>
const NEWS = {payload_json};

function field(k, v, cls="") {{
  return `<div class="field"><div class="k">${{k}}</div><div class="v ${{cls}}">${{v}}</div></div>`;
}}

function openCard(idx) {{
  const n = NEWS[idx];
  if (!n) return;

  document.getElementById('c-name').textContent = n.name;
  document.getElementById('c-sub').innerHTML =
    `<span class="ccy">${{n.currency}}</span> &nbsp;•&nbsp; ${{n.country}} &nbsp;•&nbsp; ${{n.importance.toUpperCase()}} impact &nbsp;•&nbsp; ${{n.type}}`;

  let aCls = "";
  const a = parseFloat(n.actual), f = parseFloat(n.forecast);
  if (!isNaN(a) && !isNaN(f)) aCls = a > f ? "beat" : (a < f ? "miss" : "");

  const grid = [
    field("Time (Tehran)", n.timeTehran, "big"),
    field("Time (UTC)",    n.timeUtc),
    field("Actual",        n.actual,   aCls),
    field("Forecast",      n.forecast),
    field("Previous",      n.previous),
    field("Revised Prev.", n.revisedPrevious),
    field("Currency",      n.currency),
    field("Country",       n.country),
    field("Importance",    n.importance.toUpperCase()),
    field("Sector",        n.sector),
    field("Type",          n.type),
    field("Unit",          n.unit),
    field("Multiplier",    n.multiplier),
    field("Digits",        n.digits),
    field("Period",        n.period),
    field("Event ID",      n.eventId),
    field("ID",            n.id),
    field("Source",        n.source),
  ].join("");

  document.getElementById('c-grid').innerHTML = grid;
  document.getElementById('c-text').textContent = n.text;

  const link = document.getElementById('c-source');
  if (n.sourceUrl) {{
    link.href = n.sourceUrl;
    link.style.display = 'inline-block';
  }} else {{
    link.style.display = 'none';
  }}

  document.getElementById('backdrop').classList.add('open');
}}

function closeCard() {{
  document.getElementById('backdrop').classList.remove('open');
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeCard(); }});

// Wire up row clicks
document.querySelectorAll('#newsTable tbody tr').forEach(tr => {{
  tr.addEventListener('click', () => openCard(parseInt(tr.dataset.idx, 10)));
}});

// Filtering
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
    print(f"[i] Times shown in Tehran time (UTC+3:30)")


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
if __name__ == "__main__":
    news = load_news()
    if not news:
        print("[!] Nothing to export.")
    else:
        generate_html(news, output="news_report.html")