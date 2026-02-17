import threading
from services.logger import Logger

class MainController:
    def __init__(self, view, services):
        self.view = view
        self.market_data = services['market']
        self.ai_trader = services['ai']
        self.news_service = services['news']
        self.chart_service = services['chart']
        self.logger = Logger()
        self.last_df = None

    def on_startup(self):
        """Called when UI is ready."""
        threading.Thread(target=self._load_initial_data, daemon=True).start()

    def _load_initial_data(self):
        try:
            inputs = self.view.get_inputs()
            symbol = inputs['symbol']
            timeframe = inputs['timeframe']

            self.view.after(0, lambda: self.view.update_status(f"Startup: Fetching {symbol}..."))
            
            df, error = self.market_data.fetch_data(symbol, timeframe)
            if error:
                self.view.after(0, lambda: self.view.display_error(error))
                return

            self.last_df = self.market_data.calculate_indicators(df)
            
            # Generate chart (no AI overlays yet)
            fig = self.chart_service.create_chart_figure(self.last_df, None)
            
            self.view.after(0, lambda: self.view.embed_chart(fig))
            self.view.after(0, lambda: self.view.update_status(f"Ready. {symbol} data loaded."))
        except Exception as e:
            self.logger.exception(f"Startup error: {e}")
            self.view.after(0, lambda: self.view.display_error(str(e)))

    def get_models_for_provider(self, provider):
        if provider == "Gemini": return ["gemini-2.0-flash-exp", "gemini-1.5-flash"]
        if provider == "Cerebras": return ["llama3.1-70b", "llama3.1-8b"]
        if provider == "Groq": return ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
        if provider == "OpenRouter": return ["stepfun/step-3.5-flash:free", "google/gemini-2.0-flash-lite-preview-02-05:free"]
        return []

    def start_analysis(self):
        threading.Thread(target=self._run_analysis_pipeline, daemon=True).start()

    def _run_analysis_pipeline(self):
        try:
            inputs = self.view.get_inputs()
            symbol = inputs['symbol']
            
            self.view.after(0, lambda: self.view.update_status("1. Fetching Market Data..."))
            
            # 1. Data
            df, error = self.market_data.fetch_data(symbol, inputs['timeframe'])
            if error:
                self.view.after(0, lambda: self.view.display_error(error))
                return
            
            self.last_df = self.market_data.calculate_indicators(df)

            # 2. News
            self.view.after(0, lambda: self.view.append_status("\n2. Fetching News & Calendar..."))
            auto_news = self.news_service.fetch_news(symbol)
            calendar = self.news_service.fetch_economic_calendar(symbol)
            full_context = f"{inputs['news_context']}\n\n{auto_news}" if inputs['news_context'] else auto_news

            # 3. AI
            self.view.after(0, lambda: self.view.append_status("\n3. Consulting AI..."))
            prompt, tech_details = self.ai_trader.generate_prompt(
                self.last_df, symbol, news_context=full_context, calendar_context=calendar
            )
            
            ai_response = self.ai_trader.analyze(prompt, provider=inputs['provider'], model=inputs['model'])
            
            if "error" in ai_response:
                self.view.after(0, lambda: self.view.display_error(ai_response['error']))
                return

            # 4. Result Formatting
            report = self._format_report(ai_response, tech_details)
            self.view.after(0, lambda: self.view.display_report(report))

            # 5. Chart Update
            fig = self.chart_service.create_chart_figure(self.last_df, ai_response)
            self.view.after(0, lambda: self.view.embed_chart(fig))

        except Exception as e:
            self.logger.exception(f"Analysis error: {e}")
            self.view.after(0, lambda: self.view.display_error(str(e)))

    def _format_report(self, ai, tech):
        return (
            f"\n{'='*30}\n DECISION: {ai.get('decision', 'N/A')} ({ai.get('confidence_score', '0')}%) \n{'='*30}\n\n"
            f"--- SETUP ---\nEntry: {ai.get('entry')}\nSL: {ai.get('stop_loss')}\nTP: {ai.get('take_profit')}\n\n"
            f"--- DATA ---\nPrice: {tech.get('price')} | Trend: {tech.get('trend')}\nRSI: {tech.get('rsi')}\n\n"
            f"--- REASONING ---\n{ai.get('reasoning', 'N/A')}"
        )
