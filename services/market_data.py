import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import timedelta
from services.logger import Logger
from services.database import Database

class MarketDataProvider:
    def __init__(self):
        self.logger = Logger()
        self.db = Database()

    def fetch_data(self, symbol, interval, force_full=False):
        """
        Fetches OHLC data using yfinance with local database caching.
        Handles '4h' interval by fetching '1h' and resampling.
        
        Args:
            symbol (str): Ticker symbol.
            interval (str): Timeframe (e.g., '1h', '1d', '1wk').
            force_full (bool): If True, ignores local cache and fetches full history.
        """
        try:
            self.logger.info(f"Fetching data for {symbol} with interval {interval} (Force Full: {force_full})")
            
            # 1. Ticker Resolution
            if not symbol.endswith('=X') and len(symbol) == 6: 
                 ticker_symbol = f"{symbol}=X"
            else:
                ticker_symbol = symbol

            # 2. Determine Native Interval for Storage
            native_interval = interval
            resample_needed = False
            
            if interval == '4h':
                native_interval = '1h'
                resample_needed = True

            # 3. Check Local Database for Last Timestamp
            last_ts = None
            if not force_full:
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
                elif native_interval == '1wk':
                    fetch_period = "10y"
                else:
                    fetch_period = "2y"
                self.logger.info(f"No existing data (or forced refresh) for {symbol}. Fetching full history ({fetch_period})")

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
            
            # --- INSUFFICIENT DATA CHECK ---
            # If we have very few rows (e.g. < 200), indicators like EMA200 will be 0/NaN.
            # If we didn't just force a full fetch, try forcing one now.
            if (df is None or len(df) < 200) and not force_full:
                self.logger.warning(f"Insufficient data ({len(df) if df is not None else 0} rows) for {symbol}. Forcing full history fetch.")
                return self.fetch_data(symbol, interval, force_full=True)

            # --- DATA SANITY CHECK ---
            # Detect corruption (e.g. GBPUSD mixing with GBPJPY: 147.0 vs 1.35)
            if not df.empty and len(df) > 10:
                try:
                    # Check for massive instantaneous price drops/gaps (> 40% change in one step)
                    # This handles the 147 -> 1.35 crash which causes RSI=2
                    df['pct_change'] = df['Close'].pct_change().abs()
                    max_change = df['pct_change'].max()
                    
                    if max_change > 0.4: # 40% jump is impossible in Forex majors/minors
                        self.logger.warning(f"CORRUPTION DETECTED in {symbol}: Max change {max_change*100:.0f}%. PURGING DATA.")
                        self.db.clear_data(symbol, native_interval)
                        
                        # Recursive retry with full fetch
                        if not force_full:
                            return self.fetch_data(symbol, interval, force_full=True)
                        
                except Exception as e:
                    self.logger.error(f"Sanity check error: {e}")

            if df.empty:
                return None, "No data available."

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

    def calculate_volume_profile(self, df, timeframe='1d'):
        """
        Calculates Volume Profile (VPVR) to find Point of Control (POC), 
        Value Area High (VAH), and Value Area Low (VAL).
        Uses Year-To-Date (YTD) for '1d', otherwise 100 candle lookback.
        """
        try:
            if df is None or len(df) < 50:
                return "Not enough data for VPVR.", {}

            # Use YTD if 1d timeframe, else last 100 candles
            if timeframe == '1d':
                current_year = df.index[-1].year
                data = df[df.index.year == current_year].copy()
                if len(data) < 20: # If it's early Jan, fall back to last 100
                     data = df.iloc[-100:].copy()
            else:
                data = df.iloc[-100:].copy()
            
            # Create a histogram of volume at price levels
            # We use 50 bins/levels
            price_min = data['Low'].min()
            price_max = data['High'].max()
            
            # Avoid division by zero
            if price_max == price_min:
                return "Flat Market (No VPVR)", {}

            # Create bins
            bins = np.linspace(price_min, price_max, 50)
            
            # Simple Volume Profile: Aggregate volume into buckets
            # We can't use histogram directly with weights efficiently in one line without numpy
            # So we iterate or use numpy.histogram
            
            # Calculate volume per bin
            vol_profile, bin_edges = np.histogram(data['Close'], bins=bins, weights=data['Volume'])
            
            # Find POC (Bin with max volume)
            max_vol_idx = vol_profile.argmax()
            poc_price = (bin_edges[max_vol_idx] + bin_edges[max_vol_idx+1]) / 2
            
            # Calculate Value Area (70% of volume)
            total_vol = vol_profile.sum()
            target_vol = total_vol * 0.70
            
            # Start from POC and expand outwards
            current_vol = vol_profile[max_vol_idx]
            low_idx = max_vol_idx
            high_idx = max_vol_idx
            
            while current_vol < target_vol:
                # Try expanding down
                lower_vol = 0
                if low_idx > 0:
                    lower_vol = vol_profile[low_idx - 1]
                
                # Try expanding up
                upper_vol = 0
                if high_idx < len(vol_profile) - 1:
                    upper_vol = vol_profile[high_idx + 1]
                
                # Compare and expand
                if lower_vol > upper_vol:
                    current_vol += lower_vol
                    low_idx -= 1
                elif upper_vol > lower_vol:
                    current_vol += upper_vol
                    high_idx += 1
                else: 
                    # Equal or both zero/boundaries
                    if low_idx > 0:
                        current_vol += lower_vol
                        low_idx -= 1
                    elif high_idx < len(vol_profile) - 1:
                        current_vol += upper_vol
                        high_idx += 1
                    else:
                        break # Cannot expand further
            
            val_price = bin_edges[low_idx]
            vah_price = bin_edges[high_idx + 1]
            
            current_price = df.iloc[-1]['Close']
            
            # Interpret
            status = "INSIDE VALUE AREA (Rotation Likely)"
            if current_price > vah_price:
                status = "ABOVE VALUE AREA (Bullish Breakout)"
            elif current_price < val_price:
                status = "BELOW VALUE AREA (Bearish Breakdown)"

            text = (
                f"VOLUME PROFILE (VPVR):\n"
                f"- POC: {poc_price:.5f}\n"
                f"- VAH: {vah_price:.5f}\n"
                f"- VAL: {val_price:.5f}\n"
                f"- Status: {status}\n"
            )
            
            levels = {
                "POC": poc_price,
                "VAH": vah_price,
                "VAL": val_price,
                "Status": status
            }
            
            return text, levels

        except Exception as e:
            self.logger.error(f"VPVR Calculation Error: {e}")
            return "VPVR Error", {}

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
            
            # --- NEW: Z-SCORE ANALYSIS (Statistical Divergence) ---
            # Calculate the spread between the two assets (Normalized)
            # We normalize them first to compare apples to apples
            
            # Z-Score of the SPREAD (Asset A - Asset B)
            # If Z-Score is extreme (>2), it means the relationship is stretched and due for mean reversion.
            
            # Normalize prices to percentage change from start of window
            window = 50
            subset = aligned.iloc[-window:].copy()
            
            # Normalize to 0-1 or pct change range for comparison
            subset['Main_Norm'] = (subset['Main'] - subset['Main'].mean()) / subset['Main'].std()
            subset['Comp_Norm'] = (subset['Comp'] - subset['Comp'].mean()) / subset['Comp'].std()
            
            subset['Spread'] = subset['Main_Norm'] - subset['Comp_Norm']
            
            spread_mean = subset['Spread'].mean() # Should be close to 0
            spread_std = subset['Spread'].std()
            
            current_spread = subset['Spread'].iloc[-1]
            z_score = (current_spread - spread_mean) / spread_std if spread_std != 0 else 0
            
            status = "NORMAL"
            
            # Interpretation
            if abs(z_score) > 2.0:
                 status = f"⚠️ EXTREME DIVERGENCE (Z: {z_score:.2f}) - Mean Reversion Likely"
            elif abs(z_score) > 1.5:
                 status = f"WATCH (Z: {z_score:.2f}) - Stretched"
            
            text = (
                f"INTER-MARKET CORRELATION ({comp_name}):\n"
                f"- Correlation Coeff (50): {current_corr:.2f}\n"
                f"- 50-Day Z-Score Divergence: {z_score:.2f}\n"
                f"- Status: {status}\n"
            )
            
            return text, current_corr

        except Exception as e:
            self.logger.error(f"Correlation Error: {e}")
            return f"Correlation Analysis Failed: {e}", 0
