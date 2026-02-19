import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.rag_service import RAGService
import shutil

def verify_rag():
    TEST_DB_PATH = "test_rag_memory"
    
    # Clean up previous test
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)
        
    print("1. Initializing RAG Service...")
    rag = RAGService(persistence_path=TEST_DB_PATH)
    
    # 2. Add Mock Memory
    context_1 = "RSI: 80 | Trend: BEARISH | Pattern: Double Top | News: Rate Hikes"
    print(f"2. Adding Memory: {context_1} -> LOSS")
    rag.add_memory(trade_id=101, context_text=context_1, result="LOSS", profit_factor=-1.0)
    
    context_2 = "RSI: 30 | Trend: BULLISH | Pattern: Hammer | News: Rate Cut"
    print(f"2. Adding Memory: {context_2} -> WIN")
    rag.add_memory(trade_id=102, context_text=context_2, result="WIN", profit_factor=2.5)
    
    # 3. Query
    query = "RSI: 82 | Trend: BEARISH | Pattern: Double Top"
    print(f"3. Querying: {query}")
    
    results = rag.find_similar_trades(query, limit=1)
    
    if not results:
        print("FAIL: No results found.")
        return
        
    top_match = results[0]
    print(f"4. Result: {top_match}")
    
    if top_match['id'] == '101' and top_match['result'] == 'LOSS':
        print("SUCCESS: Retrieved correct historical trade logic.")
    else:
        print(f"FAIL: Expected ID 101/LOSS, got {top_match['id']}/{top_match['result']}")

    # Clean up
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

if __name__ == "__main__":
    verify_rag()
