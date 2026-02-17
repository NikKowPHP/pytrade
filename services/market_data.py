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
        Handles '4h' interval by fetching '1h' and resampling.
        """
        try:
            self.logger.info(f"Fetching data for {symbol} with interval {interval}")
            
            # 1. Ticker Resolution
            if not symbol.endswith('=X') and len(symbol) == 6: 
                 ticker_symbol = f"{symbol}=X"
            else:
                ticker_symbol = symbol

            # 2. Interval & Period Resolution
            # Yahoo Finance valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            # It DOES NOT support '4h'. We must resample.
            request_interval = interval
            resample_needed = False
            
            if interval == '4h':
                request_interval = '1h'
                resample_needed = True
                # We need enough 1h candles to form 200+ 4h candles. 
                # 200 * 4 = 800 hours. 1y is safe (approx 6000 trading hours).
                fetch_period = "1y" 
            elif interval == '1h':
                 fetch_period = "1y" 
            elif interval == '1d':
                 fetch_period = "5y"
            else:
                 fetch_period = "1y"

            # 3. Fetch Data using download (more robust)
            # auto_adjust=False ensures we get raw OHLC (sometimes adjusted close messes up tech analysis)
            df = yf.download(
                tickers=ticker_symbol, 
                period=fetch_period, 
                interval=request_interval, 
                progress=False,
                auto_adjust=False 
            )
            
            if df.empty:
                self.logger.warning(f"No data found for symbol: {symbol}")
                return None, "No data found for symbol."
            
            # 4. Handle MultiIndex Columns (Newer yfinance versions return (Price, Ticker))
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten: If columns are ('Close', 'EURUSD=X'), keep 'Close'
                df.columns = df.columns.get_level_values(0)

            # 5. Resample if needed (e.g., 1h -> 4h)
            if resample_needed:
                self.logger.info(f"Resampling {request_interval} data to {interval}")
                # Define aggregation rules
                agg_dict = {
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last'
                }
                if 'Volume' in df.columns:
                    agg_dict['Volume'] = 'sum'

                # Perform resampling
                df = df.resample('4h').agg(agg_dict).dropna()

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
            self.logger.info("Calculating technical indicators using pandas_ta")
            
            if len(df) < 200:
                self.logger.warning(f"Not enough data for 200 EMA. Got {len(df)} rows.")

            # Calculate indicators
            df = df.copy()
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            
            # LOGGING THE LATEST DATA FOR DEBUGGING
            latest = df.iloc[-1]
            self.logger.info(
                f"LATEST TECHNICALS -> "
                f"Close: {latest['Close']:.5f} | "
                f"RSI: {latest['RSI']:.2f} | "
                f"ATR: {latest['ATR']:.5f} | "
                f"EMA200: {latest['EMA_200']:.5f}"
            )
            
            return df
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return df


