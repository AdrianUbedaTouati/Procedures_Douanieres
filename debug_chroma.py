"""
Debug script to check ChromaDB state
"""
import chromadb
from pathlib import Path
from agent_ia_core import config

chroma_path = Path(config.CHROMA_PERSIST_DIRECTORY)
collection_name = config.CHROMA_COLLECTION_NAME

print(f"ChromaDB Path: {chroma_path}")
print(f"Collection: {collection_name}")
print(f"Exists: {chroma_path.exists()}")

if chroma_path.exists():
    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = client.get_collection(name=collection_name)
        print(f"\nChunks: {collection.count()}")

        # Get one document to check dimension
        if collection.count() > 0:
            result = collection.get(limit=1, include=['embeddings', 'metadatas'])
            embeddings_list = result.get('embeddings')
            if embeddings_list is not None and len(embeddings_list) > 0:
                import numpy as np
                embedding = embeddings_list[0]
                if isinstance(embedding, np.ndarray):
                    dim = embedding.shape[0]
                else:
                    dim = len(embedding)
                print(f"Embedding dimension: {dim}")
            metadatas = result.get('metadatas')
            if metadatas is not None and len(metadatas) > 0:
                print(f"Sample metadata keys: {list(metadatas[0].keys())}")
    except Exception as e:
        print(f"Error: {e}")
