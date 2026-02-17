Here is the comprehensive summary of the **AI Forex Swing Assistant** application flow. This strategy leverages the strengths of Python (math/data) and Gemini Flash (reasoning/context).

### **1. The Strategy Profile**
*   **Trading Style:** Swing Trading (positions held for days/weeks).
*   **Timeframe:** 4-Hour (4H) or Daily (1D).
*   **AI Model:** Google Gemini 1.5 Flash (Low latency, large context window).
*   **Risk Management:** Volatility-based (using ATR).

---

### **2. The Application Flow (Step-by-Step)**

#### **Phase 1: Input (Data Gathering)**
*   **User Action:** You open the GUI and select a pair (e.g., `EURUSD`).
*   **User Action:** You select the **Timeframe** (e.g., `1H`, `4H`, `1D`) and the **Number of Candles** to analyze.
*   **User Action:** You copy-paste the latest major economic news or fundamental context into the text box (e.g., *"Fed Chair Powell suggests interest rates will stay high"*).
*   **System Action (Python):**
    *   Fetches the requested number of candles (e.g., 100) of OHLC data for the chosen timeframe via `yfinance` (or `MT5`).
    *   *Why?* To get the raw price action structure according to user preference.

#### **Phase 2: Pre-Processing (The Mathematical Layer)**
*   **Who does it:** Python (`pandas_ta` library).
*   **Why:** LLMs are bad at calculation. Python prepares the "Hard Facts."
*   **Calculations:**
    1.  **Trend:** Calculates 50 EMA and 200 EMA to determine if the long-term trend is Bullish or Bearish.
    2.  **Momentum:** Calculates RSI (14) to see if the market is Overbought (>70) or Oversold (<30).
    3.  **Volatility:** Calculates **ATR (Average True Range)**. *This is crucial for calculating a safe Stop Loss.*

#### **Phase 3: The "Prompt" (Context Assembly)**
*   **Who does it:** Python.
*   **Action:** It formats a text prompt for Gemini that looks like this:
    > "You are a professional trader.
    > **Technical Context:** EURUSD is in a BEARISH trend (Price < 200 EMA). RSI is 65 (Neutral). Volatility (ATR) is 0.0040.
    > **Fundamental Context:** [User Paste: Fed rates staying high].
    > Based on this, decide BUY/SELL/WAIT. If acting, set SL at 1.5x ATR."

#### **Phase 4: The Analysis (The Reasoning Layer)**
*   **Who does it:** Gemini 3 Flash API.
*   **Action:**
    1.  Reads the Fundamental News (identifies sentiment: Hawkish/Dovish/Fear/Greed).
    2.  Checks if Fundamentals align with Technicals (e.g., "News is bad for Euro, and Technical Trend is Bearish -> **High Probability Short**").
    3.  Calculates Entry, SL, and TP based on the ATR rule provided in the prompt.
    4.  Outputs a JSON object.

#### **Phase 5: The Output (The User Interface)**
*   **Who does it:** CustomTkinter (GUI).
*   **Action:** Displays a clean notification card:
    *   **Decision:** 🔴 **SELL**
    *   **Entry:** 1.0500
    *   **Stop Loss:** 1.0560 (Calculated via ATR)
    *   **Take Profit:** 1.0380 (1:2 Risk Ratio)
    *   **Reasoning:** *"Technicals show a downtrend and the RSI has room to fall. Fundamentals regarding the Fed are bearish for EUR/USD. The alignment suggests a short position."*

---

### **3. Why this flow works**
1.  **No Hallucinated Math:** Python calculates the indicators, so the AI doesn't guess the RSI value.
2.  **Dynamic Risk:** By passing the `ATR` value to the AI, your Stop Loss is always adapted to the current market speed (tight SL in quiet markets, wide SL in volatile markets).
3.  **Human-in-the-Loop:** You act as the filter for News. You control what the AI reads, preventing it from reacting to "fake news" or irrelevant articles.

Do you want to proceed with writing the final code for this specific flow?