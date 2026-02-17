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
        
        # --- DASHBOARD TAB ---
        self.dashboard = self.tab_view.tab("Dashboard")
        self.dashboard.grid_columnconfigure(0, weight=1) 
        self.dashboard.grid_rowconfigure(1, weight=1)

        # 3. Top Tools Bar
        self.create_top_bar()

        # 4. Content Area (Sidebar + Chart)
        self.create_content_area()

    def set_controller(self, controller):
        self.controller = controller
        # Trigger initial load once controller is linked
        self.after(500, self.controller.on_startup)

    def create_top_bar(self):
        self.tools_frame = ctk.CTkFrame(self.dashboard, fg_color="transparent")
        self.tools_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Symbol
        ctk.CTkLabel(self.tools_frame, text="Symbol:", font=("Roboto", 14, "bold")).pack(side="left", padx=(10, 5))
        self.symbol_var = ctk.StringVar(value="EURUSD")
        self.pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "XAUUSD"]
        self.symbol_option = ctk.CTkOptionMenu(self.tools_frame, values=self.pairs, variable=self.symbol_var, width=120)
        self.symbol_option.pack(side="left", padx=5)

        # Timeframe
        ctk.CTkLabel(self.tools_frame, text="Timeframe:", font=("Roboto", 14, "bold")).pack(side="left", padx=(20, 5))
        self.timeframe_var = ctk.StringVar(value="1d")
        self.timeframe_option = ctk.CTkOptionMenu(self.tools_frame, values=["1h", "4h", "1d"], variable=self.timeframe_var, width=80)
        self.timeframe_option.pack(side="left", padx=5)

        # Provider
        ctk.CTkLabel(self.tools_frame, text="AI Provider:", font=("Roboto", 14, "bold")).pack(side="left", padx=(20, 5))
        self.provider_var = ctk.StringVar(value="Gemini")
        self.provider_option = ctk.CTkOptionMenu(
            self.tools_frame, 
            values=["Gemini", "Cerebras", "Groq", "OpenRouter"], 
            variable=self.provider_var, 
            command=self.on_provider_change,
            width=120
        )
        self.provider_option.pack(side="left", padx=5)

        # Model
        ctk.CTkLabel(self.tools_frame, text="Model:", font=("Roboto", 14, "bold")).pack(side="left", padx=(20, 5))
        self.model_var = ctk.StringVar(value="gemini-2.0-flash-exp")
        self.model_option = ctk.CTkOptionMenu(self.tools_frame, values=["gemini-2.0-flash-exp"], variable=self.model_var, width=200)
        self.model_option.pack(side="left", padx=5)

    def create_content_area(self):
        self.content_split = ctk.CTkFrame(self.dashboard, fg_color="transparent")
        self.content_split.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_split.grid_columnconfigure(0, weight=1) # Sidebar
        self.content_split.grid_columnconfigure(1, weight=3) # Chart Area
        self.content_split.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self.content_split)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self.sidebar, text="Fundamental Context:", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.news_textbox = ctk.CTkTextbox(self.sidebar, height=100)
        self.news_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.analyze_btn = ctk.CTkButton(self.sidebar, text="Analyze Market", command=self.on_analyze_click, font=("Roboto", 16, "bold"), height=40)
        self.analyze_btn.grid(row=2, column=0, padx=10, pady=15, sticky="ew")

        ctk.CTkLabel(self.sidebar, text="Analysis Report:", font=("Roboto", 14, "bold")).grid(row=3, column=0, padx=10, pady=(5,0), sticky="nw")
        self.result_box = ctk.CTkTextbox(self.sidebar, font=("Consolas", 13), wrap="word")
        self.result_box.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.result_box.configure(state="disabled")

        # --- Chart Frame ---
        self.chart_frame = ctk.CTkFrame(self.content_split)
        self.chart_frame.grid(row=0, column=1, sticky="nsew")
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)
        
        self.chart_placeholder = ctk.CTkLabel(self.chart_frame, text="Chart loading...", font=("Roboto", 14))
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

    def display_report(self, report):
        self.update_status(report)
        self.analyze_btn.configure(state="normal", text="Analyze Market")

    def display_error(self, message):
        self.append_status(f"\nERROR: {message}\n")
        self.analyze_btn.configure(state="normal", text="Analyze Market")

    def embed_chart(self, fig):
        # Clear previous
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
