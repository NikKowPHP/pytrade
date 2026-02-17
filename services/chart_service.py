import mplfinance as mpf
from services.logger import Logger

class ChartService:
    def __init__(self):
        self.logger = Logger()
        self.style = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='', facecolor='#2b2b2b', edgecolor='#404040')

    def create_chart_figure(self, df, ai_results=None):
        """
        Creates the Matplotlib Figure for the candle chart.
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
