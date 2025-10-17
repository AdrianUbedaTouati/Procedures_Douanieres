"""
Simple direct test of NVIDIA embeddings with user's API key
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("="*70)
print("TEST NVIDIA API KEY DIRECTO")
print("="*70)

# Get user
user = User.objects.get(username='pepe2012')
print(f"\nUser: {user.username}")
print(f"Provider: {user.llm_provider}")
print(f"API Key: {user.llm_api_key}")

# Set environment variable BEFORE any imports
os.environ['NVIDIA_API_KEY'] = user.llm_api_key
print(f"\nNVIDIA_API_KEY set in environment")

# Now import and test embeddings
print("\n[1] Creating NVIDIA embeddings directly...")
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

embeddings = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    nvidia_api_key=user.llm_api_key
)
print("  Embeddings created")

# Test embedding a query
print("\n[2] Testing embedding query...")
try:
    test_query = "licitaciones software"
    embedding = embeddings.embed_query(test_query)
    print(f"  Success! Embedding dimension: {len(embedding)}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETADO")
print("="*70)
