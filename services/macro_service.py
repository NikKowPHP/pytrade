import yfinance as yf
import pandas as pd
from services.logger import Logger

class MacroService:
    def __init__(self):
        self.logger = Logger()
        # Tickers: S&P500, VIX, 10Y Yield, Dollar Index, Gold
        self.tickers = {
            "SPX": "^GSPC",
            "VIX": "^VIX",
            "US10Y": "^TNX", 
            "DXY": "DX-Y.NYB",
            "GOLD": "GC=F"
        }

    def fetch_macro_context(self):
        """
        Fetches % change of macro assets to determine regime.
        Also calculates S&P 500 (SPX) 20-day SMA for Risk ON/OFF filter.
        Returns a text summary and a raw dictionary (stats).
        """
        try:
            self.logger.info("Fetching Global Macro Data...")
            data_text = "GLOBAL MACRO CONTEXT (24h Change):\n"
            stats = {}
            
            # 1. Fetch SPX History for SMA Calculation (Risk Regime)
            # We need at least 20 days. Fetching '1mo' is safer.
            spx_ticker = self.tickers["SPX"]
            spx_history = yf.Ticker(spx_ticker).history(period="1mo")
            
            risk_regime = "NEUTRAL"
            spx_price = 0
            spx_sma20 = 0

            if not spx_history.empty and len(spx_history) >= 20:
                spx_sma20 = spx_history['Close'].rolling(window=20).mean().iloc[-1]
                spx_price = spx_history['Close'].iloc[-1]
                
                # Determine Regime
                if spx_price > spx_sma20:
                    risk_regime = "RISK ON (Bullish Equities)"
                else:
                    risk_regime = "RISK OFF (Bearish Equities)"
                
                stats['spx_price'] = spx_price
                stats['spx_sma20'] = spx_sma20
                stats['risk_regime'] = risk_regime

                data_text += f"\n--- RISK REGIME FILTER ---\n"
                data_text += f"Market State: {risk_regime}\n"
                data_text += f"SPX Price: {spx_price:.2f} | 20 SMA: {spx_sma20:.2f}\n"
                data_text += "--------------------------\n"

            # 2. Fetch Daily Context for Dashboard (Last 5 days)
            # Download all at once for speed
            tickers_list = list(self.tickers.values())
            df = yf.download(tickers_list, period="5d", progress=False)['Close']
            
            if df.empty:
                return "Macro Data Unavailable", {}

            # Calculate % Change from previous close
            # We use the last two valid trading days
            if len(df) >= 2:
                current = df.iloc[-1]
                prev = df.iloc[-2]
                
                # Map back to readable names
                # yfinance multi-index columns handling
                for name, ticker in self.tickers.items():
                    try:
                        # Handle different df structures depending on yf version
                        c_price = current.get(ticker)
                        p_price = prev.get(ticker)
                        
                        # Fallback for simple index if MultiIndex fails
                        if c_price is None and ticker in df.columns:
                            c_price = df[ticker].iloc[-1]
                            p_price = df[ticker].iloc[-2]

                        if c_price is not None and p_price is not None:
                            pct = ((c_price - p_price) / p_price) * 100
                            stats[name] = pct
                            symbol = "🟢" if pct > 0 else "🔴"
                            if name == "VIX": symbol = "🔴" if pct > 0 else "🟢" # Inverted for VIX
                            data_text += f"- {name}: {pct:+.2f}% {symbol}\n"
                    except Exception as e:
                        self.logger.error(f"Error processing {name}: {e}")

            return data_text, stats

        except Exception as e:
            self.logger.error(f"Macro fetch error: {e}")
            return "Macro Data Unavailable", {}
