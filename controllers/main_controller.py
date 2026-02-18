import threading
import concurrent.futures
from services.logger import Logger
from services.scanner_service import ScannerService
from services.performance_service import PerformanceService

class MainController:
    def __init__(self, view, services):
        self.view = view
        self.market_data = services['market']
        self.ai_trader = services['ai']
        self.news_service = services['news']
        self.chart_service = services['chart']
        self.scanner = ScannerService(self.market_data)
        self.logger = Logger()
        self.last_df = None
        self.current_analysis_data = None
        
        self.performance_service = PerformanceService(self.market_data.db)
        
        # Inject AI into scanner for smart scanning
        self.scanner.ai_service = self.ai_trader
        
        # List of pairs to scan
        self.scan_pairs = [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", 
            "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "XAUUSD", "BTC-USD"
        ]
        self.view.symbol_option.configure(values=self.scan_pairs)

    def on_startup(self):
        """Grades trades and loads stats on start."""
        def startup_tasks():
            self.performance_service.grade_open_trades()
            self.update_stats()
            self._startup_worker()
            self.load_journal_data()
            
        threading.Thread(target=startup_tasks, daemon=True).start()

    def update_stats(self):
        """Fetches stats from DB and updates UI."""
        stats = self.market_data.db.get_performance_stats()
        self.view.after(0, lambda: self.view.update_stats_display(stats))

    def _startup_worker(self):
        """Step 1: Fetch Data (Thread)"""
        try:
            inputs = self.view.get_inputs()
            symbol = inputs['symbol']
            timeframe = inputs['timeframe']

            self.view.after(0, lambda: self.view.update_status(f"Startup: Fetching {symbol}..."))
            
            df, error = self.market_data.fetch_data(symbol, timeframe)
            if error:
                self.view.after(0, lambda: self.view.display_error(error))
                return

            # Calculations
            self.last_df = self.market_data.calculate_indicators(df)
            
            # Step 2: Render Chart (Main Thread)
            self.view.after(0, self._render_chart_only)
            self.view.after(0, lambda: self.view.update_status(f"Ready. {symbol} loaded."))
            
        except Exception as e:
            self.logger.exception(f"Startup error: {e}")

    def _render_chart_only(self):
        """Executed on Main Thread to safely use Matplotlib."""
        try:
            if self.last_df is not None:
                fig = self.chart_service.create_chart_figure(self.last_df, None)
                self.view.embed_chart(fig)
        except Exception as e:
            self.logger.error(f"Chart render error: {e}")

    def load_symbol(self, symbol):
        """Called when user clicks a button in the scanner list."""
        self.view.symbol_var.set(symbol)
        # Trigger the standard load
        threading.Thread(target=self._startup_worker, daemon=True).start()

    # --- ANALYSIS PIPELINE ---

    def start_analysis(self):
        """Starts the 3-step analysis pipeline."""
        self.view.analyze_btn.configure(state="disabled", text="Analyzing...")
        self.view.result_box.configure(state="normal")
        self.view.result_box.delete("0.0", "end")
        self.view.update_status("1. Fetching Market Data...")
        
        # Step 1: Data (Thread)
        threading.Thread(target=self._pipeline_step_1_data, daemon=True).start()

    def _pipeline_step_1_data(self):
        try:
            inputs = self.view.get_inputs()
            symbol = inputs['symbol']
            main_tf = inputs['timeframe']

            # Fetch Data
            df, error = self.market_data.fetch_data(symbol, main_tf)
            if error:
                self.view.after(0, lambda: self.view.display_error(error))
                self.view.after(0, lambda: self.view.analyze_btn.configure(state="normal", text="Analyze Symbol"))
                return
            
            self.last_df = self.market_data.calculate_indicators(df)
            
            # 2. Fetch Higher Timeframe Context
            htf_context = "Higher Timeframe Data Unavailable"
            try:
                htf_map = {'1h': '4h', '4h': '1d', '1d': '1wk'}
                htf = htf_map.get(main_tf, '1d')
                
                df_htf, err_htf = self.market_data.fetch_data(symbol, htf)
                if not err_htf and df_htf is not None:
                    df_htf = self.market_data.calculate_indicators(df_htf)
                    last_htf = df_htf.iloc[-1]
                    
                    htf_trend = "BULLISH" if last_htf['Close'] > last_htf['EMA_200'] else "BEARISH"
                    htf_context = (
                        f"**{htf.upper()} Trend:** {htf_trend}\n"
                        f"- RSI: {last_htf['RSI']:.2f}\n"
                        f"- Price vs EMA200: {'Above' if htf_trend == 'BULLISH' else 'Below'}"
                    )
            except Exception as e:
                self.logger.error(f"HTF Fetch Error: {e}")

            # Trigger Step 2 (Main Thread)
            self.view.after(0, lambda: self._pipeline_step_2_visuals(htf_context))
            
        except Exception as e:
            self.logger.exception(f"Pipeline Step 1 Error: {e}")
            self.view.after(0, lambda: self.view.display_error(str(e)))
            self.view.after(0, lambda: self.view.analyze_btn.configure(state="normal", text="Analyze Symbol"))

    def _pipeline_step_2_visuals(self, htf_context):
        """
        Step 2: Generate Charts & Images (Main Thread).
        Matplotlib is NOT thread-safe, so this MUST be here.
        """
        try:
            self.view.append_status("\n2. Generating Vision Data...")
            
            # 1. Update UI Chart immediately
            fig = self.chart_service.create_chart_figure(self.last_df, None)
            self.view.embed_chart(fig)
            
            # 2. Generate Image for AI
            chart_image = self.chart_service.generate_chart_image(self.last_df)
            
            # Trigger Step 3 (Thread)
            threading.Thread(target=self._pipeline_step_3_ai, args=(chart_image, htf_context), daemon=True).start()
            
        except Exception as e:
            self.logger.exception(f"Pipeline Step 2 Error: {e}")
            self.view.display_error(f"Vision Error: {e}")
            self.view.analyze_btn.configure(state="normal", text="Analyze Symbol")

    def _pipeline_step_3_ai(self, chart_image, htf_context):
        """Step 3: Intelligence (Thread) rewritten for Council Architecture."""
        try:
            inputs = self.view.get_inputs()
            symbol = inputs['symbol']
            provider = inputs['provider']
            model = inputs['model']
            strategy = inputs['strategy']

            self.view.after(0, lambda: self.view.append_status("\n3. Gathering Context..."))
            
            # 1. Gather Context
            auto_news = self.news_service.fetch_news(symbol)
            calendar_text, is_high_impact = self.news_service.fetch_economic_calendar(symbol)
            
            # Safety Warning
            if is_high_impact:
                msg = "⚠️ HIGH IMPACT EVENT DETECTED TODAY. TRADING IS RISKY."
                self.view.after(0, lambda: self.view.append_status(f"\n\n{msg}"))
                calendar_text = f"!!! WARNING: {msg} !!!\n{calendar_text}"

            manual_news = inputs['news_context']
            full_news = f"{manual_news}\n{auto_news}" if manual_news else auto_news
            pivots = self.market_data.calculate_pivots(self.last_df)
            
            tech_summary = self.last_df.iloc[-1].to_dict()
            # Add mtf_trend for Master
            tech_summary['higher_timeframe'] = htf_context

            # 2. Sequential Agent Analysis (The Council)
            self.view.after(0, lambda: self.view.append_status("\n4. Consulting Quant Agent..."))
            quant_report = self.ai_trader.analyze_quant(tech_summary, pivots, strategy, provider, model)

            self.view.after(0, lambda: self.view.append_status("\n5. Consulting Vision Agent..."))
            vision_report = self.ai_trader.analyze_vision(chart_image, strategy, provider, model)

            self.view.after(0, lambda: self.view.append_status("\n6. Consulting Fundamental Agent..."))
            fund_report = self.ai_trader.analyze_fundamental(full_news, calendar_text, provider, model)

            # 3. Master Synthesis
            self.view.after(0, lambda: self.view.append_status("\n7. Master Decision in progress..."))
            
            council_reports = f"""
            QUANT: {quant_report}
            VISION: {vision_report}
            FUNDAMENTAL: {fund_report}
            """
            
            final_response = self.ai_trader.analyze_master(
                council_reports, 
                tech_summary,
                provider=provider, 
                model=model
            )

            if "error" in final_response:
                self.view.after(0, lambda: self.view.display_error(final_response['error']))
                self.view.after(0, lambda: self.view.analyze_btn.configure(state="normal", text="Analyze Symbol"))
                return

            # 4. Finalize
            self.view.after(0, lambda: self._finalize_results(final_response, {"symbol": symbol, "price": tech_summary['Close']}))

        except Exception as e:
            self.logger.exception(f"Council Pipeline Error: {e}")
            self.view.after(0, lambda: self.view.display_error(str(e)))
            self.view.after(0, lambda: self.view.analyze_btn.configure(state="normal", text="Analyze Symbol"))

    def _finalize_results(self, ai_response, tech_details):
        """Update UI with final results (Main Thread)."""
        report = self._format_report(ai_response, tech_details)
        self.view.display_report(report)
        self.view.analyze_btn.configure(state="normal", text="Analyze Symbol")
        
        # Store data
        self.current_analysis_data = {
            "symbol": tech_details['symbol'],
            "timeframe": self.view.timeframe_var.get(),
            "provider": self.view.provider_var.get(),
            "decision": ai_response.get('decision', 'WAIT'),
            "entry": ai_response.get('entry'),
            "stop_loss": ai_response.get('stop_loss'),
            "take_profit": ai_response.get('take_profit'),
            "confidence": ai_response.get('confidence_score', 0),
            "reasoning": ai_response.get('reasoning', ''),
            "model": self.view.model_var.get()
        }
        self.view.save_btn.configure(state="normal", fg_color="#2B823A")
        
        # Update chart with levels
        fig = self.chart_service.create_chart_figure(self.last_df, ai_response)
        self.view.embed_chart(fig)

    def _format_report(self, ai, tech):
        return (
            f"\n{'='*30}\n DECISION: {ai.get('decision', 'N/A')} ({ai.get('confidence_score', '0')}%) \n{'='*30}\n\n"
            f"--- SETUP ---\nEntry: {ai.get('entry')}\nSL: {ai.get('stop_loss')}\nTP: {ai.get('take_profit')}\n\n"
            f"--- DATA ---\nPrice: {tech.get('price')} | Trend: {tech.get('trend')}\n"
            f"RSI: {tech.get('rsi')} | ATR: {tech.get('atr')}\n\n"
            f"--- REASONING ---\n{ai.get('reasoning', 'N/A')}"
        )

    # --- Journal ---
    def save_current_analysis(self):
        if self.current_analysis_data:
            success = self.market_data.db.save_analysis(self.current_analysis_data)
            if success:
                self.view.save_btn.configure(state="disabled", text="Saved!", fg_color="#555555")
                self.load_journal_data()
            else:
                self.view.display_error("Failed to save to database.")

    def load_journal_data(self):
        """Fetches history and updates UI."""
        rows = self.market_data.db.get_journal_entries()
        self.view.after(0, lambda: self.view.populate_journal(rows))

    def get_models_for_provider(self, provider):
        if provider == "Gemini": return ["gemini-2.0-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash"]
        if provider == "Cerebras": return ["llama3.1-8b", "llama3.1-70b"]
        if provider == "Groq": return ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
        if provider == "OpenRouter": return ["google/gemini-2.0-flash-lite-preview-02-05:free", "stepfun/step-3.5-flash:free"]
        return []

    # --- Scanner ---
    def run_market_scan(self):
        """Scans all pairs in background."""
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        timeframe = self.view.timeframe_var.get()
        found_count = 0
        
        # Use ThreadPool to speed up network requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Prepare futures
            future_to_symbol = {
                executor.submit(self.scanner.scan_symbol, symbol, timeframe): symbol 
                for symbol in self.scan_pairs
            }
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        # Update UI safely
                        self.view.after(0, lambda r=result: self.view.add_scan_result(r))
                        found_count += 1
                except Exception as e:
                    self.logger.error(f"Scan failed for {symbol}: {e}")

        self.view.after(0, self.view.reset_scan_button)
        if found_count == 0:
            self.view.after(0, lambda: self.view.update_status("No opportunities found."))
