
import pandas as pd
from services.logger import Logger

class StructureService:
    def __init__(self):
        self.logger = Logger()

    def detect_structure(self, df):
        """
        Detects Market Structure: Swings, Break of Structure (BOS), 
        Change of Character (ChoCH).
        """
        try:
            if df is None or len(df) < 20:
                return "Insufficient Data for Structure", {}

            # 1. Identify Swing Highs and Lows
            # Strict definition: High > 2 prev highs AND High > 2 next highs
            # We need a window.
            df = df.copy()
            df['Swing_High'] = df['High'].rolling(window=5, center=True).apply(lambda x: 1 if x[2] == max(x) else 0, raw=True)
            df['Swing_Low'] = df['Low'].rolling(window=5, center=True).apply(lambda x: 1 if x[2] == min(x) else 0, raw=True)
            
            # Extract distinct swing points
            swings = []
            
            # Iterate through the last 50 candles to find swings
            subset = df.iloc[-50:]
            for i, row in subset.iterrows():
                if row['Swing_High'] == 1:
                    swings.append({'type': 'HIGH', 'price': row['High'], 'index': i})
                if row['Swing_Low'] == 1:
                    swings.append({'type': 'LOW', 'price': row['Low'], 'index': i})
            
            if len(swings) < 4:
                return "Market Choppy / No Clear Structure", {}

            # 2. Determine Trend (HH/HL vs LH/LL)
            last_high = next((s for s in reversed(swings) if s['type'] == 'HIGH'), None)
            prev_high = next((s for s in reversed(swings) if s['type'] == 'HIGH' and s['index'] < last_high['index']), None)
            
            last_low = next((s for s in reversed(swings) if s['type'] == 'LOW'), None)
            prev_low = next((s for s in reversed(swings) if s['type'] == 'LOW' and s['index'] < last_low['index']), None)

            trend = "NEUTRAL"
            structure_note = ""

            if last_high and prev_high and last_low and prev_low:
                # Uptrend Check
                if last_high['price'] > prev_high['price'] and last_low['price'] > prev_low['price']:
                    trend = "BULLISH (HH + HL)"
                    structure_note = "Expect continued upside unless Swing Low is broken."
                
                # Downtrend Check
                elif last_high['price'] < prev_high['price'] and last_low['price'] < prev_low['price']:
                    trend = "BEARISH (LL + LH)"
                    structure_note = "Expect continued downside unless Swing High is broken."
                
                # ChoCH / Reversal Check
                # Uptrend Broken?
                elif last_high['price'] < prev_high['price'] and last_low['price'] > prev_low['price']:
                    trend = "POSSIBLE REVERSAL (LH detected in Uptrend)"
                    structure_note = "Watch for Lower Low to confirm Bearish ChoCH."
                 
                elif last_high['price'] > prev_high['price'] and last_low['price'] < prev_low['price']:
                    trend = "POSSIBLE REVERSAL (LL detected in Bullish context)" # Expanding?
                    structure_note = "Volatile / Expanding structure."

            current_price = df.iloc[-1]['Close']
            
            # Check for immediate Break of Structure (Live)
            bos_status = "Holding"
            if trend.startswith("BULLISH"):
                if current_price < last_low['price']:
                    bos_status = "⚠️ BEARISH CHOCH (Structure Broken Down)"
            elif trend.startswith("BEARISH"):
                if current_price > last_high['price']:
                    bos_status = "⚠️ BULLISH CHOCH (Structure Broken Up)"

            text = (
                f"MARKET STRUCTURE:\n"
                f"- Trend: {trend}\n"
                f"- Last Swing High: {last_high['price']:.5f} (Time: {last_high['index']})\n"
                f"- Last Swing Low: {last_low['price']:.5f} (Time: {last_low['index']})\n"
                f"- Status: {bos_status}\n"
                f"- Note: {structure_note}"
            )
            
            return text, {"trend": trend, "last_high": last_high['price'], "last_low": last_low['price']}

        except Exception as e:
            self.logger.error(f"Structure Analysis Error: {e}")
            return "Structure Analysis Failed", {}

    def analyze_multi_timeframe(self, daily_text, hourly_text):
        """
        Correlates Daily and Hourly structure to find setups.
        """
        try:
            daily_trend = "NEUTRAL"
            if "BULLISH" in daily_text: daily_trend = "BULLISH"
            if "BEARISH" in daily_text: daily_trend = "BEARISH"
            
            hourly_trend = "NEUTRAL"
            if "BULLISH" in hourly_text: hourly_trend = "BULLISH"
            if "BEARISH" in hourly_text: hourly_trend = "BEARISH"
            
            status = "ALIGNMENT UNKNOWN"
            
            if daily_trend == "BULLISH":
                if hourly_trend == "BULLISH":
                    status = "✅ FULL ALIGNMENT (Strong Buy)"
                elif hourly_trend == "BEARISH":
                    status = "⚠️ PULLBACK (Daily Up, Hourly Down)"
            
            elif daily_trend == "BEARISH":
                if hourly_trend == "BEARISH":
                    status = "✅ FULL ALIGNMENT (Strong Sell)"
                elif hourly_trend == "BULLISH":
                    status = "⚠️ PULLBACK (Daily Down, Hourly Up)"
                    
            return f"MTF STRUCTURE ALIGNMENT:\n{status}"

        except Exception as e:
            return f"MTF Error: {e}"
