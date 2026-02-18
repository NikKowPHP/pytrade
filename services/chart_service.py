import mplfinance as mpf
import io
import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from services.logger import Logger

class ChartService:
    def __init__(self):
        self.logger = Logger()
        self.style = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='', facecolor='#2b2b2b', edgecolor='#404040')
        self.template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "chart.html")

    def create_chart_figure(self, df, ai_results=None):
        """
        Creates the Matplotlib Figure for the candle chart (legacy/backup).
        """
        try:
            if df is None or df.empty:
                return None

            plot_df = df.tail(100)
            
            # Logic to determine lines
            hlines_list = []
            colors = []
            
            if ai_results and ai_results.get("decision") != "WAIT":
                try:
                    entry = ai_results.get("entry")
                    sl = ai_results.get("stop_loss")
                    tp = ai_results.get("take_profit")

                    # Helper to check validity
                    def is_valid(val): return val and val != "N/A" and isinstance(val, (int, float))

                    if is_valid(entry): 
                        hlines_list.append(float(entry))
                        colors.append('blue')
                    if is_valid(sl): 
                        hlines_list.append(float(sl))
                        colors.append('red')
                    if is_valid(tp): 
                        hlines_list.append(float(tp))
                        colors.append('green')
                except Exception:
                    pass # Ignore parsing errors for lines

            plot_kwargs = dict(
                type='candle',
                style=self.style,
                returnfig=True,
                figsize=(8, 5),
                tight_layout=True,
                datetime_format='%m-%d %H:%M',
                volume=True,
                show_nontrading=False
            )
            
            if hlines_list:
                plot_kwargs['hlines'] = dict(hlines=hlines_list, colors=colors, linestyle='-.', linewidths=2)

            fig, axlist = mpf.plot(plot_df, **plot_kwargs)
            return fig

        except Exception as e:
            self.logger.error(f"Error creating chart figure: {e}")
            return None

    def get_chart_html(self, df, ai_results=None):
        """
        Generates HTML content for TradingView Lightweight Charts.
        """
        try:
            self.logger.info(f"Generating chart HTML for {len(df)} candles")
            if df is None or df.empty:
                self.logger.warning("Empty dataframe provided to get_chart_html")
                return "<html><body>No Data</body></html>"

            # Prepare OHLC Data
            chart_data = []
            volume_data = []
            
            # TV charts want time in seconds (unix)
            for timestamp, row in df.iterrows():
                t = int(timestamp.timestamp())
                chart_data.append({
                    "time": t,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close'])
                })
                
                color = '#26a69a' if row['Close'] >= row['Open'] else '#ef5350'
                volume_data.append({
                    "time": t,
                    "value": float(row['Volume']),
                    "color": color
                })

            # Prepare AI Levels
            ai_levels = {
                "entry": None,
                "sl": None,
                "tp": None
            }
            if ai_results:
                try:
                    def safe_float(val):
                        if val is None or val == "N/A": return None
                        return float(val)
                    
                    ai_levels["entry"] = safe_float(ai_results.get("entry"))
                    ai_levels["sl"] = safe_float(ai_results.get("stop_loss"))
                    ai_levels["tp"] = safe_float(ai_results.get("take_profit"))
                except (ValueError, TypeError):
                    pass

            # Read template
            self.logger.info(f"Loading chart template from {self.template_path}")
            with open(self.template_path, "r") as f:
                template = f.read()

            # Inject Data
            self.logger.info("Injecting data into template")
            html = template.replace("{{ CHART_DATA }}", json.dumps(chart_data))
            html = html.replace("{{ VOLUME_DATA }}", json.dumps(volume_data))
            html = html.replace("{{ AI_LEVELS }}", json.dumps(ai_levels))

            self.logger.info(f"HTML generation complete, size: {len(html)} chars")
            return html

        except Exception as e:
            self.logger.error(f"Error generating chart HTML: {e}")
            return f"<html><body>Error: {str(e)}</body></html>"
            
    def generate_chart_image(self, df):
        """
        Generates a PNG image of the chart in memory for AI consumption.
        """
        try:
            if df is None or df.empty:
                return None
            
            # Simple clean chart for AI (last 100 candles)
            plot_df = df.tail(100)
            
            # We use a specific style to make it clear for vision models
            fig, _ = mpf.plot(
                plot_df, 
                type='candle', 
                style='charles', 
                volume=True, 
                returnfig=True, 
                figsize=(10, 6),
                tight_layout=True,
                axisoff=False # AI needs to see the axis numbers
            )
            
            # Save to buffer
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            fig.clf() # Clear to free memory without closing the figure manager
            plt.close(fig)
            
            # Convert to PIL Image (standard for many SDKs)
            return Image.open(buf)

        except Exception as e:
            self.logger.error(f"Error generating chart image: {e}")
            return None
