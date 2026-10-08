import json
import os
from datetime import datetime, timezone, timedelta, date
from html import escape

# --------------------------------------------------------------------
# Tehran timezone (Iran Standard Time, UTC+3:30 — no DST since 2022)
# --------------------------------------------------------------------
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30), name="Tehran")

FALLBACK_SYMBOLS = ["XAUUSD", "XAGUSD"]

KNOWN_CCY = [
    "XAU", "XAG", "XPT", "XPD",
    "USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF",
    "CNH", "CNY", "TRY", "SEK", "NOK", "DKK", "PLN", "HUF",
    "CZK", "MXN", "ZAR", "SGD", "HKD", "RUB", "INR", "BRL",
]

# --------------------------------------------------------------------
# Inverse indicators — higher value is BAD for the currency
# (e.g., more jobless claims = weaker economy = weaker currency)
# --------------------------------------------------------------------
INVERSE_KEYWORDS = [
    "jobless", "unemployment", "claims", "layoff", "layoffs",
    "dismissal", "bankrupt", "bankruptcy", "default",
    "inventories", "stockpiles",     # rising inventories often bearish
]

def is_inverse_indicator(name):
    n = (name or "").lower()
    return any(kw in n for kw in INVERSE_KEYWORDS)


def get_connected_symbols():
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print(f"[!] MT5 initialize() failed: {mt5.last_error()}")
            return FALLBACK_SYMBOLS[:]
        syms = mt5.symbols_get()
        mt5.shutdown()
        if not syms:
            return FALLBACK_SYMBOLS[:]
        names = sorted({s.name for s in syms})
        print(f"[✓] MT5 returned {len(names)} symbols.")
        return names
    except ImportError:
        print("[i] MetaTrader5 package not installed — using fallback symbols.")
        return FALLBACK_SYMBOLS[:]
    except Exception as ex:
        print(f"[!] MT5 symbol fetch error: {ex} — using fallback.")
        return FALLBACK_SYMBOLS[:]


def split_symbol(sym):
    s = sym.upper().replace(".", "").replace("_", "").replace("-", "")
    found = []
    i = 0
    while i < len(s):
        for ccy in KNOWN_CCY:
            if s.startswith(ccy, i):
                found.append(ccy)
                i += len(ccy)
                break
        else:
            i += 1
    return found


def relevant_currencies(symbols):
    out = set()
    for sym in symbols:
        out.update(split_symbol(sym))
    return out


def _get(obj, *names, default=None):
    for n in names:
        if isinstance(obj, dict) and n in obj and obj[n] not in (None, ""):
            return obj[n]
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v not in (None, ""):
                return v
    return default


def fetch_free_news(today_only=True):
    try:
        from biquote import Biquote
        bq = Biquote()

        events = None
        if today_only:
            today = date.today()
            try:
                events = bq.calendar(from_date=today, to_date=today)
                print(f"[i] biquote date-range fetch returned {len(events) if events else 0} events.")
            except TypeError:
                print("[i] biquote does not support date-range — falling back to full calendar.")
                events = None
            except Exception as ex:
                print(f"[i] Date-range fetch failed ({ex}) — falling back to full calendar.")

        if events is None:
            events = bq.calendar()

        print(f"[i] biquote returned {len(events)} raw events.")
        if events:
            sample = events[0]
            fields = sample.keys() if isinstance(sample, dict) else vars(sample)
            print(f"[i] Sample fields: {list(fields)}")

        if today_only:
            today_tehran = datetime.now(TEHRAN_TZ).date()
            filtered = []
            for e in events:
                raw = _get(e, 'date', 'datetime', 'time', 'timestamp', default='')
                if not raw:
                    continue
                try:
                    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt.astimezone(TEHRAN_TZ).date() == today_tehran:
                        filtered.append(e)
                except Exception:
                    filtered.append(e)
            print(f"[i] Filtered to today (Tehran): {len(filtered)} events.")
            events = filtered

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


LOCAL_NEWS = []


def load_news(today_only=True):
    if os.path.exists("news.json"):
        try:
            with open("news.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                print(f"[✓] Loaded {len(data)} events from news.json.")
                if today_only:
                    today_tehran = datetime.now(TEHRAN_TZ).date()
                    filt = []
                    for e in data:
                        t = e.get("time") or ""
                        try:
                            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            if dt.astimezone(TEHRAN_TZ).date() == today_tehran:
                                filt.append(e)
                        except Exception:
                            filt.append(e)
                    print(f"[i] Filtered to today (Tehran): {len(filt)} events.")
                    return filt
                return data
        except Exception as ex:
            print(f"[!] news.json parse error: {ex}")

    data = fetch_free_news(today_only=today_only)
    if data is not None:
        print(f"[✓] Using {len(data)} events from biquote.")
        return data

    if LOCAL_NEWS:
        print(f"[✓] Using {len(LOCAL_NEWS)} inline events.")
        return LOCAL_NEWS

    print("[!] No data source available.")
    return []


IMPORTANCE_COLORS = {
    "high":    ("#e53935", "#ffebee"),
    "medium":  ("#fb8c00", "#fff3e0"),
    "low":     ("#43a047", "#e8f5e9"),
    "holiday": ("#7e57c2", "#ede7f6"),
    "speech":  ("#0288d1", "#e1f5fe"),
}


def parse_iso(iso_str):
    if not iso_str:
        return None
    s = str(iso_str).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def to_tehran(iso_str):
    dt = parse_iso(iso_str)
    if dt is None:
        return str(iso_str or "")
    return dt.astimezone(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")


def to_utc(iso_str):
    dt = parse_iso(iso_str)
    if dt is None:
        return str(iso_str or "")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def to_iso_utc(iso_str):
    dt = parse_iso(iso_str)
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_value(v, digits=2):
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):.{int(digits)}f}"
    except (ValueError, TypeError):
        return escape(str(v))


def matches_symbols(ev, symbols, relevant_ccys):
    ccy = (ev.get("currency") or "").upper()
    if not ccy or ccy not in relevant_ccys:
        return False, []
    matched = [s for s in symbols if ccy in split_symbol(s)]
    return True, matched


# --------------------------------------------------------------------
# 3b. Trade advice engine — inverse-aware, no WAIT/NO TRADE rows
# --------------------------------------------------------------------
def build_trade_advice(ev, matched_syms):
    name  = ev.get("name") or "Event"
    ccy   = (ev.get("currency") or "").upper()
    imp   = (ev.get("importance") or "low").lower()
    a     = ev.get("actual")
    f     = ev.get("forecast")
    p     = ev.get("previous")
    digits = int(ev.get("digits") or 2)

    inverse = is_inverse_indicator(name)

    def num(x):
        if x is None or x == "":
            return None
        try:
            return float(x)
        except (ValueError, TypeError):
            return None

    a_f, f_f, p_f = num(a), num(f), num(p)

    if a_f is None and f_f is not None:
        scenario = "pre"
    elif a_f is not None and f_f is not None:
        if a_f > f_f:      scenario = "beat"
        elif a_f < f_f:    scenario = "miss"
        else:              scenario = "inline"
    elif a_f is not None:
        scenario = "released"
    else:
        scenario = "unknown"

    def direction_for_symbol(sym, base_strength):
        parts = split_symbol(sym)
        if len(parts) < 2:
            return None, None
        base, quote = parts[0], parts[1]
        if base_strength == 0:
            return None, None
        if ccy == base:
            signal = "BUY" if base_strength > 0 else "SELL"
        elif ccy == quote:
            signal = "SELL" if base_strength > 0 else "BUY"
        else:
            return None, None
        cls = "buy" if signal == "BUY" else "sell"
        return signal, cls

    strength = 0
    reason_prefix = ""
    headline = ""
    tag = " [inverse]" if inverse else ""

    if scenario == "pre":
        if f_f is not None and p_f is not None:
            if f_f == p_f:
                strength = 0
                reason_prefix = "Forecast = previous — no clear bias"
                headline = (f"🔮 PREDICTED — Forecast matches Previous "
                            f"({fmt_value(f, digits)}) → no directional edge")
            else:
                # Normal: forecast > prev → +1 | Inverse: forecast > prev → -1
                raw = +1 if f_f > p_f else -1
                strength = raw if not inverse else -raw
                if strength > 0:
                    reason_prefix = f"{ccy} biased STRONGER"
                    headline = (f"🔮 PREDICTED — Forecast {fmt_value(f, digits)} "
                                f"{'<' if f_f < p_f else '>'} Previous {fmt_value(p, digits)} "
                                f"→ {ccy} bias STRONGER{tag}")
                else:
                    reason_prefix = f"{ccy} biased WEAKER"
                    headline = (f"🔮 PREDICTED — Forecast {fmt_value(f, digits)} "
                                f"{'<' if f_f < p_f else '>'} Previous {fmt_value(p, digits)} "
                                f"→ {ccy} bias WEAKER{tag}")
        else:
            strength = 0
            reason_prefix = "No forecast data — no clear bias"
            headline = "🔮 PREDICTED — no forecast available"
    elif scenario == "beat":
        raw = +1
        strength = raw if not inverse else -raw
        if strength > 0:
            reason_prefix = "Beat forecast — base strengthens"
            headline = (f"📈 BEAT — Actual {fmt_value(a, digits)} > "
                        f"Forecast {fmt_value(f, digits)} → {ccy} STRONGER{tag}")
        else:
            reason_prefix = "Beat forecast — base weakens (inverse)"
            headline = (f"📈 BEAT (inverse) — Actual {fmt_value(a, digits)} > "
                        f"Forecast {fmt_value(f, digits)} → {ccy} WEAKER{tag}")
    elif scenario == "miss":
        raw = -1
        strength = raw if not inverse else -raw
        if strength < 0:
            reason_prefix = "Missed forecast — base weakens"
            headline = (f"📉 MISS — Actual {fmt_value(a, digits)} < "
                        f"Forecast {fmt_value(f, digits)} → {ccy} WEAKER{tag}")
        else:
            reason_prefix = "Missed forecast — base strengthens (inverse)"
            headline = (f"📉 MISS (inverse) — Actual {fmt_value(a, digits)} < "
                        f"Forecast {fmt_value(f, digits)} → {ccy} STRONGER{tag}")
    elif scenario == "inline":
        strength = 0
        reason_prefix = "In-line with forecast — no directional edge"
        headline = f"➖ IN-LINE — Actual = Forecast ({fmt_value(a, digits)})"
    else:
        strength = 0
        reason_prefix = "No forecast to compare"
        headline = "ℹ️ Released — no forecast to compare"

    conf_map = {"high": "High", "medium": "Medium", "low": "Low"}
    confidence = conf_map.get(imp, "Low")

    rows = []
    for sym in matched_syms:
        sig, cls = direction_for_symbol(sym, strength)
        if sig is None:
            continue
        rows.append({
            "symbol": sym,
            "signal": sig,
            "cls": cls,
            "reason": reason_prefix,
        })

    if imp == "high":
        note = "⚠️ HIGH-impact event — volatility likely. Use tight stops, max 1% risk per trade."
    elif imp == "medium":
        note = "⚠️ MEDIUM-impact event — moderate volatility. Consider reduced position size."
    else:
        note = "ℹ️ LOW-impact event — moves may be small (5–20 pips). Edge is thin."

    return {
        "scenario":  scenario,
        "headline":  headline,
        "rows":      rows,
        "confidence": confidence,
        "hint":      "",
        "note":      note,
        "impact":    imp,
        "inverse":   inverse,
    }


def render_trade_advice_html(advice):
    if not advice:
        return ""
    if not advice.get("rows"):
        return ""

    html_parts = []
    html_parts.append(f'<div class="advice-headline">{advice["headline"]}</div>')

    if advice.get("hint"):
        html_parts.append(f'<div class="advice-hint">{advice["hint"]}</div>')

    rows_html = ""
    for r in advice["rows"]:
        sig = r["signal"]
        if sig == "BUY":
            badge = '<span class="sig sig-buy">🟢 BUY</span>'
        else:
            badge = '<span class="sig sig-sell">🔴 SELL</span>'
        rows_html += (
            f'<tr><td class="adv-sym">{escape(r["symbol"])}</td>'
            f'<td class="adv-sig">{badge}</td>'
            f'<td class="adv-reason">{escape(r["reason"])}</td></tr>'
        )
    html_parts.append(
        '<table class="advice-table"><thead><tr>'
        '<th>Symbol</th><th>Signal</th><th>Reason</th>'
        '</tr></thead><tbody>' + rows_html + '</tbody></table>'
    )

    html_parts.append(
        f'<div class="advice-confidence">Confidence: <b>{advice["confidence"]}</b></div>'
    )
    html_parts.append(f'<div class="advice-note">{advice["note"]}</div>')
    html_parts.append(
        '<div class="advice-disclaimer">⚠️ Educational analysis only. '
        'Not financial advice. Always use proper risk management (max 1–2% per trade).</div>'
    )
    return "".join(html_parts)


def build_summary(ev, symbols=None, relevant_ccys=None):
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

    unit_txt = ""
    if unit not in ("none", "", None):
        unit_txt = f" measured in {unit}"
        if mult not in ("none", "", None):
            unit_txt += f" ({mult})"

    impact_phrase = {
        "high":   "a high-impact release that frequently triggers sharp moves in related currency pairs",
        "medium": "a medium-impact release that can cause moderate volatility in related markets",
        "low":    "a low-impact release that typically produces limited market reaction",
    }.get(imp, "an economic release")

    parts = []
    sector_txt = f" in the {sector} sector" if sector else ""
    parts.append(
        f"{name} is {impact_phrase}. "
        f"It is a {ccy} {typ}{sector_txt}, published by {country}{unit_txt}."
    )

    if n(a) is not None and n(f) is not None:
        try:
            a_f = float(a); f_f = float(f); diff = a_f - f_f
            pct = (abs(diff) / abs(f_f) * 100) if f_f != 0 else 0
            if diff > 0:
                verdict = (f"The actual reading came in at {n(a)}, exceeding the forecast of {n(f)} "
                           f"by {abs(diff):.{digits}f} ({pct:.1f}%). This stronger-than-expected result "
                           f"is generally bullish for {ccy}.")
            elif diff < 0:
                verdict = (f"The actual reading came in at {n(a)}, falling short of the forecast of {n(f)} "
                           f"by {abs(diff):.{digits}f} ({pct:.1f}%). This weaker-than-expected result "
                           f"is generally bearish for {ccy}.")
            else:
                verdict = (f"The actual reading of {n(a)} matched the forecast exactly. "
                           f"Markets are unlikely to react strongly to this release.")
            parts.append(verdict)
        except (TypeError, ValueError):
            parts.append(f"Actual: {n(a)}, Forecast: {n(f)}, Previous: {n(p)}.")
    elif n(a) is not None:
        parts.append(f"The actual reading was released at {n(a)}.")
    elif n(f) is not None:
        parts.append(f"The event is scheduled for release. Analysts forecast a reading of {n(f)}. "
                     f"Markets will watch closely for the actual figure.")
    else:
        parts.append("The event has been scheduled but no forecast or actual values are available yet.")

    if n(p) is not None:
        prev_txt = f"The previous reading was {n(p)}"
        if n(rp) is not None and str(rp) != str(p):
            prev_txt += f", later revised to {n(rp)}"
        prev_txt += "."
        parts.append(prev_txt)

    if symbols and relevant_ccys:
        is_rel, matched = matches_symbols(ev, symbols, relevant_ccys)
        if is_rel:
            parts.append(f"⚠️ This event directly affects your connected symbols: {', '.join(matched)}.")
        else:
            parts.append(f"ℹ️ This event does not directly affect your connected symbols ({', '.join(symbols)}).")

    if imp == "high":
        parts.append("Traders should be prepared for increased volatility around the release time. "
                     "Use appropriate risk management and consider spread widening on affected pairs.")
    elif imp == "medium":
        parts.append("Traders may want to monitor the release for potential short-term opportunities.")

    return " ".join(parts)


def build_row(ev, idx, symbols, relevant_ccys):
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

    is_rel, matched = matches_symbols(ev, symbols, relevant_ccys)
    rel_mark = "✅" if is_rel else "❎"
    rel_cls  = "yes" if is_rel else "no"
    rel_title = f"Affects: {', '.join(matched)}" if is_rel else "Not relevant to your symbols"

    neon_cls = ""
    if is_rel:
        if "XAUUSD" in matched:
            neon_cls = "neon gold"
        elif "XAGUSD" in matched:
            neon_cls = "neon"

    return f"""
    <tr class="row {neon_cls}" data-idx="{idx}" data-importance="{imp}" data-currency="{escape(str(ev.get('currency','')))}" data-relevant="{1 if is_rel else 0}">
      <td class="xcol"><span class="xmark {rel_cls}" title="{escape(rel_title)}">{rel_mark}</span></td>
      <td>{escape(str(t))}</td>
      <td class="rel-time" data-iso="{escape(to_iso_utc(ev.get('time')))}">—</td>
      <td><span class="ccy">{escape(str(ev.get('currency','')))}</span></td>
      <td><span class="badge" style="background:{bg};color:{color};border:1px solid {color}">{imp.upper()}</span></td>
      <td class="name">{escape(str(ev.get('name','')))}</td>
      <td class="num {actual_cls}">{actual}</td>
      <td class="num">{forecast}</td>
      <td class="num">{previous}</td>
      <td>{escape(str(ev.get('sector') or '—'))}</td>
      <td>{escape(str(ev.get('source') or '—'))}</td>
    </tr>"""


def build_payload(news, symbols, relevant_ccys):
    out = []
    for ev in news:
        imp = (ev.get("importance") or "low").lower()
        color, bg = IMPORTANCE_COLORS.get(imp, ("#757575", "#f5f5f5"))
        text = ev.get("description")
        if not text:
            text = build_summary(ev, symbols, relevant_ccys)

        is_rel, matched = matches_symbols(ev, symbols, relevant_ccys)

        advice_html = ""
        if is_rel and matched:
            advice = build_trade_advice(ev, matched)
            advice_html = render_trade_advice_html(advice)

        out.append({
            "name":        ev.get("name") or "—",
            "currency":    ev.get("currency") or "—",
            "country":     ev.get("countryCode") or "—",
            "importance":  imp,
            "impColor":    color,
            "impBg":       bg,
            "timeTehran":  to_tehran(ev.get("time")) or "—",
            "timeUtc":     to_utc(ev.get("time")) or "—",
            "timeIso":     to_iso_utc(ev.get("time")),
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
            "relevant":    is_rel,
            "matchedSyms": matched,
            "adviceHtml":  advice_html,
        })
    return out


def generate_html(news, output="news_report.html"):
    symbols = get_connected_symbols()
    relevant_ccys = relevant_currencies(symbols)
    print(f"[i] Connected symbols: {', '.join(symbols)}")
    print(f"[i] Relevant currencies: {', '.join(sorted(relevant_ccys))}")

    def sort_key(e):
        dt = parse_iso(e.get("time"))
        return dt if dt else datetime.max.replace(tzinfo=timezone.utc)

    news = sorted(news, key=sort_key)
    rows = "\n".join(build_row(e, i, symbols, relevant_ccys) for i, e in enumerate(news))
    payload_json = json.dumps(build_payload(news, symbols, relevant_ccys), ensure_ascii=False)

    now_tehran = datetime.now(TEHRAN_TZ)
    generated_at = now_tehran.strftime("%Y-%m-%d %H:%M Tehran")
    today_str = now_tehran.strftime("%A, %d %B %Y")
    total = len(news)
    highs   = sum(1 for e in news if (e.get("importance") or "").lower() == "high")
    mediums = sum(1 for e in news if (e.get("importance") or "").lower() == "medium")
    lows    = sum(1 for e in news if (e.get("importance") or "").lower() == "low")
    relevant_count = sum(1 for e in news if matches_symbols(e, symbols, relevant_ccys)[0])

    currencies = sorted({str(e.get("currency", "")) for e in news if e.get("currency")})
    ccy_options = "".join(f'<option value="{c}">{c}</option>' for c in currencies)

    symbols_str = ", ".join(symbols)
    rel_ccy_str = ", ".join(sorted(relevant_ccys))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MQL5 Economic News — {today_str}</title>
<style>
  :root {{
    --bg: #0f172a; --panel: #1e293b; --text: #e2e8f0;
    --muted: #94a3b8; --accent: #38bdf8; --border: #334155;
    --buy: #4ade80; --sell: #f87171; --wait: #fbbf24;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); padding: 24px; }}
  header {{ display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }}
  h1 {{ font-size: 22px; margin: 0; }}
  .meta {{ color: var(--muted); font-size: 13px; }}

  .next-banner {{
    background: linear-gradient(135deg, #0b1220 0%, #162033 100%);
    border: 1px solid var(--border); border-left: 4px solid var(--accent);
    border-radius: 10px; padding: 14px 18px; margin-bottom: 14px;
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 14px;
  }}
  .next-banner.empty {{ border-left-color: #64748b; opacity: .8; }}
  .next-banner .left {{ display: flex; flex-direction: column; gap: 4px; }}
  .next-banner .lbl {{ color: var(--accent); font-size: 11px; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase; }}
  .next-banner.empty .lbl {{ color: var(--muted); }}
  .next-banner .name {{ font-size: 16px; font-weight: 600; }}
  .next-banner .sub {{ color: var(--muted); font-size: 12px; }}
  .countdown {{ font-family: "SF Mono", Consolas, monospace; font-size: 26px;
    font-weight: 700; color: var(--accent); letter-spacing: .05em; white-space: nowrap; }}
  .countdown.soon {{ color: var(--wait); animation: blink 1s ease-in-out infinite; }}
  .countdown.live {{ color: var(--buy); }}
  .countdown.past {{ color: var(--muted); }}
  @keyframes blink {{ 50% {{ opacity: .5; }} }}

  .symbols-bar {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;
    font-size: 13px; display: flex; flex-wrap: wrap; gap: 10px 20px; align-items: center;
  }}
  .symbols-bar .lbl {{ color: var(--muted); }}
  .symbols-bar code {{
    background: #0b1220; border: 1px solid var(--border);
    padding: 2px 8px; border-radius: 4px; font-size: 12px; color: var(--accent);
  }}
  .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }}
  .stat {{ background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 16px; min-width: 90px; }}
  .stat .num {{ font-size: 22px; font-weight: 700; }}
  .stat .lbl {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
  .stat.high .num {{ color: #e53935; }}
  .stat.medium .num {{ color: #fb8c00; }}
  .stat.low .num {{ color: #43a047; }}
  .stat.rel .num {{ color: var(--accent); }}
  .controls {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; align-items: center; }}
  input, select {{ background: var(--panel); border: 1px solid var(--border);
    color: var(--text); padding: 8px 10px; border-radius: 6px; font-size: 13px; }}
  input:focus, select:focus {{ outline: none; border-color: var(--accent); }}
  .chk-label {{ display: inline-flex; align-items: center; gap: 6px;
    background: var(--panel); border: 1px solid var(--border);
    padding: 7px 12px; border-radius: 6px; font-size: 13px; cursor: pointer; }}
  .chk-label input {{ margin: 0; cursor: pointer; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--panel);
    border-radius: 10px; overflow: hidden; font-size: 13px; }}
  thead {{ background: #0b1220; position: sticky; top: 0; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
  tbody tr {{ cursor: pointer; transition: background .15s; }}
  tbody tr:hover td {{ background: rgba(56,189,248,.08); }}
  .name {{ font-weight: 500; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .num.beat {{ color: var(--buy); font-weight: 600; }}
  .num.miss {{ color: var(--sell); font-weight: 600; }}
  .rel-time {{ font-family: "SF Mono", Consolas, monospace; font-size: 12px; color: var(--muted); white-space: nowrap; }}
  .rel-time.soon {{ color: var(--wait); font-weight: 600; }}
  .rel-time.live {{ color: var(--buy); font-weight: 600; }}
  .ccy {{ display: inline-block; background: #0b1220; border: 1px solid var(--border);
    padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 700; letter-spacing: .04em; }}
  .xcol {{ text-align: center; width: 40px; }}
  .xmark {{ font-size: 16px; display: inline-block; line-height: 1; }}
  .xmark.yes {{ filter: drop-shadow(0 0 4px rgba(74,222,128,.5)); }}
  .xmark.no  {{ opacity: .55; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 16px; text-align: center; }}

  tbody tr.is-next td {{ background: rgba(56,189,248,.10); }}
  tbody tr.is-next td:last-child::after {{
    content: "⏱ NEXT"; display: inline-block; margin-left: 8px;
    font-size: 10px; font-weight: 700; letter-spacing: .06em;
    color: #0b1220; background: var(--accent);
    padding: 2px 6px; border-radius: 4px;
  }}

  tbody tr.neon td {{ background: rgba(56, 189, 248, 0.06);
    border-bottom-color: rgba(56, 189, 248, 0.25); }}
  tbody tr.neon td:first-child {{
    box-shadow: inset 3px 0 0 0 #38bdf8, inset 6px 0 18px -8px rgba(56,189,248,.9);
    animation: neonPulse 2.2s ease-in-out infinite; }}
  tbody tr.neon:hover td {{ background: rgba(56, 189, 248, 0.12); }}
  @keyframes neonPulse {{
    0%, 100% {{ box-shadow: inset 3px 0 0 0 #38bdf8, inset 6px 0 18px -8px rgba(56,189,248,.9); }}
    50%      {{ box-shadow: inset 3px 0 0 0 #7dd3fc, inset 6px 0 26px -6px rgba(125,211,252,1); }}
  }}
  tbody tr.neon.gold td {{ background: rgba(251, 191, 36, 0.07);
    border-bottom-color: rgba(251, 191, 36, 0.25); }}
  tbody tr.neon.gold td:first-child {{
    box-shadow: inset 3px 0 0 0 #fbbf24, inset 6px 0 18px -8px rgba(251,191,36,.9);
    animation: neonPulseGold 2.2s ease-in-out infinite; }}
  tbody tr.neon.gold:hover td {{ background: rgba(251, 191, 36, 0.13); }}
  @keyframes neonPulseGold {{
    0%, 100% {{ box-shadow: inset 3px 0 0 0 #fbbf24, inset 6px 0 18px -8px rgba(251,191,36,.9); }}
    50%      {{ box-shadow: inset 3px 0 0 0 #fde68a, inset 6px 0 26px -6px rgba(253,230,138,1); }}
  }}

  .backdrop {{ position: fixed; inset: 0; background: rgba(2,6,23,.75);
    backdrop-filter: blur(4px); display: none; align-items: center;
    justify-content: center; padding: 20px; z-index: 1000; }}
  .backdrop.open {{ display: flex; }}
  .card {{ background: var(--panel); border: 1px solid var(--border);
    border-radius: 14px; max-width: 760px; width: 100%; max-height: 90vh;
    overflow-y: auto; box-shadow: 0 25px 60px rgba(0,0,0,.6);
    animation: pop .18s ease-out; }}
  @keyframes pop {{
    from {{ transform: translateY(12px) scale(.98); opacity: 0; }}
    to   {{ transform: translateY(0) scale(1); opacity: 1; }}
  }}
  .card-head {{ padding: 18px 22px; border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
  .card-head h2 {{ margin: 0; font-size: 18px; }}
  .card-head .sub {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  .close {{ background: transparent; border: 1px solid var(--border); color: var(--muted);
    border-radius: 6px; padding: 4px 10px; cursor: pointer; font-size: 14px; }}
  .close:hover {{ color: var(--text); border-color: var(--accent); }}
  .card-body {{ padding: 18px 22px 22px; }}

  .rel-banner {{ padding: 10px 14px; border-radius: 8px; margin-bottom: 14px;
    font-size: 13px; font-weight: 600; }}
  .rel-banner.yes {{ background: rgba(74,222,128,.1); border: 1px solid rgba(74,222,128,.4); color: #86efac; }}
  .rel-banner.no  {{ background: rgba(148,163,184,.1); border: 1px solid rgba(148,163,184,.3); color: var(--muted); }}

  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px; margin-bottom: 16px; }}
  .field {{ background: #0b1220; border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 10px; }}
  .field .k {{ color: var(--muted); font-size: 10px; text-transform: uppercase;
    letter-spacing: .05em; margin-bottom: 3px; }}
  .field .v {{ font-size: 14px; font-weight: 600; word-break: break-word; }}
  .field .v.big {{ font-size: 18px; }}
  .field .v.beat {{ color: var(--buy); }}
  .field .v.miss {{ color: var(--sell); }}

  .news-text {{ background: linear-gradient(135deg, #0b1220 0%, #162033 100%);
    border: 1px solid var(--border); border-left: 3px solid var(--accent);
    border-radius: 10px; padding: 14px 16px; margin-top: 6px; }}
  .news-text .lbl {{ color: var(--accent); font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; }}
  .news-text .body {{ line-height: 1.7; font-size: 14px; color: #cbd5e1; }}

  .advice {{ margin-top: 14px; background: linear-gradient(135deg, #0b1220 0%, #1a2739 100%);
    border: 1px solid var(--border); border-left: 3px solid var(--wait);
    border-radius: 10px; padding: 14px 16px; }}
  .advice .lbl {{ color: var(--wait); font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; }}
  .advice-headline {{ font-size: 15px; font-weight: 700; margin-bottom: 8px; color: #fde68a; }}
  .advice-hint {{ font-size: 13px; color: #cbd5e1; margin-bottom: 10px; font-style: italic; }}
  .advice-table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px;
    font-size: 13px; background: #0b1220; border-radius: 8px; overflow: hidden; }}
  .advice-table th, .advice-table td {{ padding: 8px 10px; text-align: left;
    border-bottom: 1px solid var(--border); }}
  .advice-table th {{ color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: .05em; }}
  .adv-sym {{ font-weight: 700; color: var(--accent); }}
  .sig {{ font-weight: 700; padding: 2px 8px; border-radius: 6px; font-size: 12px; }}
  .sig-buy  {{ background: rgba(74,222,128,.15); color: var(--buy); }}
  .sig-sell {{ background: rgba(248,113,113,.15); color: var(--sell); }}
  .adv-reason {{ color: var(--muted); font-size: 12px; }}
  .advice-confidence {{ font-size: 13px; color: #cbd5e1; margin-bottom: 6px; }}
  .advice-note {{ font-size: 12px; color: #cbd5e1; margin-bottom: 8px;
    padding: 8px 10px; background: rgba(251,191,36,.08);
    border-left: 2px solid var(--wait); border-radius: 4px; }}
  .advice-disclaimer {{ font-size: 11px; color: var(--muted); font-style: italic;
    padding-top: 6px; border-top: 1px dashed var(--border); }}

  .src-link {{ display: inline-block; margin-top: 14px; color: var(--accent);
    font-size: 13px; text-decoration: none; border-bottom: 1px dashed var(--accent); }}
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
    <h1>📊 MQL5 Economic News — {today_str}</h1>
    <div class="meta">Generated: {generated_at} &nbsp;•&nbsp; {total} events today &nbsp;•&nbsp; Click any row for details</div>
  </header>

  <div class="next-banner" id="nextBanner">
    <div class="left">
      <div class="lbl">⏱ Next event</div>
      <div class="name" id="nextName">Loading…</div>
      <div class="sub" id="nextSub">—</div>
    </div>
    <div class="countdown" id="countdown">—</div>
  </div>

  <div class="symbols-bar">
    <span class="lbl">🔌 Connected symbols:</span>
    <span>{escape(symbols_str)}</span>
    <span class="lbl">·&nbsp; Relevant currencies:</span>
    <span>{escape(rel_ccy_str)}</span>
    <span class="lbl">·&nbsp; Legend:</span>
    <code style="color:#fbbf24">🟡 XAUUSD</code>
    <code style="color:#38bdf8">🔵 XAGUSD</code>
  </div>

  <div class="stats">
    <div class="stat high"><div class="num">{highs}</div><div class="lbl">High</div></div>
    <div class="stat medium"><div class="num">{mediums}</div><div class="lbl">Medium</div></div>
    <div class="stat low"><div class="num">{lows}</div><div class="lbl">Low</div></div>
    <div class="stat rel"><div class="num">{relevant_count}</div><div class="lbl">Relevant</div></div>
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
    <label class="chk-label">
      <input type="checkbox" id="relFilter" onchange="filterRows()">
      ✅ Only relevant to my symbols
    </label>
    <label class="chk-label">
      <input type="checkbox" id="upFilter" onchange="filterRows()">
      ⏱ Only upcoming
    </label>
    <span id="visibleCount" class="meta" style="align-self:center"></span>
  </div>

  <table id="newsTable">
    <thead>
      <tr>
        <th class="xcol" title="Relevance">X</th>
        <th>Time (Tehran)</th>
        <th>From now</th>
        <th>CCY</th><th>Impact</th><th>Event</th>
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

  <footer>Generated locally • No API credits used • All times shown in Tehran (UTC+3:30)</footer>

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
        <div class="rel-banner" id="c-rel">—</div>
        <div class="grid" id="c-grid"></div>

        <div class="news-text">
          <div class="lbl">📰 News Text</div>
          <div class="body" id="c-text">—</div>
        </div>

        <div class="advice" id="c-advice" style="display:none">
          <div class="lbl">💹 Trade Analysis</div>
          <div id="c-advice-body"></div>
        </div>

        <a id="c-source" class="src-link" href="#" target="_blank" rel="noopener">🔗 Official source</a>
      </div>
    </div>
  </div>

<script>
const NEWS = {payload_json};

function humanDelta(ms) {{
  const past = ms < 0;
  let s = Math.abs(Math.floor(ms / 1000));
  const d = Math.floor(s / 86400); s %= 86400;
  const h = Math.floor(s / 3600);  s %= 3600;
  const m = Math.floor(s / 60);    s %= 60;
  let parts = [];
  if (d) parts.push(d + 'd');
  if (h || d) parts.push(h + 'h');
  parts.push(m + 'm');
  if (!d && !h) parts.push(s + 's');
  return (past ? '−' : 'in ') + parts.join(' ');
}}

function shortDelta(ms) {{
  const past = ms < 0;
  let s = Math.abs(Math.floor(ms / 1000));
  const h = Math.floor(s / 3600); s %= 3600;
  const m = Math.floor(s / 60);   s %= 60;
  if (h > 0) return (past ? '−' : '') + h + 'h ' + m + 'm';
  if (m > 0) return (past ? '−' : '') + m + 'm ' + s + 's';
  return (past ? '−' : '') + s + 's';
}}

function tick() {{
  const now = Date.now();
  document.querySelectorAll('#newsTable tbody tr').forEach(tr => {{
    const cell = tr.querySelector('.rel-time');
    if (!cell) return;
    const iso = cell.dataset.iso;
    if (!iso) {{ cell.textContent = '—'; return; }}
    const t = new Date(iso).getTime();
    const delta = t - now;
    cell.textContent = humanDelta(delta);
    cell.classList.toggle('live', Math.abs(delta) < 60000);
    cell.classList.toggle('soon', delta > 0 && delta < 900000);
  }});

  let next = null;
  NEWS.forEach(n => {{
    if (!n.timeIso) return;
    const t = new Date(n.timeIso).getTime();
    if (t > now && (!next || t < new Date(next.timeIso).getTime())) next = n;
  }});

  const banner = document.getElementById('nextBanner');
  const nameEl = document.getElementById('nextName');
  const subEl  = document.getElementById('nextSub');
  const cdEl   = document.getElementById('countdown');

  document.querySelectorAll('tr.is-next').forEach(r => r.classList.remove('is-next'));

  if (next) {{
    banner.classList.remove('empty');
    nameEl.textContent = next.name;
    const matched = next.matchedSyms && next.matchedSyms.length
      ? ' · affects ' + next.matchedSyms.join(', ') : '';
    subEl.textContent = next.timeTehran + ' · ' + next.currency + ' · ' +
                        next.importance.toUpperCase() + matched;
    const delta = new Date(next.timeIso).getTime() - now;
    cdEl.textContent = shortDelta(delta);
    cdEl.classList.toggle('soon', delta < 900000 && delta > 0);
    cdEl.classList.toggle('live', Math.abs(delta) < 60000);
    cdEl.classList.remove('past');
    const idx = NEWS.indexOf(next);
    const row = document.querySelector(`tr[data-idx="${{idx}}"]`);
    if (row) row.classList.add('is-next');
  }} else {{
    banner.classList.add('empty');
    nameEl.textContent = 'No more events today';
    subEl.textContent = 'All scheduled events have passed.';
    cdEl.textContent = '—';
    cdEl.className = 'countdown past';
  }}
}}

setInterval(tick, 1000);
tick();

function field(k, v, cls="") {{
  return `<div class="field"><div class="k">${{k}}</div><div class="v ${{cls}}">${{v}}</div></div>`;
}}

function openCard(idx) {{
  const n = NEWS[idx];
  if (!n) return;

  document.getElementById('c-name').textContent = n.name;
  document.getElementById('c-sub').innerHTML =
    `<span class="ccy">${{n.currency}}</span> &nbsp;•&nbsp; ${{n.country}} &nbsp;•&nbsp; ${{n.importance.toUpperCase()}} impact &nbsp;•&nbsp; ${{n.type}}`;

  const rel = document.getElementById('c-rel');
  if (n.relevant) {{
    rel.className = 'rel-banner yes';
    rel.textContent = `✅ Affects your connected symbols: ${{n.matchedSyms.join(', ')}}`;
  }} else {{
    rel.className = 'rel-banner no';
    rel.textContent = '❎ Does not affect your connected symbols';
  }}

  let aCls = "";
  const a = parseFloat(n.actual), f = parseFloat(n.forecast);
  if (!isNaN(a) && !isNaN(f)) aCls = a > f ? "beat" : (a < f ? "miss" : "");

  let relTxt = '—';
  if (n.timeIso) {{
    const delta = new Date(n.timeIso).getTime() - Date.now();
    relTxt = humanDelta(delta);
  }}

  const grid = [
    field("Time (Tehran)", n.timeTehran, "big"),
    field("From now",      relTxt),
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

  const advWrap = document.getElementById('c-advice');
  const advBody = document.getElementById('c-advice-body');
  if (n.adviceHtml) {{
    advWrap.style.display = 'block';
    advBody.innerHTML = n.adviceHtml;
  }} else {{
    advWrap.style.display = 'none';
    advBody.innerHTML = '';
  }}

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

document.querySelectorAll('#newsTable tbody tr').forEach(tr => {{
  tr.addEventListener('click', () => openCard(parseInt(tr.dataset.idx, 10)));
}});

function filterRows() {{
  const q    = document.getElementById('search').value.toLowerCase();
  const imp  = document.getElementById('impFilter').value;
  const ccy  = document.getElementById('ccyFilter').value;
  const rel  = document.getElementById('relFilter').checked;
  const up   = document.getElementById('upFilter').checked;
  const now  = Date.now();
  let visible = 0;
  document.querySelectorAll('#newsTable tbody tr').forEach(tr => {{
    const name = tr.querySelector('.name').textContent.toLowerCase();
    const iso  = tr.querySelector('.rel-time')?.dataset.iso || '';
    const isUpcoming = iso ? new Date(iso).getTime() > now : false;
    const ok = (!q || name.includes(q)) &&
               (!imp || tr.dataset.importance === imp) &&
               (!ccy || tr.dataset.currency === ccy) &&
               (!rel || tr.dataset.relevant === '1') &&
               (!up  || isUpcoming);
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
    print(f"[i] Breakdown — High: {highs} | Medium: {mediums} | Low: {lows} | Relevant: {relevant_count} | Total: {total}")


if __name__ == "__main__":
    news = load_news(today_only=True)
    if not news:
        print("[!] Nothing to export.")
    else:
        generate_html(news, output="news_report.html")