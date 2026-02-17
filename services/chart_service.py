import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from services.logger import Logger

class ChartService:
    def __init__(self):
        self.logger = Logger()
        # Use a dark theme for the charts to match your UI
        # 'charles' is a standard candle style, we can customize colors further if needed
        self.style = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='', facecolor='#2b2b2b', edgecolor='#404040')
        self.canvas = None

    def create_chart(self, parent_frame, df, ai_results=None):
        """
        Plots the candlestick chart and draws AI levels (Entry, SL, TP).
        """
        try:
            if df is None or df.empty:
                self.logger.warning("Empty dataframe provided to ChartService")
                return

            self.logger.info("Generating candlestick chart")

            # Clear any previous charts in the frame
            for widget in parent_frame.winfo_children():
                widget.destroy()

            # We only want to plot the last 100 candles for visibility
            plot_df = df.tail(100)

            # Prepare horizontal lines for AI levels
            hlines_list = []
            colors = []
            
            if ai_results and ai_results.get("decision") != "WAIT":
                # Ensure we handle strings or floats
                try:
                    entry = ai_results.get("entry")
                    sl = ai_results.get("stop_loss")
                    tp = ai_results.get("take_profit")

                    if entry and entry != "N/A": 
                        hlines_list.append(float(entry))
                        colors.append('blue') # Blue for Entry
                    if sl and sl != "N/A": 
                        hlines_list.append(float(sl))
                        colors.append('red')  # Red for Stop Loss
                    if tp and tp != "N/A": 
                        hlines_list.append(float(tp))
                        colors.append('green') # Green for Take Profit
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Error parsing AI levels for chart: {e}")

            hlines_config = None
            if hlines_list:
                hlines_config = dict(hlines=hlines_list, colors=colors, linestyle='-.', linewidths=2)

            # Create the figure
            fig, axlist = mpf.plot(
                plot_df,
                type='candle',
                style=self.style,
                hlines=hlines_config,
                returnfig=True,
                figsize=(8, 5),
                tight_layout=True,
                datetime_format='%m-%d %H:%M',
                volume=True,
                show_nontrading=False
            )

            # Embed into Tkinter
            self.canvas = FigureCanvasTkAgg(fig, master=parent_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            
            self.logger.info("Chart successfully embedded")

        except Exception as e:
            self.logger.exception(f"Critical error in ChartService.create_chart: {e}")
            import customtkinter as ctk
            error_label = ctk.CTkLabel(parent_frame, text=f"Chart Error: {str(e)}")
            error_label.pack(expand=True)
