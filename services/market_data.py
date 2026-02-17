import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import timedelta
from services.logger import Logger
from services.database import Database

class MarketDataProvider:
    def __init__(self):
        self.logger = Logger()
        self.db = Database()

    def fetch_data(self, symbol, interval):
        """
        Fetches OHLC data using yfinance with local database caching.
        Handles '4h' interval by fetching '1h' and resampling.
        """
        try:
            self.logger.info(f"Fetching data for {symbol} with interval {interval}")
            
            # 1. Ticker Resolution
            if not symbol.endswith('=X') and len(symbol) == 6: 
                 ticker_symbol = f"{symbol}=X"
            else:
                ticker_symbol = symbol

            # 2. Determine Native Interval for Storage
            # We store '1h' for '4h' requests to keep DB granular.
            # We store '1d' for '1d' requests.
            native_interval = interval
            resample_needed = False
            
            if interval == '4h':
                native_interval = '1h'
                resample_needed = True

            # 3. Check Local Database for Last Timestamp
            last_ts = self.db.get_last_timestamp(symbol, native_interval)
            
            # 4. Determine Fetch Strategy
            start_date = None
            fetch_period = None
            
            if last_ts:
                # Fetch from the last timestamp to ensure we update the latest candle
                # Adding a small buffer isn't strictly necessary as 'start' is inclusive, 
                # but we rely on INSERT OR REPLACE to handle overlaps.
                start_date = last_ts
                self.logger.info(f"Found existing data for {symbol}. Fetching new data from {start_date}")
            else:
                # No data: set default lookback
                if native_interval == '1h':
                    fetch_period = "2y" 
                elif native_interval == '1d':
                    fetch_period = "5y"
                else:
                    fetch_period = "1y"
                self.logger.info(f"No existing data for {symbol}. Fetching full history ({fetch_period})")

            # 5. Fetch Data from Yahoo Finance
            try:
                new_df = pd.DataFrame()
                if start_date:
                    # Fetch update
                    # Note: yf.download with 'start' expects a date or datetime string/object
                    new_df = yf.download(
                        tickers=ticker_symbol, 
                        start=start_date, 
                        interval=native_interval, 
                        progress=False,
                        auto_adjust=False,
                        multi_level_index=False # Try to force simple index if supported by version
                    )
                else:
                    # Fetch full history
                    new_df = yf.download(
                        tickers=ticker_symbol, 
                        period=fetch_period, 
                        interval=native_interval, 
                        progress=False,
                        auto_adjust=False,
                        multi_level_index=False
                    )
                
                # Handle MultiIndex manually if the parameter didn't work (common in some versions)
                if isinstance(new_df.columns, pd.MultiIndex):
                    new_df.columns = new_df.columns.get_level_values(0)
                
                # Validate data before saving
                if not new_df.empty:
                    self.db.save_data(new_df, symbol, native_interval)
                else:
                    self.logger.warning("No new data fetched from provider (market might be closed).")

            except Exception as e:
                self.logger.error(f"Error fetching from provider: {e}. Attempting to use cached data only.")

            # 6. Load Complete Dataset from Database
            df = self.db.load_data(symbol, native_interval)
            
            if df.empty:
                return None, "No data available (neither local nor remote)."

            # 7. Resample if needed (e.g., 1h -> 4h)
            if resample_needed:
                self.logger.info(f"Resampling {native_interval} data to {interval}")
                agg_dict = {
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last'
                }
                # Check lowercase/uppercase volume
                vol_col = 'Volume' if 'Volume' in df.columns else 'volume'
                if vol_col in df.columns:
                    agg_dict[vol_col] = 'sum'

                # '4h' resampling
                # Use closed='left', label='left' or similar if needed, but standard resample is usually fine for forex
                df = df.resample('4h').agg(agg_dict).dropna()

            self.logger.debug(f"Total rows available for {symbol}: {len(df)}")
            return df, None

        except Exception as e:
            self.logger.error(f"Error in fetch_data pipeline: {str(e)}")
            return None, str(e)

    def calculate_indicators(self, df):
        """
        Calculates EMA 50, EMA 200, RSI 14, and ATR 14.
        """
        try:
            self.logger.info("Calculating technical indicators using pandas_ta")
            
            # Ensure column names are standard Capitalized for pandas_ta
            # Database might return lowercase if we aren't careful, but load_data handles capitalization.
            
            if len(df) < 50:
                self.logger.warning(f"Not enough data for indicators. Got {len(df)} rows.")

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
