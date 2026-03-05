import yfinance as yf
import pandas as pd
from services.logger import Logger

class CSMService:
    def __init__(self):
        self.logger = Logger()
        # Basket of 28 major pairs to calculate individual currency strength
        self.currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
        
        self.pairs = [
            # EUR Crosses
            "EURUSD", "EURGBP", "EURJPY", "EURAUD", "EURNZD", "EURCAD", "EURCHF",
            # GBP Crosses
            "GBPUSD", "GBPJPY", "GBPAUD", "GBPNZD", "GBPCAD", "GBPCHF",
            # USD Crosses (Remaining)
            "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
            # JPY Crosses (Remaining)
            "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
            # AUD Crosses (Remaining)
            "AUDNZD", "AUDCAD", "AUDCHF",
            # NZD & CAD Crosses (Remaining)
            "NZDCAD", "NZDCHF", "CADCHF"
        ]

    def get_currency_strength(self, timeframe='1d'):
        """
        Calculates a strength matrix for the 8 major currencies.
        Uses Rate of Change (ROC) and distance from SMA(50) to rank them.
        Returns a sorted dictionary and formatted string.
        """
        try:
            self.logger.info("Calculating Currency Strength Matrix (CSM)...")
            
            # We will use yfinance to fetch a fast 'history' for all symbols
            # Prepare tickers
            tickers = [f"{p}=X" for p in self.pairs]
            
            # Fetch last 50 periods
            data = yf.download(tickers, period="3mo", interval=timeframe, group_by="ticker", progress=False, auto_adjust=False)
            
            # Dictionary to accumulate strength scores
            scores = {c: 0.0 for c in self.currencies}
            
            for pair in self.pairs:
                ticker = f"{pair}=X"
                if ticker not in data.columns.levels[0]:
                    continue
                    
                df = data[ticker].dropna()
                if len(df) < 20: continue
                
                # Calculate Strength of the PAIR
                # Simple metric: % distance from 20-period moving average
                close = df['Close']
                sma20 = close.rolling(window=20).mean()
                
                last_price = close.iloc[-1]
                last_sma = sma20.iloc[-1]
                
                # If price > SMA, base currency is stronger. If price < SMA, quote is stronger.
                pct_diff = ((last_price - last_sma) / last_sma) * 100
                
                base = pair[:3]
                quote = pair[3:]
                
                # Add score to Base, subtract from Quote
                if base in scores: scores[base] += pct_diff
                if quote in scores: scores[quote] -= pct_diff

            # Normalize scores (Rank them)
            # Sort by score descending
            sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            
            if not sorted_scores:
                return "CSM Unavailable (Data Error)", {}

            strongest = sorted_scores[:2]
            weakest = sorted_scores[-2:]
            
            text = "CURRENCY STRENGTH MATRIX (CSM):\n"
            text += f"- STRONGEST: {strongest[0][0]} (+{strongest[0][1]:.2f}), {strongest[1][0]} (+{strongest[1][1]:.2f})\n"
            text += f"- WEAKEST: {weakest[1][0]} ({weakest[1][1]:.2f}), {weakest[0][0]} ({weakest[0][1]:.2f})\n"
            text += "\nFull Rankings:\n"
            for c, s in sorted_scores:
                text += f"[{c}: {s:.2f}] "

            return text, dict(sorted_scores)

        except Exception as e:
            self.logger.error(f"Error calculating CSM: {e}")
            return f"CSM Calculation Failed: {e}", {}
