import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
from config import GEMINI_API_KEY

class ForexAnalyzer:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def fetch_data(self, symbol, period, interval):
        """
        Fetches OHLC data using yfinance.
        """
        try:
            # yfinance tickers for forex often have '=X' suffix, e.g., 'EURUSD=X'
            if not symbol.endswith('=X') and len(symbol) == 6: 
                 # Basic check, user might input 'EURUSD'
                 ticker_symbol = f"{symbol}=X"
            else:
                ticker_symbol = symbol

            ticker = yf.Ticker(ticker_symbol)
            # period can be '1mo', '1y', etc. or use start/end. 
            # validating period might be needed, but yf handles it well usually.
            # However, for '100 candles', we usually fetch a standard period that covers it.
            # Mapping user '100 candles' to a period is tricky without specific start dates.
            # We'll stick to a default period that ensures enough data for now, 
            # or allow the user to specify standard yf periods. 
            # app_flow says: "Fetches the requested number of candles (e.g., 100)"
            # yfinance download doesn't support 'limit'.
            # We will fetch a longer period and slice.
            
            # Map user timeframe to reasonable fetch limit
            # This is a simplification. 
            if interval in ['1h', '4h']:
                 fetch_period = "1mo" # Should be enough for 100 candles
            elif interval == '1d':
                 fetch_period = "1y"
            else:
                 fetch_period = "1mo"

            df = ticker.history(period=fetch_period, interval=interval)
            
            if df.empty:
                return None, "No data found for symbol."
            
            # Slice to requested number of candles (end of list is most recent)
            # User wants e.g. 100 candles.
            # But creating indicators requires more history (pre-warming).
            # We will keep all data for calc, then slice for display/prompt if needed.
            return df, None
        except Exception as e:
            return None, str(e)

    def calculate_indicators(self, df):
        """
        Calculates EMA 50, EMA 200, RSI 14, and ATR 14.
        """
        try:
             # Ensure we have enough data
            if len(df) < 200:
                print("Warning: Not enough data for 200 EMA.")

            # Calculate indicators using pandas_ta
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            
            return df
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return df

    def generate_prompt(self, df, news, symbol):
        """
        Constructs the prompt for Gemini.
        """
        # Get latest values
        latest = df.iloc[-1]
        
        # Determine Trend
        trend = "NEUTRAL"
        if pd.notna(latest['EMA_200']):
            if latest['Close'] > latest['EMA_200']:
                trend = "BULLISH"
            else:
                trend = "BEARISH"
        
        # Format values
        rsi = f"{latest['RSI']:.2f}" if pd.notna(latest['RSI']) else "N/A"
        atr = f"{latest['ATR']:.4f}" if pd.notna(latest['ATR']) else "N/A"
        price = f"{latest['Close']:.5f}"
        
        prompt = f"""
You are a professional Forex trader using a Swing Trading strategy.

**Market Data for {symbol}:**
- Current Price: {price}
- Trend (vs 200 EMA): {trend}
- RSI (14): {rsi}
- Volatility (ATR): {atr}

**Fundamental News / Context:**
"{news}"

**Task:**
Analyze the provided technical and fundamental data.
1. Determine the trade decision: BUY, SELL, or WAIT.
2. If acting (BUY/SELL):
    - Set Entry Price (use current price or a close pending order).
    - Set Stop Loss (SL) based on the ATR (e.g., 1.5x ATR).
    - Set Take Profit (TP) aiming for at least a 1:2 Risk-Reward Ratio.
    - Provide a reasoning summary.

**Output Format:**
Return ONLY a valid JSON object with the following keys:
{{
  "decision": "BUY" | "SELL" | "WAIT",
  "entry": float or null,
  "stop_loss": float or null,
  "take_profit": float or null,
  "reasoning": "string"
}}
"""
        return prompt

    def analyze_with_gemini(self, prompt):
        """
        Calls Gemini API.
        """
        if not self.model:
            return {"error": "API Key missing"}
        
        try:
            response = self.model.generate_content(prompt)
            # Cleanup markdown code blocks if present
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            return {"error": str(e)}
