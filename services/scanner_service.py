import pandas as pd
from services.logger import Logger

class ScannerService:
    def __init__(self, data_provider):
        self.logger = Logger()
        self.data_provider = data_provider

    def scan_symbol(self, symbol, timeframe):
        """Analyzes a single symbol for technical setups."""
        try:
            # Fetch and calculate
            df, error = self.data_provider.fetch_data(symbol, timeframe)
            if error or df is None or df.empty:
                return None
            
            df = self.data_provider.calculate_indicators(df)
            latest = df.iloc[-1]
            
            # Logic: Determine Setup
            trend = "BULLISH" if latest['Close'] > latest['EMA_200'] else "BEARISH"
            rsi = latest['RSI']
            
            signal = "NEUTRAL"
            color = "gray"

            # Simple Heuristics for "Interesting" setups
            if rsi > 70:
                signal = "OVERBOUGHT"
                color = "#ff4444" # Red
            elif rsi < 30:
                signal = "OVERSOLD"
                color = "#00c851" # Green
            
            # Check for EMA 200 touch (within 0.1% range)
            ema_dist = abs(latest['Close'] - latest['EMA_200']) / latest['EMA_200']
            if ema_dist < 0.002:
                signal = "EMA 200 TEST"
                color = "#ffbb33" # Amber

            return {
                "symbol": symbol,
                "price": f"{latest['Close']:.5f}",
                "trend": trend,
                "rsi": f"{rsi:.1f}",
                "signal": signal,
                "color": color
            }
        except Exception as e:
            self.logger.error(f"Scanner error for {symbol}: {e}")
            return None
