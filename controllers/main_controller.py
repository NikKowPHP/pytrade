import threading
import concurrent.futures
import pandas as pd
from services.logger import Logger
from services.scanner_service import ScannerService
from services.performance_service import PerformanceService
from services.backtest_service import BacktestService
from services.rag_service import RAGService
from services.structure_service import StructureService
from services.math_service import MathService
from services.config_manager import ConfigManager
from config import AI_MODELS

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
        self.backtester = BacktestService(self.market_data, self.ai_trader, self.chart_service)
        self.macro_service = services['macro']
        self.cot_service = services.get('cot') # COT Service
        self.current_macro_text = ""
        self.rag_service = RAGService()
        self.structure_service = StructureService()
        self.math_service = MathService()
        self.config_manager = ConfigManager()
        
        # Inject AI into scanner for smart scanning
        self.scanner.ai_service = self.ai_trader
        
        # List of pairs to scan
        self.scan_pairs = [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
            "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
            "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
            "AUDJPY", "AUDCHF", "AUDNZD", "AUDCAD",
            "NZDJPY", "NZDCHF", "NZDCAD",
            "CADJPY", "CADCHF", "CHFJPY",
            "USDMXN", "USDTRY", "USDZAR", "USDSEK", "USDNOK",
            "XAUUSD", "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"
        ]
        self.view.symbol_option.configure(values=self.scan_pairs)

    def save_agent_config(self):
        """Saves values from Settings tab to JSON."""
        try:
            settings = self.view.get_settings_input()
            if self.config_manager.save_config(settings):
                self.view.display_report("Configuration Saved Successfully!")
            else:
                self.view.display_error("Failed to save configuration.")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            self.view.display_error(f"Error saving config: {e}")

    def on_startup(self):
        """Grades trades and loads stats on start."""
        def startup_tasks():
            self.performance_service.grade_open_trades()
            self.update_stats()
            self._startup_worker()
            self.load_journal_data()
            if self.cot_service:
                self.cot_service.update_cot_data(self.market_data.db)
            
            # Load User Config into UI
            self.view.after(0, lambda: self.view.load_settings_display(self.config_manager.config))
            
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
        """Executed on Main Thread to safely use Matplotlib/WebView."""
        try:
            if self.last_df is not None:
                self.logger.info("Executing _render_chart_only")
                # Use create_chart_figure instead of get_chart_html
                fig = self.chart_service.create_chart_figure(self.last_df, None)
                self.view.embed_chart(fig)
            else:
                self.logger.warning("_render_chart_only called but last_df is None")
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
            htf = '1d' # Default fallback
            
            try:
                htf_map = {'1h': '4h', '4h': '1d', '1d': '1wk'}
                htf = htf_map.get(main_tf, '1d')
                
                df_htf, err_htf = self.market_data.fetch_data(symbol, htf)
                if not err_htf and df_htf is not None:
                    df_htf = self.market_data.calculate_indicators(df_htf)
                    last_htf = df_htf.iloc[-1]
                    
                    if pd.notna(last_htf['EMA_200']):
                        htf_trend = "BULLISH" if last_htf['Close'] > last_htf['EMA_200'] else "BEARISH"
                        ema_status = 'Above' if htf_trend == 'BULLISH' else 'Below'
                    else:
                        htf_trend = "NEUTRAL (EMA200 N/A)"
                        ema_status = "N/A"
                    
                    # HTF Structure
                    htf_struct, _ = self.structure_service.detect_structure(df_htf)
                    
                    htf_context = (
                        f"**{htf.upper()} Trend:** {htf_trend}\n"
                        f"- RSI: {last_htf['RSI']:.2f}\n"
                        f"- Price vs EMA200: {ema_status}\n"
                        f"{htf_struct}"
                    )
            except Exception as e:
                self.logger.error(f"HTF Fetch Error: {e}")

            # 3. Fetch Macro (Weekly) Context if not already fetched
            if htf != '1wk' and main_tf != '1wk':
                try:
                    df_wk, err_wk = self.market_data.fetch_data(symbol, '1wk')
                    if not err_wk and df_wk is not None:
                         df_wk = self.market_data.calculate_indicators(df_wk)
                         last_wk = df_wk.iloc[-1]
                         wk_trend = "BULLISH" if last_wk['Close'] > last_wk.get('EMA_200', 0) else "BEARISH"
                         
                         htf_context += f"\n\n**MACRO WEEKLY CONTEXT:**\n- Trend: {wk_trend}\n- RSI: {last_wk['RSI']:.2f}"
                except Exception as e:
                    self.logger.error(f"Macro Weekly Fetch Error: {e}")

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
            self.view.after(0, lambda: self.view.embed_chart(fig))
            
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
            strategy = inputs['strategy']

            self.view.after(0, lambda: self.view.append_status("\n3. Gathering Context (News & Macro)..."))
            
            # 1. Gather Context
            macro_text, macro_stats = self.macro_service.fetch_macro_context()
            self.view.after(0, lambda: self.view.update_macro_display(macro_stats))

            # Update: unpack the tuple from news_service
            auto_news, raw_headlines = self.news_service.fetch_news(symbol)
            
            # NEW: Sentiment Analysis
            self.view.after(0, lambda: self.view.append_status("\n3.5. Analyzing News Sentiment..."))
            
            # Use Sentiment Agent config
            s_prov, s_mod = self.config_manager.get_agent_config("Sentiment")
            sentiment_data = self.ai_trader.analyze_sentiment(raw_headlines, symbol, s_prov, s_mod)
            
            sent_score = float(sentiment_data.get("score", 0))
            sent_summary = sentiment_data.get("reasoning", "")
            
            # Detect Divergence
            # 1. Tech Trend (Slope of EMA 50 or Price vs EMA 200)
            last_close = self.last_df.iloc[-1]['Close']
            ema_200 = self.last_df.iloc[-1]['EMA_200']
            
            tech_bullish = last_close > ema_200
            
            divergence_msg = None
            if tech_bullish and sent_score < -0.4:
                divergence_msg = "BEARISH DIVERGENCE: Price Rising but News is Negative!"
            elif not tech_bullish and sent_score > 0.4:
                divergence_msg = "BULLISH DIVERGENCE: Price Falling but News is Positive!"

            # Update UI
            self.view.after(0, lambda: self.view.update_sentiment_meter(sent_score, sent_summary, divergence_msg))

            calendar_text, is_high_impact = self.news_service.fetch_economic_calendar(symbol)
            
            # Safety Warning
            if is_high_impact:
                msg = "⚠️ HIGH IMPACT EVENT DETECTED TODAY. TRADING IS RISKY."
                self.view.after(0, lambda: self.view.append_status(f"\n\n{msg}"))
                calendar_text = f"!!! WARNING: {msg} !!!\n{calendar_text}"

            manual_news = inputs['news_context']
            # Add to context for Master Agent
            full_news = f"SENTIMENT SCORE: {sent_score} ({sent_summary})\nDIVERGENCE CHECK: {divergence_msg if divergence_msg else 'None'}\n\n{manual_news}\n{auto_news}"
            pivots = self.market_data.calculate_pivots(self.last_df)
            
            # Calculate Smart Money Concepts
            smc_text, smc_levels = self.market_data.calculate_smart_money(self.last_df)
            
            # NEW: Correlation Matrix
            self.view.after(0, lambda: self.view.append_status("\n3.8. Checking Correlations..."))
            corr_text, corr_score = self.market_data.get_correlation_data(self.last_df, symbol, inputs['timeframe'])

            # NEW: Volume Profile (VPVR)
            vpvr_text, vpvr_levels = self.market_data.calculate_volume_profile(self.last_df)
            
            # NEW: Structure Analysis (Current TF)
            st_text, st_data = self.structure_service.detect_structure(self.last_df)
            
            # Combine with HTF context (which now includes HTF structure)
            mtf_alignment = self.structure_service.analyze_multi_timeframe(htf_context, st_text)
            
            if "⚠️" in mtf_alignment:
                 self.view.after(0, lambda: self.view.append_status(f"\n{mtf_alignment.splitlines()[1]}"))

            # NEW: Monte Carlo Simulation
            mc_text, mc_ranges = self.math_service.monte_carlo_simulation(self.last_df)

            # Update UI with correlation warning if needed
            if "⚠️" in corr_text:
                 self.view.after(0, lambda: self.view.append_status(f"\n{corr_text.splitlines()[2]}"))

            tech_summary = self.last_df.iloc[-1].to_dict()
            # Add mtf_trend for Master
            tech_summary['higher_timeframe'] = htf_context
            tech_summary['structure'] = st_text
            tech_summary['mtf_alignment'] = mtf_alignment
            tech_summary['monte_carlo'] = mc_text # Add Monte Carlo context
            # Add SMC to tech summary for Agents
            tech_summary['smart_money_concepts'] = smc_text
            tech_summary['correlations'] = corr_text  # Add to tech summary
            tech_summary['volume_profile'] = vpvr_text # Add VPVR

            # 2. Sequential Agent Analysis (The Council)
            self.view.after(0, lambda: self.view.append_status("\n4. Consulting Quant Agent..."))
            q_prov, q_mod = self.config_manager.get_agent_config("Quant")
            quant_report = self.ai_trader.analyze_quant(tech_summary, pivots, strategy, q_prov, q_mod)

            self.view.after(0, lambda: self.view.append_status("\n5. Consulting Vision Agent..."))
            v_prov, v_mod = self.config_manager.get_agent_config("Vision")
            vision_report = self.ai_trader.analyze_vision(chart_image, strategy, v_prov, v_mod)

            self.view.after(0, lambda: self.view.append_status("\n6. Consulting Fundamental Agent..."))
            f_prov, f_mod = self.config_manager.get_agent_config("Fundamental")
            fund_report = self.ai_trader.analyze_fundamental(full_news, calendar_text, f_prov, f_mod)

            # NEW: Devil's Advocate
            self.view.after(0, lambda: self.view.append_status("\n6.5. Summoning Devil's Advocate..."))
            r_prov, r_mod = self.config_manager.get_agent_config("Risk")
            risk_report = self.ai_trader.analyze_risk(tech_summary, pivots, full_news, r_prov, r_mod)

            # NEW: RAG MEMORY RETRIEVAL
            self.view.after(0, lambda: self.view.append_status("\n6.8. Checking RAG Memory..."))
            
            # Construct Context String for RAG
            # Format: "RSI: 75 | Trend: BULLISH | Pattern: Double Top | News: Negative"
            rag_query = (
                f"RSI: {tech_summary.get('RSI', 0):.2f} | "
                f"Trend: {tech_summary.get('higher_timeframe', '').splitlines()[0]} | "
                f"SMC: {smc_text} | "
                f"News Score: {sent_score}"
            )
            
            memory_data = self.rag_service.find_similar_trades(rag_query, limit=3)
            
            # 3. Master Synthesis
            self.view.after(0, lambda: self.view.append_status("\n7. Master Decision in progress..."))
            
            council_reports = f"""
            QUANT ANALYST: {quant_report}
            VISION ANALYST: {vision_report}
            FUNDAMENTAL ANALYST: {fund_report}
            ----------------------------------
            DEVIL'S ADVOCATE (RISK ASSESSMENT):
            {risk_report}
            """
            
            # Fetch Master configuration
            m_prov, m_mod = self.config_manager.get_agent_config("Master")
            
            final_response = self.ai_trader.analyze_master(
                council_reports, 
                tech_summary,
                provider=m_prov, 
                model=m_mod,
                macro_context=macro_text,
                rag_data=memory_data
            )
            
            # Embed the context used for this analysis so we can save it later
            final_response['rag_context_used'] = rag_query

            if "error" in final_response:
                self.view.after(0, lambda: self.view.display_error(final_response['error']))
                self.view.after(0, lambda: self.view.analyze_btn.configure(state="normal", text="Analyze Symbol"))
                return

            # --- RISK REGIME FILTER (New) ---
            # Block BUYs on High-Beta assets if SPX < 20MA (Risk Off)
            
            # 1. Define High-Beta Assets (Risk-On)
            # Crypto and High-Beta Forex (AUD, NZD, GBP, JPY Crosses)
            RISK_ON_ASSETS = [
                "AUDUSD", "NZDUSD", "GBPUSD", "EURUSD",
                "AUDJPY", "NZDJPY", "GBPJPY", "EURJPY",
                "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD",
                "SPX", "NDX"
            ]
            
            # 2. Get Regime from Macro Stats
            risk_regime = macro_stats.get('risk_regime', 'NEUTRAL')
            is_risk_off = "RISK OFF" in risk_regime
            
            # 3. Apply Logic
            if final_response.get('decision') == "BUY":
                if symbol in RISK_ON_ASSETS and is_risk_off:
                    
                    # Override Decision
                    final_response['decision'] = "WAIT"
                    
                    # Append Warning to Reasoning
                    block_msg = (
                        "\n\n⛔ **RISK REGIME BLOCK TRIGGERED** ⛔\n"
                        "Global Equities are in a downtrend (SPX < 20-Day SMA). "
                        "Buying high-beta assets like AUD/NZD/Crypto is statistically dangerous here. "
                        "The AI's Buy signal has been OVERRIDDEN to WAIT/PROTECT CAPITAL."
                    )
                    final_response['reasoning'] = block_msg + "\n\nOriginal Reasoning:\n" + final_response.get('reasoning', '')
                    
                    self.view.after(0, lambda: self.view.append_status("\n⛔ RISK FILTER: Trade Blocked (Market is Risk-Off)"))

            # 4. Finalize
            self.view.after(0, lambda: self._finalize_results(final_response, {"symbol": symbol, "price": tech_summary['Close']}, master_config={"provider": m_prov, "model": m_mod}))

        except Exception as e:
            self.logger.exception(f"Council Pipeline Error: {e}")
            self.view.after(0, lambda: self.view.display_error(str(e)))
            self.view.after(0, lambda: self.view.analyze_btn.configure(state="normal", text="Analyze Symbol"))

    def _finalize_results(self, ai_response, tech_details, master_config=None):
        """Update UI with final results (Main Thread)."""
        report = self._format_report(ai_response, tech_details)
        self.view.display_report(report)
        self.view.analyze_btn.configure(state="normal", text="Analyze Symbol")
        
        # Store data
        self.current_analysis_data = {
            "symbol": tech_details['symbol'],
            "timeframe": self.view.timeframe_var.get(),
            "provider": master_config['provider'] if master_config else "Unknown",
            "decision": ai_response.get('decision', 'WAIT'),
            "entry": ai_response.get('entry'),
            "stop_loss": ai_response.get('stop_loss'),
            "take_profit": ai_response.get('take_profit'),
            "confidence": ai_response.get('confidence_score', 0),
            "reasoning": ai_response.get('reasoning', ''),
            "confidence": ai_response.get('confidence_score', 0),
            "reasoning": ai_response.get('reasoning', ''),
            "model": master_config['model'] if master_config else "Unknown",
            "context": ai_response.get('rag_context_used', '')
        }
        self.view.save_btn.configure(state="normal", fg_color="#2B823A")
        
        # Update chart with levels
        self.logger.info("Updating chart with AI levels in _finalize_results")
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
        """Fetches models from central config."""
        return AI_MODELS.get(provider, [])

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

    # --- Backtest Orchestration ---

    def start_backtest(self):
        """Orchestrates the backtest in a background thread."""
        inputs = self.view.get_inputs()
        symbol = inputs['symbol']
        timeframe = inputs['timeframe']
        strategy = inputs['strategy']
        
        # Use backtest-specific model settings
        provider = self.view.bt_provider_var.get()
        model = self.view.bt_model_var.get()
        
        days = int(self.view.bt_days_var.get())

        def progress_wrapper(current, total):
            self.view.after(0, lambda: self.view.update_backtest_progress(current, total))

        def run():
            results = self.backtester.run_backtest(
                symbol, timeframe, provider, model, strategy, days, 
                progress_callback=progress_wrapper
            )
            self.view.after(0, lambda: self.view.display_backtest_results(results))

        threading.Thread(target=run, daemon=True).start()
