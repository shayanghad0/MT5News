# 📊 MQL5 Economic News → HTML Report

A free, local Python tool that fetches economic news/calendar events, filters them by relevance to your **connected MT5 symbols**, predicts **BUY/SELL signals** for upcoming releases, and exports everything to:

- 🎨 A single self-contained **HTML dashboard** for humans
- 🤖 A rich **structured JSON** (`news_metadata.json`) for AI analysis

**No API credits required.**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🆓 **100% Free** | Uses `biquote` (no API key, no signup) |
| 📅 **Today-Only Filter** | Auto-filters events to today's Tehran date |
| 🕒 **Tehran Timezone** | All times shown as **UTC+3:30** (Iran Standard Time) |
| ⏱ **Live Countdown** | Top banner shows time until the next event (updates every second) |
| 🔔 **Row Countdown** | Every row shows "from now" — live-updating without page refresh |
| ✅ **Symbol Relevance** | Auto-detects your connected MT5 symbols → marks rows ✅ / ❎ |
| 🥇 **XAUUSD Gold Glow** | Pulsing gold neon on rows affecting gold |
| 🔵 **XAGUSD Cyan Glow** | Pulsing cyan neon on rows affecting silver |
| 💹 **Trade Analysis** | Auto BUY/SELL signal for each relevant symbol |
| 🔄 **Inverse-Aware** | Handles Jobless Claims, Inventories, etc. correctly |
| 🚫 **No NO-TRADE Rows** | Only shows actionable BUY/SELL signals |
| 🎴 **Detail Card Modal** | Click any row → full data + news narrative + trade advice |
| 🔍 **Live Filters** | Search, impact, currency, relevance, upcoming-only |
| 🤖 **AI Metadata Export** | `news_metadata.json` with raw data + analytics + signals |
| 📱 **Responsive** | Works on desktop, tablet, and mobile |

---

## 🚀 Quick Start

### 1. Install dependencies

```powershell
pip install biquote
```

*Optional — for live MT5 symbol detection:*

```powershell
pip install MetaTrader5
```

### 2. Run the script

```powershell
cd C:\Users\Shayan\Desktop\YTStrategy
py news_to_html.py
```

### 3. Open the outputs

- **`news_report.html`** — the visual dashboard
- **`news_metadata.json`** — structured data for AI analysis

---

## 📁 Project Structure

```
YTStrategy/
├── news_to_html.py        # Main script
├── news_report.html       # 📊 Generated HTML dashboard
├── news_metadata.json     # 🤖 Generated AI-friendly JSON
└── README.md              # This file
```

> **Note:** `news.json` is **no longer used**. The script fetches live data directly from `biquote`. You can safely delete any old `news.json` file.

---

## 🔌 Data Flow

The script fetches news in this order:

| # | Source | When used |
|---|---|---|
| 1 | **`biquote`** live fetch | Always tried first |
| 2 | **`LOCAL_NEWS`** (inline list in script) | If biquote fails |
| 3 | *(nothing)* | Prints warning, exits cleanly |

---

## 📤 Output Files

Every run produces **two files**:

### 📊 `news_report.html`

- Self-contained (CSS + JS embedded)
- Interactive filters, live countdowns, click-to-open modal cards
- No internet needed after the initial fetch
- Opens in any browser

### 🤖 `news_metadata.json`

A rich structured export designed for AI analysis. Contains:

| Section | Contents |
|---|---|
| `meta` | Generator version, timestamps, schema info |
| `marketContext` | Connected symbols, currencies, inverse keywords |
| `statistics` | Aggregate counts (high/medium/low, BUY/SELL totals) |
| `nextEvent` | Info about the next upcoming release |
| `events[]` | Per-event records with **raw numbers** + **derived analytics** + **per-symbol signals** |

**Example event record:**

```json
{
  "name": "Initial Jobless Claims",
  "currency": "USD",
  "importance": "high",
  "inverseIndicator": true,
  "actual": null,
  "forecast": 190.0,
  "previous": 197.0,
  "deviation": null,
  "surprise": null,
  "trend": "down",
  "trendDir": "forecast lower than previous",
  "isUpcoming": true,
  "isReleased": false,
  "secondsUntil": 1800,
  "isRelevant": true,
  "matchedSymbols": ["XAUUSD", "XAGUSD", "EURUSD", "..."],
  "tradeScenario": "pre",
  "baseCurrencyStrength": "stronger",
  "tradeHeadline": "🔮 PREDICTED — Forecast 190 < Previous 197 → USD bias STRONGER [inverse]",
  "symbolSignals": [
    {"symbol": "XAUUSD", "signal": "SELL", "reason": "USD biased STRONGER"},
    {"symbol": "XAGUSD", "signal": "SELL", "reason": "USD biased STRONGER"}
  ],
  "newsText": "Initial Jobless Claims is a high-impact release..."
}
```

### 🤖 How to Use the Metadata with an AI

```python
import json

with open("news_metadata.json") as f:
    data = json.load(f)

# Filter to high-impact upcoming relevant events
relevant = [
    e for e in data["events"]
    if e["isUpcoming"] and e["isRelevant"] and e["importance"] == "high"
]

# Feed to ChatGPT / Claude / etc.:
prompt = f"""
Here is today's economic calendar in structured JSON.
Analyse which events are most likely to move my symbols
({', '.join(data['marketContext']['connectedSymbols'])})
and suggest a trading plan.

Data: {json.dumps(relevant, indent=2)}
"""
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
| In-line | Neutral | **Block hidden** |
| No data | Neutral | **Block hidden** |

### Inverse indicators (higher = weaker currency)

Handled automatically for:
- **Jobless Claims** / **Unemployment** / **Layoffs**
- **Bankruptcy** / **Default**
- **Inventories** / **Stockpiles**

For these, the signal logic flips. Example:

> **Initial Jobless Claims** — Forecast `190` < Previous `197`
> → Fewer claims = **good for USD** → **USD strengthens** → **SELL XAUUSD** ✅

The headline shows `[inverse]` so you know why.

### No NO-TRADE clutter

When a signal would be "NO TRADE", that row is **skipped entirely**. If all matched symbols end up with no signal, the **entire Trade Analysis block is hidden** on the card. You only ever see actionable **🟢 BUY** or **🔴 SELL**.

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

### Fetch today vs. all events

At the bottom of the script:

```python
news = load_news(today_only=True)   # or False for all events
```

---

## 🧠 How It Works (Flow)

```
┌─────────────────┐
│  1. Fetch News  │  biquote → LOCAL_NEWS → warn
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
         ├──────────────────┐
         ▼                  ▼
┌─────────────────┐  ┌──────────────────┐
│ 5a. Export      │  │ 5b. Render HTML  │
│  Metadata JSON  │  │  Report          │
│  (for AI)       │  │  (for humans)    │
└─────────────────┘  └──────────────────┘
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

### ❌ Trade Analysis block missing from card

**Not a bug.** If all matched symbols would produce NO TRADE (in-line result, no forecast, no data), the block is hidden entirely by design.

---

### ❌ `news_metadata.json` is too large

**Cause:** The file includes every event with full analytics.
**Fix:** Filter with Python after loading — e.g., keep only `isRelevant: true` events. Or edit `export_metadata()` to skip irrelevant events.

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
[✓] Using 12 events from biquote.
[✓] AI metadata written → C:\Users\Shayan\Desktop\YTStrategy\news_metadata.json
[i] 12 events, 9 relevant, 42 BUY signals, 38 SELL signals
[✓] HTML report written → C:\Users\Shayan\Desktop\YTStrategy\news_report.html
[i] Breakdown — High: 5 | Medium: 4 | Low: 3 | Relevant: 9 | Total: 12
```

---

## 🎯 Typical Workflow

### Manual (for trading)

1. **Morning** — Run `py news_to_html.py`
2. **Open** `news_report.html` in your browser
3. **Watch** the ⏱ NEXT banner countdown
4. **Click** any relevant row for full analysis
5. **Trade** the BUY/SELL signals the card suggests
6. **Re-run** the script for updated data (e.g., every 30 minutes)

### AI-Assisted (for deeper analysis)

1. Run `py news_to_html.py` → generates `news_metadata.json`
2. Load it in a Python notebook / ChatGPT / Claude
3. Ask questions like:
   - *"Which events today are most likely to move XAUUSD?"*
   - *"Rank the high-impact events by expected volatility."*
   - *"Build me a trading plan for the next 4 hours."*
4. Cross-check with `news_report.html` before executing

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
3. Confirm Python version: `py --version` (should be 3.8+).
4. Check `news_metadata.json` — it contains the exact data the script is working with.

---

**Happy trading! 🚀📈**