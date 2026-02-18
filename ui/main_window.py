import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.controller = None # Injected later
        
        # Window Setup
        self.title("AI Forex Swing Assistant - Professional Edition")
        self.geometry("1200x900")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Layout Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header
        self.header_label = ctk.CTkLabel(self, text="AI Forex Professional Analysis", font=("Roboto", 24, "bold"))
        self.header_label.grid(row=0, column=0, pady=(10, 5), sticky="ew")

        # 2. TabView
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Dashboard")
        self.tab_view.add("Journal")
        self.tab_view.add("Stats") # NEW TAB
        
        # --- DASHBOARD TAB ---
        self.dashboard = self.tab_view.tab("Dashboard")
        self.dashboard.grid_columnconfigure(0, weight=1) 
        self.dashboard.grid_rowconfigure(1, weight=1)

        # --- JOURNAL TAB ---
        self.journal_tab = self.tab_view.tab("Journal")
        self.journal_tab.grid_columnconfigure(0, weight=1)
        self.journal_tab.grid_rowconfigure(0, weight=1)
        self.create_journal_tab()

        # --- STATS TAB ---
        self.create_stats_tab()

        # 4. Content Area (Scanner + Analysis + Chart)
        self.create_content_area()

    def set_controller(self, controller):
        self.controller = controller
        # Trigger initial load once controller is linked
        self.after(500, self.controller.on_startup)

    def create_content_area(self):
        # Split: [Scanner List (Left)] -- [Controls/Analysis (Center)] -- [Chart (Right)]
        # Re-adjusting grid weights
        self.dashboard.grid_columnconfigure(0, weight=0) # Scanner
        self.dashboard.grid_columnconfigure(1, weight=1) # Analysis
        self.dashboard.grid_columnconfigure(2, weight=3) # Chart
        self.dashboard.grid_rowconfigure(0, weight=1)

        # 1. SCANNER SIDEBAR
        self.scanner_frame = ctk.CTkFrame(self.dashboard, width=220, corner_radius=0)
        self.scanner_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        
        ctk.CTkLabel(self.scanner_frame, text="Market Scanner", font=("Roboto", 18, "bold")).pack(pady=10)
        self.scan_btn = ctk.CTkButton(self.scanner_frame, text="Scan All Pairs", command=self.on_scan_click, fg_color="#2B823A", hover_color="#21632C")
        self.scan_btn.pack(pady=5, padx=10, fill="x")
        
        # Scrollable area for results
        self.scan_results = ctk.CTkScrollableFrame(self.scanner_frame)
        self.scan_results.pack(fill="both", expand=True, padx=5, pady=5)

        # 2. ANALYSIS INPUTS (Middle Column)
        self.input_panel = ctk.CTkFrame(self.dashboard)
        self.input_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.input_panel, text="Control Panel", font=("Roboto", 18, "bold")).pack(pady=10)
        
        # Symbol Selection
        row_sym = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        row_sym.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_sym, text="Symbol:", font=("Roboto", 12)).pack(side="left")
        self.symbol_var = ctk.StringVar(value="EURUSD")
        self.pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "XAUUSD"]
        self.symbol_option = ctk.CTkOptionMenu(row_sym, values=self.pairs, variable=self.symbol_var, width=120)
        self.symbol_option.pack(side="right")

        # Timeframe
        row_tf = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        row_tf.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_tf, text="Timeframe:", font=("Roboto", 12)).pack(side="left")
        self.timeframe_var = ctk.StringVar(value="1d")
        self.timeframe_option = ctk.CTkOptionMenu(row_tf, values=["1h", "4h", "1d"], variable=self.timeframe_var, width=120)
        self.timeframe_option.pack(side="right")

        # Provider
        row_prov = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        row_prov.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_prov, text="AI Provider:", font=("Roboto", 12)).pack(side="left")
        self.provider_var = ctk.StringVar(value="Gemini")
        self.provider_option = ctk.CTkOptionMenu(
            row_prov, 
            values=["Gemini", "Cerebras", "Groq", "OpenRouter"], 
            variable=self.provider_var, 
            command=self.on_provider_change,
            width=120
        )
        self.provider_option.pack(side="right")

        # Model
        row_mod = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        row_mod.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_mod, text="Model/Model:", font=("Roboto", 12)).pack(side="left")
        self.model_var = ctk.StringVar(value="gemini-2.0-flash-exp")
        self.model_option = ctk.CTkOptionMenu(row_mod, values=["gemini-2.0-flash-exp"], variable=self.model_var, width=120)
        self.model_option.pack(side="right")

        # Strategy (New)
        row_strat = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        row_strat.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row_strat, text="Strategy:", font=("Roboto", 12)).pack(side="left")
        self.strategy_var = ctk.StringVar(value="Trend Following")
        self.strategy_option = ctk.CTkOptionMenu(
            row_strat, 
            values=["Trend Following", "Reversal", "Breakout"], 
            variable=self.strategy_var,
            width=120
        )
        self.strategy_option.pack(side="right")

        # News Box
        ctk.CTkLabel(self.input_panel, text="Fundamental Context:", font=("Roboto", 13, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.news_textbox = ctk.CTkTextbox(self.input_panel, height=80)
        self.news_textbox.pack(fill="x", padx=10, pady=5)

        # Analyze Button
        self.analyze_btn = ctk.CTkButton(self.input_panel, text="Full AI Analysis", command=self.on_analyze_click, font=("Roboto", 15, "bold"), height=35)
        self.analyze_btn.pack(pady=10, padx=10, fill="x")

        # NEW: Save Button (Initially disabled)
        self.save_btn = ctk.CTkButton(self.input_panel, text="Save to Journal", command=self.on_save_click, fg_color="#555555", state="disabled")
        self.save_btn.pack(pady=(0, 10), padx=10, fill="x")

        # Report Box
        ctk.CTkLabel(self.input_panel, text="Analysis Report:", font=("Roboto", 13, "bold")).pack(padx=10, anchor="w")
        self.result_box = ctk.CTkTextbox(self.input_panel, font=("Consolas", 12), wrap="word")
        self.result_box.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.result_box.configure(state="disabled")

        # 3. CHART AREA (Right Column)
        self.chart_frame = ctk.CTkFrame(self.dashboard)
        self.chart_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)
        
        self.chart_placeholder = ctk.CTkLabel(self.chart_frame, text="Select a pair to load chart", font=("Roboto", 14))
        self.chart_placeholder.grid(row=0, column=0)

    # --- View Actions ---
    def on_provider_change(self, provider):
        if self.controller:
            models = self.controller.get_models_for_provider(provider)
            self.model_option.configure(values=models)
            if models: self.model_var.set(models[0])

    def on_analyze_click(self):
        if self.controller:
            self.analyze_btn.configure(state="disabled", text="Analyzing...")
            self.controller.start_analysis()

    # --- Public Update Methods ---
    def get_inputs(self):
        return {
            "symbol": self.symbol_var.get(),
            "timeframe": self.timeframe_var.get(),
            "provider": self.provider_var.get(),
            "model": self.model_var.get(),
            "strategy": self.strategy_var.get(), # NEW
            "news_context": self.news_textbox.get("1.0", "end").strip()
        }

    def update_status(self, message):
        self.result_box.configure(state="normal")
        self.result_box.delete("0.0", "end")
        self.result_box.insert("0.0", message)
        self.result_box.configure(state="disabled")

    def append_status(self, message):
        self.result_box.configure(state="normal")
        self.result_box.insert("end", message)
        self.result_box.configure(state="disabled")

    def on_scan_click(self):
        if self.controller:
            self.scan_btn.configure(state="disabled", text="Scanning...")
            # Clear previous
            for widget in self.scan_results.winfo_children():
                widget.destroy()
            self.controller.run_market_scan()

    def add_scan_result(self, result):
        """
        Adds a button to the list.
        result = {'symbol': 'EURUSD', 'signal': 'OVERSOLD', 'score': 8, 'details': 'RSI 25.0'}
        """
        frame = ctk.CTkFrame(self.scan_results)
        frame.pack(fill="x", pady=2)
        
        # Color code based on signal
        color = "#C0392B" if "OVER" in result['signal'] else "#27AE60"
        if "EMA" in result['signal']: color = "#F39C12"

        btn = ctk.CTkButton(
            frame, 
            text=f"{result['symbol']}\n{result['signal']}\n{result['details']}", 
            fg_color=color,
            hover_color=color, # Keep it colored
            command=lambda s=result['symbol']: self.controller.load_symbol(s)
        )
        btn.pack(fill="x")
        
    def reset_scan_button(self):
        self.scan_btn.configure(state="normal", text="Scan All Pairs")

    def display_report(self, report):
        self.update_status(report)
        self.analyze_btn.configure(state="normal", text="Full AI Analysis")

    def display_error(self, message):
        self.append_status(f"\nERROR: {message}\n")
        self.analyze_btn.configure(state="normal", text="Full AI Analysis")

    def embed_chart(self, fig):
        # Clear previous
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def create_journal_tab(self):
        # Refresh Button
        self.refresh_btn = ctk.CTkButton(self.journal_tab, text="Refresh History", command=self.on_refresh_journal)
        self.refresh_btn.pack(pady=10, anchor="w", padx=20)

        # Header Frame
        header = ctk.CTkFrame(self.journal_tab, height=40)
        header.pack(fill="x", padx=10)
        columns = ["Time", "Symbol", "Decision", "Conf", "Entry", "SL", "TP"]
        widths = [150, 80, 80, 60, 80, 80, 80]
        
        for i, col in enumerate(columns):
            lbl = ctk.CTkLabel(header, text=col, font=("Roboto", 12, "bold"), width=widths[i])
            lbl.pack(side="left", padx=2)

        # Scrollable Data Area
        self.journal_list = ctk.CTkScrollableFrame(self.journal_tab)
        self.journal_list.pack(fill="both", expand=True, padx=10, pady=10)

    def on_save_click(self):
        if self.controller:
            self.controller.save_current_analysis()

    def on_refresh_journal(self):
        if self.controller:
            self.controller.load_journal_data()

    def populate_journal(self, rows):
        # Clear list
        for widget in self.journal_list.winfo_children():
            widget.destroy()

        widths = [150, 80, 80, 60, 80, 80, 80]
        colors = {"BUY": "#27AE60", "SELL": "#C0392B", "WAIT": "#7F8C8D"}

        for row in rows:
            # row: id, timestamp, symbol, decision, confidence, entry, sl, tp
            row_frame = ctk.CTkFrame(self.journal_list)
            row_frame.pack(fill="x", pady=2)
            
            # Determine color based on decision
            decision = row[3]
            color = colors.get(decision, "gray")

            data = [
                str(row[1])[:16], # Time
                row[2], # Symbol
                decision,
                f"{row[4]}%", # Conf
                str(row[5]), # Entry
                str(row[6]), # SL
                str(row[7])  # TP
            ]

            for i, text in enumerate(data):
                lbl = ctk.CTkLabel(row_frame, text=text, width=widths[i])
                if i == 2: # Color the Decision column
                    lbl.configure(text_color=color, font=("Roboto", 12, "bold"))
                lbl.pack(side="left", padx=2)

    def create_stats_tab(self):
        self.stats_tab = self.tab_view.tab("Stats")
        
        self.stats_container = ctk.CTkFrame(self.stats_tab)
        self.stats_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.win_rate_lbl = ctk.CTkLabel(self.stats_container, text="Win Rate: --%", font=("Roboto", 24, "bold"))
        self.win_rate_lbl.pack(pady=20)
        
        self.model_box = ctk.CTkTextbox(self.stats_container, font=("Consolas", 14))
        self.model_box.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkButton(self.stats_tab, text="Refresh Statistics", command=lambda: self.controller.update_stats()).pack(pady=10)

    def update_stats_display(self, stats):
        outcomes = stats.get("outcomes", {})
        wins = outcomes.get("WIN", 0)
        losses = outcomes.get("LOSS", 0)
        total = wins + losses
        
        wr = (wins / total * 100) if total > 0 else 0
        self.win_rate_lbl.configure(text=f"Win Rate: {wr:.1f}% ({wins}W / {losses}L)")
        
        # Model Breakdown
        model_text = "MODEL PERFORMANCE BREAKDOWN:\n" + "="*30 + "\n"
        for m in stats.get("models", []):
            m_total = m[1] + m[2]
            m_wr = (m[1] / m_total * 100) if m_total > 0 else 0
            model_text += f"{m[0]:<15} | WR: {m_wr:>5.1f}% | Total: {m_total}\n"
        
        self.model_box.configure(state="normal")
        self.model_box.delete("0.0", "end")
        self.model_box.insert("0.0", model_text)
        self.model_box.configure(state="disabled")
