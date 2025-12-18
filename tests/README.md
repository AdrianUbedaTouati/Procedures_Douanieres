# Tests - TenderAI Platform

Esta carpeta contiene scripts de test y utilidades para verificar el correcto funcionamiento del sistema.

## Scripts de Test Disponibles

### Test de Sistema Completo
- **test_complete_system.py**: Test integral del sistema completo
  - Verifica usuario y configuracion
  - Muestra limites de NVIDIA API
  - Prueba calculo de tokens y costes
  - Verifica VectorizationService
  - Prueba ChatService con mensaje real

**Uso:**
```bash
python tests/test_complete_system.py
```

### Tests de Integracion
- **test_integration.py**: Tests de integracion entre componentes
- **test_full_flow.py**: Test del flujo completo de usuario

### Tests de NVIDIA NIM
- **test_chat_nvidia.py**: Test del chat con NVIDIA NIM
- **test_nvidia_simple.py**: Test simple de NVIDIA
- **test_nvidia_complete.py**: Test completo de NVIDIA embeddings
- **test_retriever_direct.py**: Test directo del retriever

### Tests de TED API
- **test_ted_connection.py**: Test de conexion con TED API

### Utilidades de Debug
- **debug_chroma.py**: Utilidad para debugear ChromaDB
- **check_tenders.py**: Verificar licitaciones en BD
- **download_with_xml.py**: Descargar licitaciones con XML

## Requisitos

Todos los tests requieren:
- Django project configurado
- Base de datos inicializada
- Variables de entorno en `.env`
- Usuario `pepe2012` creado (para test_complete_system.py)

## Notas

- Los tests de NVIDIA requieren API key valida
- Los tests de ChromaDB requieren vectorstore inicializado
- Los logs y outputs temporales han sido eliminados para mantener el proyecto limpio
