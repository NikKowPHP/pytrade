
import pandas as pd
import concurrent.futures
from services.logger import Logger

class ScannerService:
    def __init__(self, data_provider, ai_service=None):
        self.logger = Logger()
        self.data_provider = data_provider
        self.ai_service = ai_service # Inject AI service

    def scan_symbol(self, symbol, timeframe):
        """
        Analyzes a symbol. Returns a dict if 'Interesting', else None.
        """
        try:
            # 1. Fetch Data (Fast fetch, we don't need full history, just 200 candles)
            # Note: In a real app, you might optimize fetch_data to get less data for scanning
            df, error = self.data_provider.fetch_data(symbol, timeframe)
            if error or df is None or df.empty:
                return None
            
            # 2. Indicators
            df = self.data_provider.calculate_indicators(df)
            latest = df.iloc[-1]
            
            # 3. Logic: Filter for "Attention Needed"
            rsi = latest['RSI'] if pd.notna(latest['RSI']) else 50
            close = latest['Close']
            ema_200 = latest['EMA_200']
            
            signal_type = "NEUTRAL"
            score = 0 # 0 to 10 scale of importance
            details = ""

            # RSI Extremes
            if rsi > 70:
                signal_type = "OVERBOUGHT"
                score = 8
                details = f"RSI {rsi:.1f}"
            elif rsi < 30:
                signal_type = "OVERSOLD"
                score = 8
                details = f"RSI {rsi:.1f}"

            # EMA Trend Test (Price close to EMA)
            if pd.notna(ema_200):
                dist_pct = abs(close - ema_200) / ema_200
                if dist_pct < 0.002: # Within 0.2%
                    signal_type = "EMA 200 TEST"
                    score = 9
                    details = "Testing Major Trend"

            # If score is high enough, return result
            if score >= 5:
                # Return standardized dict
                return {
                    "symbol": symbol,
                    "signal": signal_type,
                    "score": score,
                    "details": details,
                    "price": close
                }
            
            return None # Not interesting

        except Exception as e:
            self.logger.error(f"Scanner error for {symbol}: {e}")
            return None

    def scan_batch_smart(self, symbols, timeframe="4h"):
        """
        Fetches indicators for ALL symbols and asks AI to pick the best 3.
        """
        try:
            batch_data = []
            
            # 1. Fetch Data in Parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_symbol = {
                    executor.submit(self.data_provider.fetch_data, sym, timeframe): sym 
                    for sym in symbols
                }
                
                for future in concurrent.futures.as_completed(future_to_symbol):
                    sym = future_to_symbol[future]
                    try:
                        df, err = future.result()
                        if df is not None and not df.empty:
                            df = self.data_provider.calculate_indicators(df)
                            last = df.iloc[-1]
                            
                            # Compact summary for AI
                            batch_data.append(
                                f"{sym}: Price={last['Close']:.4f}, RSI={last['RSI']:.1f}, "
                                f"Trend={'Above' if last['Close'] > last['EMA_200'] else 'Below'} EMA200"
                            )
                    except Exception:
                        continue

            if not batch_data:
                return []

            # 2. AI Prompt
            prompt_text = "\n".join(batch_data)
            ai_prompt = f"""
You are a Forex Scanner. Analyze these pairs:
{prompt_text}

Task: Identify the TOP 3 pairs that have the most interesting technical setups (e.g. RSI extremes or Trend tests).
Return ONLY a valid JSON list of strings, e.g.: ["EURUSD", "GBPUSD", "XAUUSD"]
"""
            # 3. Call AI (using a fast model if possible)
            if self.ai_service:
                # Prefer a fast model for this batch op
                response = self.ai_service.analyze(ai_prompt, provider="Gemini", model="gemini-2.0-flash-exp")
                
                # Expecting a list from the AI, handling if it returns a dict
                if isinstance(response, list):
                    return response
                if isinstance(response, dict) and 'pairs' in response:
                    return response['pairs']
                
                # Fallback parsing if AI returns simple object
                self.logger.warning(f"Unexpected AI Scanner response format: {response}")
                return []

            return []

        except Exception as e:
            self.logger.error(f"Smart Scan Error: {e}")
            return []
