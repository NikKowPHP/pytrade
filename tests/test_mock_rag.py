import sys
from unittest.mock import MagicMock

# Create a mock chromadb module
start_mock = MagicMock()
sys.modules["chromadb"] = start_mock
sys.modules["chromadb.utils"] = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = MagicMock()

# Determine script directory
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.rag_service import RAGService

def test_mock_rag():
    print("Testing RAG logic with Mock ChromaDB...")
    
    # Mock the client and collection
    mock_client = start_mock.PersistentClient.return_value
    mock_collection = mock_client.get_or_create_collection.return_value
    
    rag = RAGService()
    
    # Test Add Memory
    print("1. Testing add_memory...")
    rag.add_memory("100", "Simulated Context", "WIN", 2.0)
    
    # Verify upsert call
    mock_collection.upsert.assert_called()
    call_args = mock_collection.upsert.call_args
    print(f"   Upsert called with: {call_args}")
    
    # Test Query
    print("2. Testing find_similar_trades...")
    # Mock query response
    mock_collection.query.return_value = {
        'ids': [['100']],
        'documents': [['Simulated Context']],
        'metadatas': [[{'result': 'WIN', 'profit': 2.0}]],
        'distances': [[0.1]]
    }
    
    results = rag.find_similar_trades("Query Context")
    print(f"   Results: {results}")
    
    if len(results) == 1 and results[0]['id'] == '100':
        print("SUCCESS: Mock verification passed.")
    else:
        print("FAIL: Mock verification failed.")

if __name__ == "__main__":
    test_mock_rag()
