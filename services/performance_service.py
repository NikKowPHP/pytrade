import pandas as pd
import yfinance as yf
from services.logger import Logger

class PerformanceService:
    def __init__(self, db):
        self.logger = Logger()
        self.db = db

    def grade_open_trades(self):
        """Checks historical price data to resolve open AI signals."""
        self.logger.info("Verifying trade outcomes...")
        open_trades = self.db.get_open_trades()
        
        for trade in open_trades:
            try:
                symbol = trade['symbol']
                # Use hourly data for precise hit detection
                ticker = f"{symbol}=X" if len(symbol) == 6 and not symbol.endswith('=X') else symbol
                
                # Fetch data since entry
                df = yf.download(ticker, start=trade['timestamp'], interval="1h", progress=False)
                
                if df.empty:
                    continue

                direction = "BUY" if trade['take_profit'] > trade['entry'] else "SELL"
                result = None
                exit_price = None

                for _, row in df.iterrows():
                    hi, lo = float(row['High']), float(row['Low'])
                    
                    if direction == "BUY":
                        if hi >= trade['take_profit']: 
                            result, exit_price = "WIN", trade['take_profit']
                        elif lo <= trade['stop_loss']: 
                            result, exit_price = "LOSS", trade['stop_loss']
                    else: # SELL
                        if lo <= trade['take_profit']: 
                            result, exit_price = "WIN", trade['take_profit']
                        elif hi >= trade['stop_loss']: 
                            result, exit_price = "LOSS", trade['stop_loss']
                    
                    if result: 
                        break

                if result:
                    self.db.update_trade_result(trade['id'], result, exit_price)
            except Exception as e:
                self.logger.error(f"Grader error for ID {trade['id']}: {e}")

    def run_grader(self):
        """Alias for grade_open_trades to maintain compatibility if needed."""
        self.grade_open_trades()
