import yfinance as yf
import pandas as pd
from datetime import datetime
from services.logger import Logger

class PerformanceService:
    def __init__(self, db):
        self.logger = Logger()
        self.db = db

    def run_grader(self):
        """Checks all open trades to see if they hit SL or TP."""
        self.logger.info("Running Trade Grader...")
        trades = self.db.get_open_trades()
        
        if not trades:
            return

        for trade in trades:
            try:
                symbol = trade['symbol']
                entry_ts = pd.to_datetime(trade['timestamp'])
                
                # Determine direction
                # If TP > Entry -> BUY, Else SELL
                direction = "BUY" if trade['take_profit'] > trade['entry'] else "SELL"
                
                # Fetch data since entry
                # We use yfinance to get hourly data from that date
                # Note: yf.download is strict on start dates. We'll fetch last 30 days to be safe 
                # if the trade is recent.
                
                ticker = f"{symbol}=X" if not symbol.endswith('=X') else symbol
                df = yf.download(ticker, period="1mo", interval="1h", progress=False)
                
                if df.empty:
                    continue
                    
                # Filter data to be AFTER entry time
                # Ensure timezone compatibility (localize if needed, naive here for simplicity)
                if df.index.tz is not None:
                    entry_ts = entry_ts.tz_localize(df.index.tz)
                
                mask = df.index > entry_ts
                future_data = df.loc[mask]
                
                if future_data.empty:
                    continue

                # Check for hits
                result = None
                exit_price = 0.0

                for index, row in future_data.iterrows():
                    high = float(row['High'])
                    low = float(row['Low'])
                    
                    if direction == "BUY":
                        if high >= trade['take_profit']:
                            result = "WIN"
                            exit_price = trade['take_profit']
                            break
                        if low <= trade['stop_loss']:
                            result = "LOSS"
                            exit_price = trade['stop_loss']
                            break
                    else: # SELL
                        if low <= trade['take_profit']:
                            result = "WIN"
                            exit_price = trade['take_profit']
                            break
                        if high >= trade['stop_loss']:
                            result = "LOSS"
                            exit_price = trade['stop_loss']
                            break
                
                if result:
                    self.db.update_trade_result(trade['id'], result, exit_price)

            except Exception as e:
                self.logger.error(f"Error grading trade {trade.get('id')}: {e}")
