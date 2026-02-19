from datetime import datetime
import calendar

class SeasonalityService:
    def __init__(self):
        # 1. Define Seasonality Rules (Month-based)
        # Format: "Month": {"Asset": "Direction", ...}
        self.MONTHLY_SEASONALITY = {
            "January": {
                "DXY": "Bullish (New Year Inflows)",
                "EURUSD": "Bearish",
                "XAUUSD": "Bullish (Chinese New Year Demand)"
            },
            "September": {
                "SPY": "Bearish (Historically Worst Month)",
                "AUDUSD": "Bearish (Risk Off)",
                "NZDUSD": "Bearish (Risk Off)"
            },
            "October": {
                "SPY": "Bullish (Pre-Holiday Rally)",
                "DXY": "Bearish"
            },
            "December": {
                "XAUUSD": "Bullish (Santa Rally)",
                "SPY": "Bullish (Santa Rally)"
            }
        }

        # 2. Define Day-of-Week Probabilities
        self.WEEKLY_SEASONALITY = {
            "Monday": "Uncertainty / Fake Moves. Often sets the low/high of the week (20% prob).",
            "Tuesday": "Turnaround Tuesday. High probability of reversal from Monday's move.",
            "Wednesday": "Mid-week trend continuation or consolidation.",
            "Thursday": "Pre-NFP positioning (if end of month) or trend continuation.",
            "Friday": "Profit Taking. Reversals common after 16:00 UTC."
        }

    def get_seasonality_report(self, symbol, date=None):
        """
        Returns a text report, confidence modifier, and instruction.
        """
        if date is None:
            date = datetime.now()
        
        month_name = date.strftime("%B")
        day_name = date.strftime("%A")
        
        report_text = f"**SEASONALITY REPORT ({month_name}, {day_name})**\n"
        instruction = "Check Seasonality."
        modifier = 0

        # 1. Check Monthly Seasonality
        monthly_bias = self.MONTHLY_SEASONALITY.get(month_name, {}).get(symbol)
        if not monthly_bias:
            # Check broad market correlations if specific symbol not found
            if "USD" in symbol and symbol != "XAUUSD": # rough check
                 # If DXY has a bias, apply inverse to USD pairs
                 dxy_bias = self.MONTHLY_SEASONALITY.get(month_name, {}).get("DXY")
                 if dxy_bias:
                     monthly_bias = f"Inverse of DXY: {dxy_bias}"

        if monthly_bias:
            report_text += f"- **Monthly Bias:** {monthly_bias}\n"
            if "Bearish" in monthly_bias:
                instruction = "Reduce confidence on BUY signals."
                modifier = -10
            elif "Bullish" in monthly_bias:
                 instruction = "Reduce confidence on SELL signals."
                 modifier = -10
        else:
            report_text += "- **Monthly Bias:** Neutral / No Data\n"

        # 2. Check Weekly Seasonality
        day_bias = self.WEEKLY_SEASONALITY.get(day_name, "Normal trading day.")
        report_text += f"- **Day Bias:** {day_bias}\n"

        # Special Logic for Turnaround Tuesday
        if day_name == "Tuesday":
            report_text += "- **Tip:** If Monday was a strong trend, look for a reversal today.\n"

        # Special Logic for Friday
        if day_name == "Friday":
            report_text += "- **Tip:** Avoid holding new trades over the weekend (Gap Risk).\n"
            modifier -= 5

        return {
            "report_text": report_text,
            "modifier": modifier,
            "instruction": instruction
        }
