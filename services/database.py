import sqlite3
import pandas as pd
from services.logger import Logger
import os

class Database:
    def __init__(self, db_name="market_data.db"):
        self.logger = Logger()
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            # Create table with composite primary key to prevent duplicates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol TEXT,
                    interval TEXT,
                    timestamp DATETIME,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (symbol, interval, timestamp)
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")

    def get_last_timestamp(self, symbol, interval):
        """Returns the latest timestamp stored for a given symbol and interval."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(timestamp) FROM market_data 
                WHERE symbol = ? AND interval = ?
            ''', (symbol, interval))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                # Ensure we return a timezone-aware timestamp if possible, or naive
                return pd.to_datetime(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting last timestamp: {e}")
            return None

    def save_data(self, df, symbol, interval):
        """Upserts market data into the database."""
        try:
            if df is None or df.empty:
                return

            # Prepare DataFrame for storage
            data = df.copy()
            
            # Handle Index (Timestamp)
            if isinstance(data.index, pd.DatetimeIndex):
                data = data.reset_index()
            
            # Normalize timestamp column name
            cols = [str(c).lower() for c in data.columns]
            
            # Map columns to standard names
            col_map = {}
            for c in data.columns:
                c_lower = str(c).lower()
                if c_lower in ['date', 'datetime']:
                    col_map[c] = 'timestamp'
                elif c_lower == 'open':
                    col_map[c] = 'open'
                elif c_lower == 'high':
                    col_map[c] = 'high'
                elif c_lower == 'low':
                    col_map[c] = 'low'
                elif c_lower == 'close':
                    col_map[c] = 'close'
                elif c_lower == 'volume':
                    col_map[c] = 'volume'
            
            data.rename(columns=col_map, inplace=True)
            
            # Fallback if timestamp wasn't found (e.g. it was the index and got reset to 'index' or similar)
            if 'timestamp' not in data.columns and 'Date' in data.columns:
                 data.rename(columns={'Date': 'timestamp'}, inplace=True)

            # Ensure we have the columns we need
            if 'volume' not in data.columns:
                data['volume'] = 0
            
            records = []
            for _, row in data.iterrows():
                try:
                    ts = str(row['timestamp'])
                    records.append((
                        symbol, 
                        interval, 
                        ts, 
                        float(row['open']), 
                        float(row['high']), 
                        float(row['low']), 
                        float(row['close']), 
                        float(row['volume'])
                    ))
                except Exception as row_e:
                    continue # Skip malformed rows

            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # INSERT OR REPLACE updates existing candles
            cursor.executemany('''
                INSERT OR REPLACE INTO market_data (symbol, interval, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            conn.commit()
            conn.close()
            self.logger.info(f"Saved {len(records)} records to DB for {symbol} ({interval})")
            
        except Exception as e:
            self.logger.error(f"Error saving data to DB: {e}")

    def load_data(self, symbol, interval):
        """Loads all historical data from database."""
        try:
            conn = sqlite3.connect(self.db_name)
            query = "SELECT timestamp, open, high, low, close, volume FROM market_data WHERE symbol = ? AND interval = ? ORDER BY timestamp ASC"
            
            df = pd.read_sql_query(query, conn, params=(symbol, interval), parse_dates=['timestamp'])
            conn.close()
            
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                # Capitalize columns to match yfinance output format expected by app
                df.columns = [c.capitalize() for c in df.columns]
                
            return df
        except Exception as e:
            self.logger.error(f"Error loading data from DB: {e}")
            return pd.DataFrame()
