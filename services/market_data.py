import yfinance as yf
import pandas as pd
import pandas_ta as ta
from services.logger import Logger

class MarketDataProvider:
    def __init__(self):
        self.logger = Logger()

    def fetch_data(self, symbol, interval):
        """
        Fetches OHLC data using yfinance.
        """
        try:
            self.logger.info(f"Fetching data for {symbol} with interval {interval}")
            # yfinance tickers for forex often have '=X' suffix, e.g., 'EURUSD=X'
            # Also support Crypto if needed, but assuming Forex for now based on context
            if not symbol.endswith('=X') and len(symbol) == 6: 
                 ticker_symbol = f"{symbol}=X"
            else:
                ticker_symbol = symbol

            ticker = yf.Ticker(ticker_symbol)
            
            # Map user timeframe to reasonable fetch limit to ensure enough data for EMA 200
            # 200 candles needed + buffer
            if interval == '1h':
                 fetch_period = "1mo" # 1mo ~ 720h (trading 24/5? approx 500 candles) - plenty
            elif interval == '4h':
                 fetch_period = "6mo" # 1mo is ~ 120 candles (too short for 200 EMA). 6mo is safer.
            elif interval == '1d':
                 fetch_period = "2y"  # 1y is ~ 260 candles. 2y is safer.
            else:
                 fetch_period = "1y"

            df = ticker.history(period=fetch_period, interval=interval)
            
            if df.empty:
                self.logger.warning(f"No data found for symbol: {symbol}")
                return None, "No data found for symbol."
            
            self.logger.debug(f"Fetched {len(df)} rows for {symbol}")
            return df, None
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None, str(e)

    def calculate_indicators(self, df):
        """
        Calculates EMA 50, EMA 200, RSI 14, and ATR 14.
        """
        try:
            self.logger.info("Calculating using pandas_ta")
             # Ensure we have enough data
            if len(df) < 200:
                self.logger.warning(f"Not enough data for 200 EMA. Got {len(df)} rows.")
                print(f"Warning: Not enough data for 200 EMA. Got {len(df)} rows.")

            # Calculate indicators using pandas_ta
            # We copy to avoid SettingWithCopy warning if it's a slice
            df = df.copy()
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            
            self.logger.debug("Indicators calculated successfully")
            return df
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            print(f"Error calculating indicators: {e}")
            return df

