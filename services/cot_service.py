import pandas as pd
import requests
import io
from services.logger import Logger
import datetime

class COTService:
    """
    Fetches and parses Commitment of Traders (COT) data from the CFTC.
    Focuses on the 'Financial Futures' report which includes Forex pairs.
    """
    
    # URL for the "Traders in Financial Futures; Futures Only" report (Weekly, Text format)
    COT_URL = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"

    # Mapping
    SYMBOL_MAP = {
        "EURUSD": "EURO FX -",
        "GBPUSD": "BRITISH POUND -", # TFF uses BRITISH POUND - CME
        "JPYUSD": "JAPANESE YEN -",
        "USDJPY": "JAPANESE YEN -",
        "AUDUSD": "AUSTRALIAN DOLLAR -",
        "USDCAD": "CANADIAN DOLLAR -",
        "USDCHF": "SWISS FRANC -",
        "NZDUSD": "NZ DOLLAR -",
        "XAUUSD": "GOLD", # Gold might be in different report (Disaggregated), but checking here matches nothing usually
        "BTCUSD": "BITCOIN -",
        "MXNUSD": "MEXICAN PESO -",
        "BRLUSD": "BRAZILIAN REAL -"
    }


    def __init__(self):
        self.logger = Logger()

    def update_cot_data(self, db):
        """Fetches and updates the database with the latest TFF COT data."""
        self.logger.info(f"Fetching TFF COT Report from {self.COT_URL}")
        
        try:
            response = requests.get(self.COT_URL, timeout=15)
            response.raise_for_status()
            
            data = self.parse_tff_report(response.content)
            
            if data:
                db.save_cot_data(data)
                self.logger.info(f"Successfully processed {len(data)} COT records.")
                return True
            else:
                self.logger.warning("No COT data parsed.")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update COT data: {e}")
            return False

    def parse_tff_report(self, csv_content):
        """
        Parses the 'Traders in Financial Futures' (TFF) report.
        Format: Text file, comma delimited.
        
        Key Columns (Indices based on known TFF format):
        0: Market_and_Exchange_Names
        2: Report_Date_as_MM_DD_YYYY
        3: Open_Interest_All
        4: Dealer_Positions_Long_All (Commercials/Banks)
        5: Dealer_Positions_Short_All
        ...
        10: Lev_Money_Positions_Long_All (Hedge Funds/Non-Commercials)
        11: Lev_Money_Positions_Short_All
        """
        try:
            # TFF txt usually has a header row? Actually FinFutWk.txt usually NO header or cryptic one.
            # But standard pandas read_csv works if we skip bad lines.
            
            df = pd.read_csv(io.BytesIO(csv_content), header=None, on_bad_lines='skip', low_memory=False)
            
            results = []
            
            for _, row in df.iterrows():
                try:
                    contract_name = str(row[0]).strip().upper()
                    
                    # Find matching symbol
                    symbol = None
                    for s, c_name in self.SYMBOL_MAP.items():
                        if c_name in contract_name:
                            symbol = s
                            break
                    
                    if symbol:
                        # Clean Date
                        date_str = str(row[2])
                        dt = pd.to_datetime(date_str).to_pydatetime()
                        
                        # Indices based on FinFutWk.txt inspection:
                        # 0: Name, 1: Code, 2: Date, 3: ID, 4: Exch, 5: ?, 6: ?
                        # 7: Open Interest
                        # 8: Dealer Long, 9: Short, 10: Spread
                        # 11: Asset Mgr Long, 12: Short, 13: Spread
                        # 14: Lev Money Long, 15: Short, 16: Spread
                        
                        # Banks (Dealer) -> Commercials
                        comm_long = float(row[8])
                        comm_short = float(row[9])
                        net_comm = comm_long - comm_short
                        
                        # Hedge Funds (Leveraged Money) -> Non-Commercials
                        nc_long = float(row[14])
                        nc_short = float(row[15])
                        net_nc = nc_long - nc_short
                        
                        results.append({
                            "date": dt,
                            "symbol": symbol,
                            "contract": contract_name,
                            "non_comm_long": nc_long,
                            "non_comm_short": nc_short,
                            "net_non_comm": net_nc,
                            "comm_long": comm_long,
                            "comm_short": comm_short,
                            "net_comm": net_comm,
                            "open_interest": float(row[7])
                        })
                except Exception as row_e:
                    # self.logger.debug(f"Row parse error: {row_e}")
                    continue
            
            return results

        except Exception as e:
            self.logger.error(f"Error parsing TFF CSV: {e}")
            return []
