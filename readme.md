# 📊 MQL5 Economic News → HTML Report

A free, local Python tool that fetches economic news/calendar events, filters them by relevance to your **connected MT5 symbols**, predicts **BUY/SELL signals** for upcoming releases, and exports everything to a single self-contained **HTML dashboard** — no API credits required.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🆓 **100% Free** | Uses `biquote` (no API key) or your local `news.json` export |
| 📅 **Today-Only Filter** | Auto-filters events to today's Tehran date |
| 🕒 **Tehran Timezone** | All times shown as **UTC+3:30** (Iran Standard Time) |
| ⏱ **Live Countdown** | Banner at the top shows time until the next event (updates every second) |
| 🔔 **Row Countdown** | Every row shows "from now" — live-updating without page refresh |
| ✅ **Symbol Relevance** | Auto-detects your connected MT5 symbols → marks rows ✅ / ❎ |
| 🥇 **XAUUSD Gold Glow** | Pulsing gold neon on rows affecting gold |
| 🔵 **XAGUSD Cyan Glow** | Pulsing cyan neon on rows affecting silver |
| 💹 **Trade Analysis** | Auto BUY/SELL signal for each relevant symbol |
| 🔄 **Inverse-Aware** | Handles Jobless Claims, Inventories, etc. correctly |
| 🎴 **Detail Card Modal** | Click any row → full data + news narrative + trade advice |
| 🔍 **Live Filters** | Search by name, filter by impact, currency, relevance, upcoming-only |
| 📱 **Responsive** | Works on desktop, tablet, and mobile |

---

## 🚀 Quick Start

### 1. Install dependencies

```powershell
pip install biquote
```

*Optional but recommended — for live MT5 symbol detection:*

```powershell
pip install MetaTrader5
```

### 2. Run the script

```powershell
cd C:\Users\Shayan\Desktop\YTStrategy
py news_to_html.py
```

### 3. Open the report

```
news_report.html
```

Double-click it, or open it in any browser.

---

## 📁 Project Structure

```
YTStrategy/
├── news_to_html.py        # Main script
├── news_report.html       # Generated report (open in browser)
├── news.json              # OPTIONAL: your MQL5 export (fallback data)
└── README.md              # This file
```

---

## 🔌 Data Sources (in priority order)

The script tries these in order:

| # | Source | When used |
|---|---|---|
| 1 | **`news.json`** (local file) | If the file exists and contains a JSON array |
| 2 | **`biquote`** live fetch | If `news.json` is missing/empty |
| 3 | **`LOCAL_NEWS`** (inline in script) | If both above fail |

### Example `news.json` (MQL5 export format)

```json
[
  {
    "id": "mql5:317675",
    "eventId": "mql5:840140001",
    "time": "2026-10-08T12:30:00Z",
    "period": "2026-10-03T00:00:00Z",
    "countryCode": "US",
    "currency": "USD",
    "name": "Initial Jobless Claims",
    "importance": "high",
    "type": "indicator",
    "sector": "jobs",
    "unit": "none",
    "multiplier": "thousands",
    "digits": 0,
    "actual": null,
    "forecast": 190,
    "previous": 197,
    "sourceUrl": "https://www.dol.gov",
    "source": "mql5"
  }
]
```

---

## 🎯 How Symbol Detection Works

The script tries to read **live symbols from MT5**:

```python
import MetaTrader5 as mt5
mt5.initialize()
symbols = [s.name for s in mt5.symbols_get()]
```

If MT5 isn't available, it falls back to:

```python
FALLBACK_SYMBOLS = ["XAUUSD", "XAGUSD"]
```

Then it extracts currency codes from each symbol:

| Symbol | Currencies detected |
|---|---|
| `XAUUSD` | `XAU`, `USD` |
| `XAGUSD` | `XAG`, `USD` |
| `USDZAR` | `USD`, `ZAR` |
| `EURUSD` | `EUR`, `USD` |
| `ZARJPY` | `ZAR`, `JPY` |

Any event whose currency matches one of those gets **✅** in the X column.

---

## 💹 Trade Signal Logic

### Standard indicators (higher = stronger currency)

| Scenario | Base currency | Signals |
|---|---|---|
| Forecast > Previous | Strengthens 📈 | BUY base pairs, SELL base-quote pairs |
| Forecast < Previous | Weakens 📉 | SELL base pairs, BUY base-quote pairs |
| Actual > Forecast | Beat → Strengthens 📈 | Same as above |
| Actual < Forecast | Miss → Weakens 📉 | Same as above |
| In-line | Neutral | Block hidden |

### Inverse indicators (higher = weaker currency)

Handled automatically for:
- **Jobless Claims** / **Unemployment** / **Layoffs**
- **Bankruptcy** / **Default**
- **Inventories** / **Stockpiles**

For these, the signal logic flips. Example:

> **Initial Jobless Claims** — Forecast `190` < Previous `197`
> → Fewer claims = **good for USD** → **USD strengthens** → **SELL XAUUSD** ✅

The headline shows `[inverse]` so you know why.

---

## 🎨 Visual Legend

| Element | Meaning |
|---|---|
| ✅ Green check | Event affects your symbols |
| ❎ Gray X | Event doesn't affect your symbols |
| 🟡 Gold glow | Row affects **XAUUSD** (gold) |
| 🔵 Cyan glow | Row affects **XAGUSD** (silver) |
| ⏱ NEXT badge | The next upcoming event |
| 🟢 BUY | Long signal |
| 🔴 SELL | Short signal |
| 🔮 PREDICTED | Pre-release forecast bias |
| 📈 BEAT | Actual exceeded forecast |
| 📉 MISS | Actual missed forecast |
| ➖ IN-LINE | Actual matched forecast |

---

## 🖱 Interaction Guide

| Action | Result |
|---|---|
| **Click any row** | Opens the detail card modal |
| **Esc key** | Closes the card |
| **Click backdrop** | Closes the card |
| **Search box** | Live filter by event name |
| **Impact dropdown** | Filter high / medium / low |
| **Currency dropdown** | Filter by currency |
| **✅ checkbox** | Show only events relevant to your symbols |
| **⏱ checkbox** | Show only upcoming events |

---

## ⚙️ Configuration

Edit these constants at the top of `news_to_html.py`:

### Change fallback symbols

```python
FALLBACK_SYMBOLS = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD"]
```

### Change timezone

```python
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30), name="Tehran")
```

### Add custom inverse indicators

```python
INVERSE_KEYWORDS = [
    "jobless", "unemployment", "claims",
    "your_custom_keyword_here",
]
```

### Fetch only today vs. all events

At the bottom of the script:

```python
news = load_news(today_only=True)   # or False for all events
```

---

## 🧠 How It Works (Flow)

```
┌─────────────────┐
│  1. Load News   │  news.json → biquote → LOCAL_NEWS
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Detect MT5   │  MetaTrader5.symbols_get() → fallback list
│    Symbols      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Match Events │  Event currency in symbol currencies?
│    to Symbols   │  → mark ✅ / ❎, add neon class
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Build Trade  │  Inverse-aware BUY/SELL per matched symbol
│    Advice       │  Skip NO TRADE rows entirely
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Render HTML  │  Single self-contained file with CSS + JS
│    Report       │  Live countdown, filters, modal card
└─────────────────┘
```

---

## 🛠 Troubleshooting

### ❌ `Error: 401 — This endpoint requires credits`

**Cause:** You're using JBlanked's paid API.
**Fix:** You don't need it. This script uses `biquote` (free). Remove any old JBlanked code.

---

### ❌ All rows show blank (empty name, currency, etc.)

**Cause:** `biquote` field names don't match expectations.
**Fix:** Run the script — it prints `[i] Sample fields: [...]`. Share that output to map the field names.

---

### ❌ `MetaTrader5 package not installed`

**Cause:** MT5 Python package is missing.
**Fix:** `pip install MetaTrader5`. Or ignore — the script uses fallback symbols.

---

### ❌ Neon glow appears on wrong rows

**Cause:** Your `matched` list contains multiple symbols.
**Fix:** The code checks `XAUUSD` first, then `XAGUSD`. To prioritize silver, swap the `if/elif` order in `build_row()`.

---

### ❌ Times look wrong

**Cause:** Tehran timezone may be misconfigured.
**Fix:** Verify `TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))` — Iran has **no DST** since 2022.

---

### ❌ BUY/SELL signals are inverted

**Cause:** Indicator is inverse but not in `INVERSE_KEYWORDS`.
**Fix:** Add the keyword to the list. Example: `"retail_sales"` if you consider it inverse.

---

## 📋 Requirements

- **Python** 3.8+
- **biquote** (`pip install biquote`) — free news feed
- **MetaTrader5** (`pip install MetaTrader5`) — *optional*, for live symbol detection
- **No API keys required** ✅
- **No internet needed** after first fetch (HTML is self-contained) ✅

---

## 📊 Example Output

```
[i] Connected symbols: XAUUSD, XAGUSD, EURUSD, GBPUSD, USDJPY, USDZAR
[i] Relevant currencies: AUD, EUR, GBP, JPY, USD, XAG, XAU, ZAR
[i] biquote returned 42 raw events.
[i] Filtered to today (Tehran): 12 events.
[✓] HTML report written → C:\Users\Shayan\Desktop\YTStrategy\news_report.html
[i] Breakdown — High: 5 | Medium: 4 | Low: 3 | Relevant: 9 | Total: 12
```

---

## 🎯 Typical Workflow

1. **Morning** — Run `py news_to_html.py`
2. **Open** `news_report.html` in your browser
3. **Watch** the ⏱ NEXT banner countdown
4. **Click** any relevant row for full analysis
5. **Trade** the BUY/SELL signals the card suggests
6. **Re-run** the script for updated data (e.g., every 30 minutes)

---

## ⚠️ Disclaimer

> **This tool is for educational and informational purposes only.**
>
> - All trade signals are algorithmically generated from public economic data.
> - **Not financial advice.** Always do your own research.
> - Use proper risk management — **max 1–2% per trade**.
> - Past performance does not guarantee future results.
> - The authors are not responsible for any trading losses.

---

## 📜 License

MIT — free to use, modify, and distribute.

---

## 🙏 Credits

- **News data:** [biquote](https://pypi.org/project/biquote/)
- **Symbol detection:** [MetaTrader5 Python API](https://www.mql5.com/en/docs/python_metatrader5)
- **Original MQL5 calendar data:** [MetaQuotes](https://www.mql5.com/en/economic-calendar)

---

## 📞 Support

If something breaks:

1. Check the **Troubleshooting** section above.
2. Run the script and **copy the console output** — it prints diagnostic info.
3. Verify your `news.json` is valid JSON (use an online validator).
4. Confirm Python version: `py --version` (should be 3.8+).

---

**Happy trading! 🚀📈**
