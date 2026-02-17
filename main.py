import customtkinter as ctk
import threading
from services.market_data import MarketDataProvider
from services.ai_service import AITrader
from services.news_service import NewsService
from services.chart_service import ChartService
from services.logger import Logger

class ForexApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.logger.info("Initializing ForexApp")

        self.title("AI Forex Swing Assistant - Professional Edition")
        self.geometry("1100x900") # Wider for chart
        
        try:
            # Initialize Services
            self.data_provider = MarketDataProvider()
            self.ai_trader = AITrader()
            self.news_service = NewsService()
            self.chart_service = ChartService()

            # Layout Configuration
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=3) # Chart column
            self.grid_rowconfigure(5, weight=1)

            # Header
            self.header_label = ctk.CTkLabel(self, text="AI Forex Professional Analysis", font=("Roboto", 24, "bold"))
            self.header_label.grid(row=0, column=0, columnspan=2, padx=20, pady=20)

            # Inputs Frame
            self.input_frame = ctk.CTkFrame(self)
            self.input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            self.input_frame.grid_columnconfigure(1, weight=1)

            # Symbol Input
            self.symbol_label = ctk.CTkLabel(self.input_frame, text="Symbol:")
            self.symbol_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
            
            self.pairs = [
                "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
                "EURGBP", "EURJPY", "GBPJPY", "XAUUSD"
            ]
            self.symbol_option = ctk.CTkOptionMenu(self.input_frame, values=self.pairs)
            self.symbol_option.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            self.symbol_option.set("EURUSD")

            # Timeframe Input
            self.timeframe_label = ctk.CTkLabel(self.input_frame, text="Timeframe:")
            self.timeframe_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
            self.timeframe_option = ctk.CTkOptionMenu(self.input_frame, values=["1h", "4h", "1d"])
            self.timeframe_option.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
            self.timeframe_option.set("4h")

            # Provider Input
            self.provider_label = ctk.CTkLabel(self.input_frame, text="AI Provider:")
            self.provider_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
            self.provider_option = ctk.CTkOptionMenu(self.input_frame, values=["Gemini", "Cerebras", "Groq", "OpenRouter"], command=self.update_models)
            self.provider_option.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
            self.provider_option.set("Gemini")

            # Model Selection
            self.model_label = ctk.CTkLabel(self.input_frame, text="Model:")
            self.model_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
            self.model_option = ctk.CTkOptionMenu(self.input_frame, values=["gemini-2.0-flash-exp"])
            self.model_option.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

            # News / Fundamentals Input
            self.news_label = ctk.CTkLabel(self, text="Fundamental News / Context:", font=("Roboto", 16))
            self.news_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
            
            self.news_textbox = ctk.CTkTextbox(self, height=80)
            self.news_textbox.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

            # Analyze Button
            self.analyze_button = ctk.CTkButton(self, text="Analyze Market", command=self.start_analysis, font=("Roboto", 16, "bold"), height=40)
            self.analyze_button.grid(row=4, column=0, padx=20, pady=20)

            # Output Area - Changed to Textbox for richer data
            self.output_frame = ctk.CTkFrame(self)
            self.output_frame.grid(row=5, column=0, padx=20, pady=20, sticky="nsew")
            self.output_frame.grid_columnconfigure(0, weight=1)
            self.output_frame.grid_rowconfigure(1, weight=1)
            
            self.result_title = ctk.CTkLabel(self.output_frame, text="Analysis Report", font=("Roboto", 18, "bold"))
            self.result_title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

            # Using a Textbox instead of Label for scrollable, detailed results
            self.result_box = ctk.CTkTextbox(self.output_frame, font=("Consolas", 14), wrap="word")
            self.result_box.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            self.result_box.insert("0.0", "Ready to analyze...")
            self.result_box.configure(state="disabled")

            # Chart Frame (Column 1)
            self.chart_frame = ctk.CTkFrame(self)
            self.chart_frame.grid(row=1, column=1, rowspan=5, padx=20, pady=10, sticky="nsew")
            self.chart_frame.grid_columnconfigure(0, weight=1)
            self.chart_frame.grid_rowconfigure(0, weight=1)
            
            self.chart_label = ctk.CTkLabel(self.chart_frame, text="Market Chart will appear here after analysis", font=("Roboto", 14))
            self.chart_label.grid(row=0, column=0)
            self.last_df = None

        except Exception as e:
            self.logger.exception(f"Error initializing UI: {e}")

    def start_analysis(self):
        try:
            self.logger.info("Start analysis button clicked")
            self.analyze_button.configure(state="disabled", text="Analyzing...")
            
            self.result_box.configure(state="normal")
            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", "1. Fetching Market Data...\n")
            self.result_box.configure(state="disabled")
            
            threading.Thread(target=self.run_analysis, daemon=True).start()
        except Exception as e:
             self.logger.exception(f"Error starting analysis: {e}")

    def update_models(self, provider):
        models = []
        if provider == "Gemini":
            models = ["gemini-2.0-flash-exp", "gemini-1.5-flash"]
        elif provider == "Cerebras":
            models = ["llama3.1-70b", "llama3.1-8b"]
        elif provider == "Groq":
            models = ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
        elif provider == "OpenRouter":
            models = ["stepfun/step-3.5-flash:free", "google/gemini-2.0-flash-lite-preview-02-05:free"]
        
        self.model_option.configure(values=models)
        if models:
            self.model_option.set(models[0])

    def run_analysis(self):
        try:
            symbol = self.symbol_option.get()
            timeframe = self.timeframe_option.get()
            news = self.news_textbox.get("1.0", "end").strip()
            
            # 1. Fetch Data
            df, error = self.data_provider.fetch_data(symbol, timeframe)
            if error:
                self.after(0, lambda: self.update_ui_error(f"Error fetching data: {error}"))
                return
            
            self.last_df = df # Store for charting
            
            # 2. Calculate Indicators
            df = self.data_provider.calculate_indicators(df)
            
            # 3. Fetch Automated News & Economic Calendar
            self.after(0, lambda: self.update_ui_status("2. Fetching Automated News & Calendar...\n"))
            auto_news = self.news_service.fetch_news(symbol)
            calendar = self.news_service.fetch_economic_calendar(symbol)
            
            # Combine with manual context if any
            manual_news = self.news_textbox.get("1.0", "end").strip()
            total_news_context = f"{manual_news}\n\n{auto_news}" if manual_news else auto_news

            # 4. Generate Prompt AND Get Technical Data
            # Note: generate_prompt now returns a tuple (prompt, details)
            prompt, tech_details = self.ai_trader.generate_prompt(
                df, symbol, 
                news_context=total_news_context, 
                calendar_context=calendar
            )
            
            # Update UI to show we are consulting AI
            self.after(0, lambda: self.update_ui_status("3. Consulting AI Model...\n"))
            
            # 4. Call AI
            provider = self.provider_option.get()
            model = self.model_option.get()
            response = self.ai_trader.analyze(prompt, provider=provider, model=model)
            
            if "error" in response:
                self.after(0, lambda: self.update_ui_error(f"AI Error: {response['error']}"))
                return
                
            # 5. Show Results (Pass both AI response and Tech Details)
            self.after(0, lambda: self.update_ui_result(response, tech_details))
            
            # 6. Render Chart
            self.after(0, lambda: self.render_chart(response))
            
        except Exception as e:
            self.logger.exception(f"Unexpected Error in run_analysis: {str(e)}")
            self.after(0, lambda: self.update_ui_error(f"Unexpected Error: {str(e)}"))

    def update_ui_status(self, message):
        self.result_box.configure(state="normal")
        self.result_box.insert("end", message)
        self.result_box.configure(state="disabled")

    def update_ui_error(self, message):
        self.result_box.configure(state="normal")
        self.result_box.insert("end", f"\nERROR: {message}\n")
        self.result_box.configure(state="disabled")
        self.analyze_button.configure(state="normal", text="Analyze Market")

    def update_ui_result(self, response, tech_details):
        try:
            self.logger.info("Updating UI with results")
            
            # Extract AI Data
            decision = response.get("decision", "N/A").upper()
            confidence = response.get("confidence_score", "N/A")
            entry = response.get("entry", "N/A")
            sl = response.get("stop_loss", "N/A")
            tp = response.get("take_profit", "N/A")
            tech_analysis = response.get("technical_analysis", "N/A")
            fund_analysis = response.get("fundamental_analysis", "N/A")
            reasoning = response.get("reasoning", "No reasoning provided.")

            # Extract Market Data
            current_price = tech_details.get("price", "N/A")
            rsi = tech_details.get("rsi", "N/A")
            atr = tech_details.get("atr", "N/A")
            trend = tech_details.get("trend", "N/A")

            # Construct the Report
            report = f"\n{'='*40}\n"
            report += f" DECISION: {decision} (Conf: {confidence}%)\n"
            report += f"{'='*40}\n\n"
            
            report += f"--- TRADE SETUP ---\n"
            report += f"Entry:      {entry}\n"
            report += f"Stop Loss:  {sl}\n"
            report += f"Take Profit:{tp}\n\n"
            
            report += f"--- MARKET DATA (What the AI saw) ---\n"
            report += f"Price: {current_price} | Trend: {trend}\n"
            report += f"RSI:   {rsi} (Momentum)\n"
            report += f"ATR:   {atr} (Volatility)\n\n"
            
            report += f"--- AI REASONING ---\n"
            report += f"Technical:  {tech_analysis}\n\n"
            report += f"Fundamental:{fund_analysis}\n\n"
            report += f"Conclusion: {reasoning}\n"

            self.result_box.configure(state="normal")
            self.result_box.delete("0.0", "end") # Clear loading text
            self.result_box.insert("0.0", report)
            self.result_box.configure(state="disabled")
            
            self.analyze_button.configure(text="Analyze Market", state="normal")
            
        except Exception as e:
             self.logger.exception(f"Error updating UI result: {e}")

    def render_chart(self, ai_response):
        """
        Uses ChartService to render the candlestick chart.
        """
        self.chart_service.create_chart(self.chart_frame, self.last_df, ai_response)

if __name__ == "__main__":
    try:
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        app = ForexApp()
        app.mainloop()
    except Exception as e:
        # Fallback logging if app crashes significantly
        import logging
        logging.basicConfig(filename='app.log', level=logging.ERROR)
        logging.exception("Fatal Application Error")

