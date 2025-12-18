#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar que el fix de metadata funciona correctamente.
Verifica el documento 00727473-2025 en ChromaDB.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from agent_ia_core.indexing.index_build import IndexBuilder
from apps.users.models import CustomUser

# Configuración ChromaDB local
CHROMA_PERSIST_DIRECTORY = os.path.join(os.path.dirname(__file__), 'data', 'index', 'chroma')
CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'eforms_chunks')

def main():
    print("=" * 80)
    print("VERIFICACIÓN: Metadata de contacto en documento 00727473-2025")
    print("=" * 80)

    try:
        # Obtener usuario admin
        user = CustomUser.objects.get(username='admin')
        print(f"✓ Usuario encontrado: {user.username}")

        # Crear IndexBuilder
        builder = IndexBuilder(
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_model=user.embedding_model,
            api_key=user.api_key,
            provider=user.llm_provider
        )

        # Cargar índice existente
        if not builder.load_existing():
            print("✗ No se pudo cargar el índice ChromaDB")
            return

        print(f"✓ Índice ChromaDB cargado")

        # Buscar chunks del documento
        collection = builder.vectorstore._collection
        results = collection.get(
            where={'ojs_notice_id': '00727473-2025'},
            limit=10
        )

        print(f"\n✓ Total chunks encontrados: {len(results['ids'])}\n")

        if len(results['ids']) == 0:
            print("⚠️ No se encontraron chunks para el documento 00727473-2025")
            print("¿Se ha re-indexado el documento después del fix?")
            return

        # Verificar cada chunk
        all_have_contact = True
        for i, (chunk_id, metadata) in enumerate(zip(results['ids'], results['metadatas'])):
            section = metadata.get('section', 'unknown')
            chunk_index = metadata.get('chunk_index', i)

            has_email = 'contact_email' in metadata and metadata['contact_email']
            has_phone = 'contact_phone' in metadata and metadata['contact_phone']
            has_url = 'contact_url' in metadata and metadata['contact_url']
            has_fax = 'contact_fax' in metadata and metadata['contact_fax']

            status = "✓" if (has_email or has_phone or has_url or has_fax) else "✗"

            print(f'{status} Chunk {chunk_index} ({section}):')
            print(f'    contact_email: {metadata.get("contact_email", "❌ NO EXISTE")}')
            print(f'    contact_phone: {metadata.get("contact_phone", "❌ NO EXISTE")}')
            print(f'    contact_url: {metadata.get("contact_url", "❌ NO EXISTE")}')
            print(f'    contact_fax: {metadata.get("contact_fax", "❌ NO EXISTE")}')
            print()

            if not (has_email or has_phone or has_url or has_fax):
                all_have_contact = False

        print("=" * 80)
        if all_have_contact:
            print("✅ ÉXITO: Todos los chunks tienen al menos un campo de contacto")
        else:
            print("⚠️ ADVERTENCIA: Algunos chunks NO tienen campos de contacto")
            print("   Posibles causas:")
            print("   1. El XML original no tiene información de contacto")
            print("   2. La re-indexación no se completó correctamente")
        print("=" * 80)

    except CustomUser.DoesNotExist:
        print("✗ Usuario 'admin' no encontrado")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
