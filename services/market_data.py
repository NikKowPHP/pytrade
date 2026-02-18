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
                    new_df = yf.download(
                        tickers=ticker_symbol, 
                        start=start_date, 
                        interval=native_interval, 
                        progress=False,
                        auto_adjust=False
                    )
                else:
                    # Fetch full history
                    new_df = yf.download(
                        tickers=ticker_symbol, 
                        period=fetch_period, 
                        interval=native_interval, 
                        progress=False,
                        auto_adjust=False
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
            
            # Safely extract and format values
            close = latest.get('Close', 0)
            rsi = latest.get('RSI')
            atr = latest.get('ATR')
            ema200 = latest.get('EMA_200')
            
            rsi_str = f"{rsi:.2f}" if rsi is not None and not pd.isna(rsi) else "N/A"
            atr_str = f"{atr:.5f}" if atr is not None and not pd.isna(atr) else "N/A"
            ema_str = f"{ema200:.5f}" if ema200 is not None and not pd.isna(ema200) else "N/A"

            self.logger.info(
                f"LATEST TECHNICALS -> "
                f"Close: {close:.5f} | "
                f"RSI: {rsi_str} | "
                f"ATR: {atr_str} | "
                f"EMA200: {ema_str}"
            )
            
            return df
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return df

    def calculate_pivots(self, df):
        """
        Calculates Standard Pivot Points, Supports, and Resistances based on the last complete candle.
        """
        try:
            if df is None or df.empty:
                return {}

            # Use the second to last row (completed candle) for accurate pivot calculation
            # If we use the current live candle, the pivots will keep shifting.
            last_complete = df.iloc[-2] 

            high = last_complete['High']
            low = last_complete['Low']
            close = last_complete['Close']

            # Standard Pivot Points
            pp = (high + low + close) / 3
            r1 = (2 * pp) - low
            s1 = (2 * pp) - high
            r2 = pp + (high - low)
            s2 = pp - (high - low)
            r3 = high + 2 * (pp - low)
            s3 = low - 2 * (high - pp)

            return {
                "pivot": pp,
                "r1": r1, "s1": s1,
                "r2": r2, "s2": s2,
                "r3": r3, "s3": s3
            }
        except Exception as e:
            self.logger.error(f"Error calculating pivots: {e}")
            return {}
    def calculate_smart_money(self, df):
        """
        Detects Institutional Footprints: Fair Value Gaps (FVG) and Order Blocks (OB).
        Returns a text summary and a list of levels for the AI.
        """
        try:
            if df is None or len(df) < 5:
                return "Not enough data for SMC.", []

            smc_text = "INSTITUTIONAL LEVELS (Smart Money):\n"
            levels = []
            
            # 1. Fair Value Gaps (FVG)
            # Look at the last 50 candles to find active gaps
            # Bullish FVG: High[i-1] < Low[i+1] (Gap in the middle of a big green candle)
            # Bearish FVG: Low[i-1] > High[i+1] (Gap in the middle of a big red candle)
            
            lookback = 50
            subset = df.iloc[-lookback:].reset_index()
            
            # Iterate (skip last candle as it's forming, start from 3rd candle)
            for i in range(len(subset) - 2, 1, -1):
                curr = subset.iloc[i]
                prev = subset.iloc[i-1]
                next_c = subset.iloc[i+1]
                
                # Check Bullish FVG
                if curr['Close'] > curr['Open']: # Green Candle
                    if next_c['Low'] > prev['High']:
                        gap_size = next_c['Low'] - prev['High']
                        # Filter small gaps (must be significant)
                        if gap_size > (curr['Close'] * 0.0005): 
                            # Check if price has since filled it (Mitigation test)
                            # Simple check: has recent price crossed this level?
                            latest_close = df.iloc[-1]['Close']
                            
                            # If price is currently below the bullish FVG, it's resistance or invalid
                            # If price is above, it's support (magnet)
                            if latest_close > next_c['Low']:
                                smc_text += f"- BULLISH FVG detected at {prev['High']:.4f} - {next_c['Low']:.4f} (Support Magnet)\n"
                                levels.append(f"Bullish FVG Zone: {prev['High']:.5f}")
                
                # Check Bearish FVG
                elif curr['Close'] < curr['Open']: # Red Candle
                    if next_c['High'] < prev['Low']:
                        gap_size = prev['Low'] - next_c['High']
                        if gap_size > (curr['Close'] * 0.0005):
                            latest_close = df.iloc[-1]['Close']
                            if latest_close < next_c['High']:
                                smc_text += f"- BEARISH FVG detected at {next_c['High']:.4f} - {prev['Low']:.4f} (Resistance Magnet)\n"
                                levels.append(f"Bearish FVG Zone: {prev['Low']:.5f}")

            # 2. Order Blocks (Simplified)
            # Detect the last opposing candle before a significant move (ATR * 3)
            # This is a heuristic approximation.
            last_30 = df.iloc[-30:]
            highest = last_30['High'].max()
            lowest = last_30['Low'].min()
            current_price = df.iloc[-1]['Close']
            
            # If we are near lows, look for Bullish OB (Last Red Candle)
            if (current_price - lowest) < (highest - lowest) * 0.3:
                smc_text += f"- Watching for Bullish Order Block near {lowest:.4f} (Swing Low)\n"
            
            # If we are near highs, look for Bearish OB (Last Green Candle)
            elif (highest - current_price) < (highest - lowest) * 0.3:
                smc_text += f"- Watching for Bearish Order Block near {highest:.4f} (Swing High)\n"

            if not levels:
                smc_text += "No significant recent FVGs found.\n"

            return smc_text, levels

        except Exception as e:
            self.logger.error(f"SMC Calculation Error: {e}")
            return "SMC Error", []

    def get_correlation_data(self, main_df, symbol, interval):
        """
        Fetches a related 'Truth Asset' and calculates correlation.
        Returns: text_summary, raw_score
        """
        try:
            if main_df is None or main_df.empty:
                return "No Data", 0

            # 1. Determine Comparison Asset
            comp_symbol = "DX-Y.NYB" # Default: Dollar Index
            comp_name = "DXY (Dollar Index)"
            
            # Logic map
            if "USD" in symbol:
                pass # Keep DXY
            elif "JPY" in symbol:
                comp_symbol = "^TNX" # 10Y Yields drive JPY
                comp_name = "US 10Y Yields"
            elif "XAU" in symbol or "GOLD" in symbol:
                comp_symbol = "SI=F"
                comp_name = "Silver"
            elif "BTC" in symbol:
                comp_symbol = "^IXIC" # Nasdaq
                comp_name = "Nasdaq"

            # 2. Fetch Comparison Data
            # Must match the main timeframe/interval
            comp_df = yf.download(
                comp_symbol, 
                period="1y", # ample buffer
                interval=interval, 
                progress=False,
                auto_adjust=False
            )
            
            if comp_df.empty:
                return f"Correlation Data Unavailable for {comp_name}", 0

            # 3. Align Data (Merge on Index)
            # Use 'Close' prices
            main_close = main_df['Close']
            
            # Handle MultiIndex if present in comp_df
            if isinstance(comp_df.columns, pd.MultiIndex):
                comp_close = comp_df['Close'][comp_symbol]
            else:
                comp_close = comp_df['Close']

            # Aligns timestamps automatically
            aligned = pd.concat([main_close, comp_close], axis=1, join='inner')
            aligned.columns = ['Main', 'Comp']
            
            if len(aligned) < 50:
                 return "Not enough aligned data", 0

            # 4. Calculate Rolling Correlation (50 periods)
            rolling_corr = aligned['Main'].rolling(window=50).corr(aligned['Comp'])
            current_corr = rolling_corr.iloc[-1]
            
            # 5. Calculate recent performance (Last 5 candles) to detect divergence
            # e.g. If Corr is -0.9 (Inverse), but both moved UP, that's a divergence.
            main_move = (aligned['Main'].iloc[-1] - aligned['Main'].iloc[-5]) / aligned['Main'].iloc[-5]
            comp_move = (aligned['Comp'].iloc[-1] - aligned['Comp'].iloc[-5]) / aligned['Comp'].iloc[-5]

            status = "NORMAL"
            if abs(current_corr) > 0.8:
                # High Correlation exists
                if current_corr < 0: # Inverse relationship (e.g. EURUSD vs DXY)
                    # If they moved in SAME direction, it's a fakeout
                    if (main_move > 0 and comp_move > 0) or (main_move < 0 and comp_move < 0):
                        status = "⚠️ DIVERGENCE (FAKE-OUT RISK)"
                else: # Direct relationship (e.g. AUDUSD vs NZDUSD)
                    # If they moved in OPPOSITE direction
                    if (main_move > 0 and comp_move < 0) or (main_move < 0 and comp_move > 0):
                         status = "⚠️ DIVERGENCE (NON-CONFIRMED)"

            text = (
                f"INTER-MARKET CORRELATION ({comp_name}):\n"
                f"- Correlation Coeff (50): {current_corr:.2f}\n"
                f"- Status: {status}\n"
                f"- {symbol} 5-bar Move: {main_move*100:.2f}%\n"
                f"- {comp_name} 5-bar Move: {comp_move*100:.2f}%\n"
            )
            
            return text, current_corr

        except Exception as e:
            self.logger.error(f"Correlation Error: {e}")
            return f"Correlation Analysis Failed: {e}", 0
