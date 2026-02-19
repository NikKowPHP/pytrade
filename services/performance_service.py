import pandas as pd
import yfinance as yf
from services.logger import Logger
from services.rag_service import RAGService

class PerformanceService:
    def __init__(self, db):
        self.logger = Logger()
        self.db = db
        self.rag_service = RAGService()

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
                    
                    # NEW: Learn from this trade
                    try:
                        context = self.db.get_trade_context(trade['id'])
                        if context:
                            profit_r = 0.0
                            if result == "WIN":
                                risk = trade['entry'] - trade['stop_loss']
                                if risk != 0:
                                    profit_r = abs((exit_price - trade['entry']) / risk)
                            elif result == "LOSS":
                                profit_r = -1.0
                            
                            self.rag_service.add_memory(trade['id'], context, result, profit_r)
                    except Exception as e:
                        self.logger.error(f"Failed to save RAG memory for trade {trade['id']}: {e}")
            except Exception as e:
                self.logger.error(f"Grader error for ID {trade['id']}: {e}")

    def run_grader(self):
        """Alias for grade_open_trades to maintain compatibility if needed."""
        self.grade_open_trades()
