"""
Direct test of retriever to isolate the 0 documents issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from agent_ia_core.retriever import create_retriever
from agent_ia_core import config

User = get_user_model()

print("="*70)
print("DIRECT RETRIEVER TEST - NVIDIA")
print("="*70)

# Get user configuration
user = User.objects.get(username='pepe2012')
print(f"\nUser: {user.username}")
print(f"Provider: {user.llm_provider}")
print(f"API Key: {user.llm_api_key[:20]}...")

# Create retriever with explicit NVIDIA configuration
print("\n[1] Creating retriever with NVIDIA embeddings...")
retriever = create_retriever(
    k=6,
    provider='nvidia',
    api_key=user.llm_api_key,
    embedding_model='nvidia/nv-embedqa-e5-v5'
)
print(f"  Retriever created: {type(retriever)}")
print(f"  Vectorstore: {type(retriever.vectorstore)}")

# Test queries
queries = [
    "licitaciones software",
    "¿Cuántas licitaciones hay?",
    "software development",
]

for i, query in enumerate(queries, 1):
    print(f"\n[Q{i}] Query: '{query}'")
    try:
        # Direct retrieval
        docs = retriever.retrieve(query, k=6)
        print(f"  Documents retrieved: {len(docs)}")

        if len(docs) > 0:
            print(f"  First doc preview: {docs[0].page_content[:150]}...")
            print(f"  Metadata: {docs[0].metadata}")
        else:
            print("  [WARNING] No documents found!")

            # Try vectorstore directly
            print("\n  Testing vectorstore.similarity_search directly...")
            vs_docs = retriever.vectorstore.similarity_search(query, k=6)
            print(f"  Vectorstore docs: {len(vs_docs)}")

            # Try with similarity scores
            print("\n  Testing with similarity_search_with_score...")
            vs_docs_with_score = retriever.vectorstore.similarity_search_with_score(query, k=6)
            print(f"  Results with scores: {len(vs_docs_with_score)}")
            if vs_docs_with_score:
                for doc, score in vs_docs_with_score:
                    print(f"    - Score: {score:.4f}, Content: {doc.page_content[:80]}...")

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

# Verify ChromaDB directly
print("\n" + "="*70)
print("CHROMADB DIRECT VERIFICATION")
print("="*70)

import chromadb
from pathlib import Path

chroma_path = Path(config.CHROMA_PERSIST_DIRECTORY)
print(f"\nChromaDB Path: {chroma_path}")
print(f"Exists: {chroma_path.exists()}")

if chroma_path.exists():
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_collection(name=config.CHROMA_COLLECTION_NAME)
    count = collection.count()
    print(f"Chunks in collection: {count}")

    # Get sample documents
    if count > 0:
        result = collection.get(limit=3, include=['documents', 'metadatas', 'embeddings'])
        print(f"\nSample documents:")
        for i, (doc, meta) in enumerate(zip(result['documents'], result['metadatas']), 1):
            print(f"  {i}. {doc[:100]}...")
            print(f"     Metadata: {meta}")

        # Check embedding dimension
        embedding = result['embeddings'][0]
        print(f"\nEmbedding dimension: {len(embedding)}")

        # Try querying directly with NVIDIA embeddings
        print("\n" + "="*70)
        print("CHROMADB QUERY WITH NVIDIA EMBEDDINGS")
        print("="*70)

        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        test_embeddings = NVIDIAEmbeddings(
            model='nvidia/nv-embedqa-e5-v5',
            nvidia_api_key=user.llm_api_key
        )

        test_query = "software development"
        print(f"\nQuerying ChromaDB with: '{test_query}'")

        # Create query embedding
        query_embedding = test_embeddings.embed_query(test_query)
        print(f"Query embedding dimension: {len(query_embedding)}")

        # Query collection
        query_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=6,
            include=['documents', 'metadatas', 'distances']
        )

        print(f"Results: {len(query_results['documents'][0])}")
        if query_results['documents'][0]:
            for i, (doc, dist) in enumerate(zip(query_results['documents'][0], query_results['distances'][0]), 1):
                print(f"  {i}. Distance: {dist:.4f}")
                print(f"     Content: {doc[:100]}...")
        else:
            print("  [WARNING] ChromaDB direct query also returned 0 results!")

print("\n" + "="*70)
print("TEST COMPLETED")
print("="*70)
