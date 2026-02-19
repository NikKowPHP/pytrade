import chromadb
from chromadb.utils import embedding_functions
from services.logger import Logger
import os
import json

class RAGService:
    def __init__(self, persistence_path="rag_memory"):
        self.logger = Logger()
        self.client = chromadb.PersistentClient(path=persistence_path)
        
        # Use a lightweight embedding model
        self.embedding_cls = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="trade_memory",
            embedding_function=self.embedding_cls,
            metadata={"hnsw:space": "cosine"}
        )

    def add_memory(self, trade_id, context_text, result, profit_factor=0.0):
        """
        Stores a closed trade's context and outcome.
        - context_text: A string description of the market state (Indicators, Patterns, News).
        - result: WIN / LOSS
        - profit_factor: Numeric outcome (e.g., 2.5 for 2.5R win, -1.0 for loss)
        """
        try:
            self.logger.info(f"RAG: Learning from Trade {trade_id} ({result})")
            
            # Metadata for filtering/analysis
            meta = {
                "trade_id": str(trade_id),
                "result": result,
                "profit": float(profit_factor),
                "timestamp": str(os.path.getmtime("market_data.db")) # Approximation or pass explicit ts
            }

            self.collection.upsert(
                documents=[context_text],
                metadatas=[meta],
                ids=[str(trade_id)]
            )
            self.logger.info("RAG: Memory Stored Successfully.")
            return True
            
        except Exception as e:
            self.logger.error(f"RAG Store Error: {e}")
            return False

    def find_similar_trades(self, current_context, limit=3):
        """
        Retrieves the top N most similar historical market situations.
        Returns a list of dicts: {'context': text, 'result': WIN/LOSS, 'profit': float, 'distance': float}
        """
        try:
            results = self.collection.query(
                query_texts=[current_context],
                n_results=limit
            )
            
            # Parse ChromaDB's weird format
            memories = []
            if results['ids']:
                ids = results['ids'][0]
                metadatas = results['metadatas'][0]
                documents = results['documents'][0]
                distances = results['distances'][0]
                
                for i in range(len(ids)):
                    memories.append({
                        "id": ids[i],
                        "context": documents[i],
                        "result": metadatas[i]['result'],
                        "profit": metadatas[i]['profit'],
                        "similarity": 1 - distances[i] # Approximate similarity score
                    })
            
            return memories

        except Exception as e:
            self.logger.error(f"RAG Query Error: {e}")
            return []
