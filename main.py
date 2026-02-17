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
        self.geometry("1200x900") # Increased width slightly for better layout
        
        try:
            # Initialize Services
            self.data_provider = MarketDataProvider()
            self.ai_trader = AITrader()
            self.news_service = NewsService()
            self.chart_service = ChartService()

            # --- MAIN LAYOUT CONFIGURATION ---
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(1, weight=1) # Make row 1 (TabView) expand

            # 1. Header (Top of Window)
            self.header_label = ctk.CTkLabel(self, text="AI Forex Professional Analysis", font=("Roboto", 24, "bold"))
            self.header_label.grid(row=0, column=0, pady=(10, 5), sticky="ew")

            # 2. TabView Container
            self.tab_view = ctk.CTkTabview(self)
            self.tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            self.tab_view.add("Dashboard")
            
            # --- DASHBOARD TAB LAYOUT ---
            self.dashboard = self.tab_view.tab("Dashboard")
            self.dashboard.grid_columnconfigure(0, weight=1) 
            self.dashboard.grid_rowconfigure(1, weight=1) # Content area expands

            # 3. Top Tools Frame (Horizontal Bar)
            self.tools_frame = ctk.CTkFrame(self.dashboard, fg_color="transparent")
            self.tools_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
            
            # Tools: Symbol
            self.symbol_label = ctk.CTkLabel(self.tools_frame, text="Symbol:", font=("Roboto", 14, "bold"))
            self.symbol_label.pack(side="left", padx=(10, 5))
            
            self.pairs = [
                "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
                "EURGBP", "EURJPY", "GBPJPY", "XAUUSD"
            ]
            self.symbol_option = ctk.CTkOptionMenu(self.tools_frame, values=self.pairs, width=120)
            self.symbol_option.pack(side="left", padx=5)
            self.symbol_option.set("EURUSD")

            # Tools: Timeframe
            self.timeframe_label = ctk.CTkLabel(self.tools_frame, text="Timeframe:", font=("Roboto", 14, "bold"))
            self.timeframe_label.pack(side="left", padx=(20, 5))
            
            self.timeframe_option = ctk.CTkOptionMenu(self.tools_frame, values=["1h", "4h", "1d"], width=80)
            self.timeframe_option.pack(side="left", padx=5)
            self.timeframe_option.set("1d")

            # Tools: Provider
            self.provider_label = ctk.CTkLabel(self.tools_frame, text="AI Provider:", font=("Roboto", 14, "bold"))
            self.provider_label.pack(side="left", padx=(20, 5))
            
            self.provider_option = ctk.CTkOptionMenu(self.tools_frame, values=["Gemini", "Cerebras", "Groq", "OpenRouter"], command=self.update_models, width=120)
            self.provider_option.pack(side="left", padx=5)
            self.provider_option.set("Gemini")

            # Tools: Model
            self.model_label = ctk.CTkLabel(self.tools_frame, text="Model:", font=("Roboto", 14, "bold"))
            self.model_label.pack(side="left", padx=(20, 5))
            
            self.model_option = ctk.CTkOptionMenu(self.tools_frame, values=["gemini-2.0-flash-exp"], width=200)
            self.model_option.pack(side="left", padx=5)

            # 4. Content Split (Left: Sidebar, Right: Chart)
            self.content_split = ctk.CTkFrame(self.dashboard, fg_color="transparent")
            self.content_split.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
            
            self.content_split.grid_columnconfigure(0, weight=1) # Sidebar
            self.content_split.grid_columnconfigure(1, weight=3) # Chart Area
            self.content_split.grid_rowconfigure(0, weight=1)

            # --- Left Sidebar (News Input & Results) ---
            self.sidebar_frame = ctk.CTkFrame(self.content_split)
            self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
            self.sidebar_frame.grid_columnconfigure(0, weight=1)
            self.sidebar_frame.grid_rowconfigure(4, weight=1) # Result box expands

            # News Input
            self.news_label = ctk.CTkLabel(self.sidebar_frame, text="Fundamental Context:", font=("Roboto", 14, "bold"))
            self.news_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
            
            self.news_textbox = ctk.CTkTextbox(self.sidebar_frame, height=100)
            self.news_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

            # Analyze Button
            self.analyze_button = ctk.CTkButton(self.sidebar_frame, text="Analyze Market", command=self.start_analysis, font=("Roboto", 16, "bold"), height=40)
            self.analyze_button.grid(row=2, column=0, padx=10, pady=15, sticky="ew")

            # Output Area
            self.result_title = ctk.CTkLabel(self.sidebar_frame, text="Analysis Report:", font=("Roboto", 14, "bold"))
            self.result_title.grid(row=3, column=0, padx=10, pady=(5,0), sticky="nw")

            self.result_box = ctk.CTkTextbox(self.sidebar_frame, font=("Consolas", 13), wrap="word")
            self.result_box.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
            self.result_box.insert("0.0", "Ready to analyze...")
            self.result_box.configure(state="disabled")

            # --- Right Chart Area ---
            self.chart_frame = ctk.CTkFrame(self.content_split)
            self.chart_frame.grid(row=0, column=1, sticky="nsew")
            # Grid config for chart frame to allow canvas to expand
            self.chart_frame.grid_columnconfigure(0, weight=1)
            self.chart_frame.grid_rowconfigure(0, weight=1)
            
            self.chart_label = ctk.CTkLabel(self.chart_frame, text="Market Chart will appear here after analysis", font=("Roboto", 14))
            self.chart_label.grid(row=0, column=0)
            
            self.last_df = None
            
            # CHANGE: Trigger initial data load on startup
            self.after(500, self.start_initial_load)

        except Exception as e:
            self.logger.exception(f"Error initializing UI: {e}")

    # NEW METHODS ADDED HERE
    def start_initial_load(self):
        """Starts the background thread to load the chart immediately."""
        threading.Thread(target=self.load_initial_chart, daemon=True).start()

    def load_initial_chart(self):
        """Fetches data and renders chart without triggering full AI analysis."""
        try:
            symbol = self.symbol_option.get()
            timeframe = self.timeframe_option.get()
            
            self.after(0, lambda: self.update_ui_status(f"Startup: Fetching latest data for {symbol} ({timeframe})..."))

            # 1. Fetch Data (Updates Local DB)
            df, error = self.data_provider.fetch_data(symbol, timeframe)
            if error:
                self.after(0, lambda: self.update_ui_error(f"Startup Data Error: {error}"))
                return
            
            self.last_df = df
            
            # 2. Calculate Indicators (needed for chart if we plot them later, or just to have ready)
            df = self.data_provider.calculate_indicators(df)
            
            # 3. Render Chart (Pass None for ai_results)
            self.after(0, lambda: self.chart_service.create_chart(self.chart_frame, df, None))
            self.after(0, lambda: self.update_ui_status(f"Ready. Data for {symbol} ({timeframe}) is up to date."))
            
        except Exception as e:
            self.logger.exception(f"Error in load_initial_chart: {e}")
            self.after(0, lambda: self.update_ui_error(f"Startup Error: {str(e)}"))

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

