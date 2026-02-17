import pandas as pd
from services.logger import Logger

class ScannerService:
    def __init__(self, data_provider):
        self.logger = Logger()
        self.data_provider = data_provider

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
