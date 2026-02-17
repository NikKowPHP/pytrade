import customtkinter as ctk
import threading
from backend import ForexAnalyzer

class ForexApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Forex Swing Assistant")
        self.geometry("600x700")
        
        # Initialize Backend
        self.analyzer = ForexAnalyzer()

        # Layout Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1) # Output area expands

        # Header
        self.header_label = ctk.CTkLabel(self, text="AI Forex Swing Analysis", font=("Roboto", 24, "bold"))
        self.header_label.grid(row=0, column=0, padx=20, pady=20)

        # Inputs Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        # Symbol Input
        self.symbol_label = ctk.CTkLabel(self.input_frame, text="Symbol (e.g., EURUSD):")
        self.symbol_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.symbol_entry = ctk.CTkEntry(self.input_frame, placeholder_text="EURUSD")
        self.symbol_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Timeframe Input
        self.timeframe_label = ctk.CTkLabel(self.input_frame, text="Timeframe:")
        self.timeframe_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.timeframe_option = ctk.CTkOptionMenu(self.input_frame, values=["1h", "4h", "1d"])
        self.timeframe_option.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.timeframe_option.set("4h")

        # Candle Count (Not strictly used for fetching but good for user intent, 
        # we can use it to slice the display if we were showing a chart, 
        # or just passed to context if needed. For now just UI.)
        self.candles_label = ctk.CTkLabel(self.input_frame, text="Candles to Analyze:")
        self.candles_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.candles_entry = ctk.CTkEntry(self.input_frame, placeholder_text="100")
        self.candles_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.candles_entry.insert(0, "100")

        # News / Fundamentals Input
        self.news_label = ctk.CTkLabel(self, text="Fundamental News / Context:", font=("Roboto", 16))
        self.news_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.news_textbox = ctk.CTkTextbox(self, height=100)
        self.news_textbox.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Analyze Button
        self.analyze_button = ctk.CTkButton(self, text="Analyze Market", command=self.start_analysis)
        self.analyze_button.grid(row=4, column=0, padx=20, pady=20)

        # Output Area
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=5, column=0, padx=20, pady=20, sticky="nsew")
        self.output_frame.grid_columnconfigure(0, weight=1)
        
        self.result_label = ctk.CTkLabel(self.output_frame, text="Analysis Results will appear here...", justify="left", font=("Roboto", 14),wraplength=500)
        self.result_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

    def start_analysis(self):
        # Disable button to prevent double clicks
        self.analyze_button.configure(state="disabled", text="Analyzing...")
        self.result_label.configure(text="Fetching data and consulting AI...")
        
        # Run in thread to not freeze GUI
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def run_analysis(self):
        try:
            symbol = self.symbol_entry.get().strip().upper()
            timeframe = self.timeframe_option.get()
            news = self.news_textbox.get("1.0", "end").strip()
            
            if not symbol:
                self.after(0, lambda: self.update_ui_error("Please enter a symbol."))
                return

            # 1. Fetch Data
            df, error = self.analyzer.fetch_data(symbol, "1mo", timeframe)
            if error:
                self.after(0, lambda: self.update_ui_error(f"Error fetching data: {error}"))
                return
            
            # 2. Calculate Indicators
            df = self.analyzer.calculate_indicators(df)
            
            # 3. Generate Prompt
            prompt = self.analyzer.generate_prompt(df, news, symbol)
            
            # 4. Call Gemini
            response = self.analyzer.analyze_with_gemini(prompt)
            
            if "error" in response:
                self.after(0, lambda: self.update_ui_error(f"AI Error: {response['error']}"))
                return
                
            # 5. Show Results
            self.after(0, lambda: self.update_ui_result(response))
            
        except Exception as e:
            self.after(0, lambda: self.update_ui_error(f"Unexpected Error: {str(e)}"))

    def update_ui_error(self, message):
        self.result_label.configure(text=message, text_color="red")
        self.analyze_button.configure(state="normal", text="Analyze Market")

    def update_ui_result(self, response):
        decision = response.get("decision", "N/A").upper()
        entry = response.get("entry", "N/A")
        sl = response.get("stop_loss", "N/A")
        tp = response.get("take_profit", "N/A")
        reasoning = response.get("reasoning", "No reasoning provided.")
        
        # Color coding
        color = "white"
        if decision == "BUY":
            color = "green" # CustomTkinter might need specific color codes or names, 'green' works usually
        elif decision == "SELL":
             color = "red"
        
        text = f"Decision: {decision}\n\n" \
               f"Entry: {entry}\n" \
               f"Stop Loss: {sl}\n" \
               f"Take Profit: {tp}\n\n" \
               f"Reasoning: {reasoning}"
        
        self.result_label.configure(text=text, text_color=color)
        self.analyze_button.configure(text="Analyze Market", state="normal")

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = ForexApp()
    app.mainloop()
