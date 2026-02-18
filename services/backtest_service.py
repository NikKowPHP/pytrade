import pandas as pd
import threading
from datetime import datetime, timedelta
from services.logger import Logger

class BacktestService:
    def __init__(self, market_data, ai_service, chart_service):
        self.market_data = market_data
        self.ai_service = ai_service
        self.chart_service = chart_service
        self.logger = Logger()
        self.is_running = False

    def run_backtest(self, symbol, timeframe, provider, model, strategy, days=60, progress_callback=None):
        """
        Runs a walk-forward backtest.
        """
        self.is_running = True
        results = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0,
            "trades": []
        }

        try:
            # 1. Fetch full data
            # To test the last 60 days, we need those 60 plus lookback for indicators
            df, error = self.market_data.fetch_data(symbol, timeframe)
            if error:
                self.logger.error(f"Backtest data error: {error}")
                return {"error": error}

            df = self.market_data.calculate_indicators(df)
            
            # 2. Determine index range
            # We iterate through the last 'days' candles
            total_candles = len(df)
            start_idx = max(200, total_candles - days) # Ensure at least 200 candles for EMA
            
            for i in range(start_idx, total_candles):
                if not self.is_running:
                    break

                if progress_callback:
                    progress_callback(i - start_idx + 1, total_candles - start_idx)

                # Slice data up to the current backtest "now"
                df_slice = df.iloc[:i+1]
                current_time = df_slice.index[-1]
                
                # 3. AI Analysis
                # Note: No historical news context available for previous dates
                pivots = self.market_data.calculate_pivots(df_slice)
                latest_tech = df_slice.iloc[-1].to_dict()
                
                # Vision Data
                chart_image = self.chart_service.generate_chart_image(df_slice)
                
                # Council reports (Mimic MainController pipeline but simplified/sequential)
                quant_report = self.ai_service.analyze_quant(latest_tech, pivots, strategy, provider, model)
                vision_report = self.ai_service.analyze_vision(chart_image, strategy, provider, model)
                
                council_summary = f"QUANT: {quant_report}\nVISION: {vision_report}\nFUNDAMENTAL: N/A (Historical News Unavailable)"
                
                ai_decision = self.ai_service.analyze_master(council_summary, latest_tech, provider, model)
                
                decision = ai_decision.get('decision', 'WAIT')
                if decision in ["BUY", "SELL"]:
                    # 4. Simulate Outcome
                    entry = ai_decision.get('entry')
                    sl = ai_decision.get('stop_loss')
                    tp = ai_decision.get('take_profit')
                    
                    if entry and sl and tp:
                        trade_result = self._simulate_outcome(df, i + 1, decision, entry, sl, tp)
                        if trade_result:
                            results["total_trades"] += 1
                            results["trades"].append({
                                "time": str(current_time),
                                "symbol": symbol,
                                "decision": decision,
                                "entry": entry,
                                "sl": sl,
                                "tp": tp,
                                "result": trade_result['status'],
                                "exit_price": trade_result['exit_price']
                            })
                            if trade_result['status'] == "WIN":
                                results["wins"] += 1
                            else:
                                results["losses"] += 1

            # 5. Final Report
            results["win_rate"] = (results["wins"] / results["total_trades"] * 100) if results["total_trades"] > 0 else 0
            results["profit_factor"] = (results["wins"] / results["losses"]) if results["losses"] > 0 else (results["wins"] if results["wins"] > 0 else 0)
            
            return results

        except Exception as e:
            self.logger.exception(f"Backtest error: {e}")
            return {"error": str(e)}
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False

    def _simulate_outcome(self, df, start_idx, direction, entry, sl, tp):
        """
        Loops through future candles to find if SL or TP was hit.
        """
        # We look ahead for up to 50 candles (timeout)
        max_lookahead = 50 
        end_idx = min(start_idx + max_lookahead, len(df))
        
        for j in range(start_idx, end_idx):
            row = df.iloc[j]
            hi, lo = float(row['High']), float(row['Low'])
            
            if direction == "BUY":
                if lo <= sl:
                    return {"status": "LOSS", "exit_price": sl}
                if hi >= tp:
                    return {"status": "WIN", "exit_price": tp}
            else: # SELL
                if hi >= sl:
                    return {"status": "LOSS", "exit_price": sl}
                if lo <= tp:
                    return {"status": "WIN", "exit_price": tp}
                    
        return None # No outcome within lookahead
