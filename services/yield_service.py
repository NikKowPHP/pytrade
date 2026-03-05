import yfinance as yf
from services.logger import Logger

class YieldService:
    def __init__(self):
        self.logger = Logger()
        # Roughly approximated current or recent central bank rates (hardcoded fallback if API fails)
        # In a generic implementation, this should be scraped or fetched, 
        # but yfinance doesn't easily provide pure central bank rates out of the box.
        # So we use Treasury/Bond yields as a proxy for the 'Risk-Free Rate'.
        
        self.yield_proxies = {
            "USD": "^TNX",   # US 10-Year
            "EUR": "TMBMKDE-10Y", # German 10-Year (often requires investing.com or specific tickers, yfinance might struggle, we will fallback)
            "JPY": "^JPY10=TR", # Japan 10-Year
            "GBP": "TMBMKGB-10Y", # UK 10-Year
            "AUD": "TMBMKAU-10Y", # AUS 10-Year
            "CAD": "TMBMKCA-10Y", # CAD 10-Year
            "CHF": "TMBMKCH-10Y", # CHF 10-Year
            "NZD": "TMBMKNZ-10Y", # NZD 10-Year
        }
        
        # Hardcoded approximations as of early 2024 to serve as a reliable fallback
        # rates in percentage
        self.cb_rates_fallback = {
            "USD": 5.50,
            "EUR": 4.50,
            "GBP": 5.25,
            "JPY": 0.10,
            "AUD": 4.35,
            "NZD": 5.50,
            "CAD": 5.00,
            "CHF": 1.75
        }

    def fetch_swap_impact(self, symbol):
        """
        Calculates the interest rate differential for a pair.
        Returns a text warning if holding the pair has massive negative carry.
        """
        try:
            if len(symbol) != 6 or not symbol.isalpha():
                return "Not a standard FX pair.", 0.0

            base = symbol[:3]
            quote = symbol[3:]

            # Try to fetch live 10Y yields from yfinance where possible (often sparse for non-US)
            # We'll use the hardcoded Central Bank fallback for stability in this tool,
            # as missing data from Yahoo for EU/UK bonds frequently breaks pipelines.
            
            rate_base = self.cb_rates_fallback.get(base, 0.0)
            rate_quote = self.cb_rates_fallback.get(quote, 0.0)
            
            differential = rate_base - rate_quote
            
            # If you go LONG, you earn base rate, pay quote rate.
            # If you go SHORT, you earn quote rate, pay base rate.
            
            long_carry = differential
            short_carry = -differential
            
            text = f"CARRY TRADE / SWAP ANALYSIS ({base}: {rate_base}% | {quote}: {rate_quote}%):\n"
            text += f"- Holding LONG: {'+' if long_carry > 0 else ''}{long_carry:.2f}% (Annualized Edge)\n"
            text += f"- Holding SHORT: {'+' if short_carry > 0 else ''}{short_carry:.2f}% (Annualized Edge)\n"
            
            # Add warnings for massive negative carry (e.g. Short USDJPY)
            if long_carry < -3.0:
                text += "⚠️ WARNING: Massive Negative Swap on LONG. Do not hold for extended periods natively.\n"
            elif short_carry < -3.0:
                text += "⚠️ WARNING: Massive Negative Swap on SHORT. Do not hold for extended periods natively.\n"
            elif long_carry > 3.0:
                text += "✅ POSITIVE CARRY: Favorable to hold LONG.\n"
            elif short_carry > 3.0:
                 text += "✅ POSITIVE CARRY: Favorable to hold SHORT.\n"

            return text, differential

        except Exception as e:
            self.logger.error(f"Yield Service Error: {e}")
            return "Yield Data Unavailable", 0.0
