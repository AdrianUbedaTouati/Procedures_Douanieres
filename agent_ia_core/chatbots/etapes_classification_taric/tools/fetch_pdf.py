# -*- coding: utf-8 -*-
"""
Tool: fetch_pdf

Descarga un archivo PDF desde una URL y lo guarda en el directorio de documentos
de la expedición para su posterior análisis.
"""

from typing import Dict, Any
from agent_ia_core.chatbots.shared import ToolDefinition
from urllib.parse import urlparse
import logging
import requests
import os
import re
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="fetch_pdf",
    description=(
        "Descarga un PDF desde una URL y lo guarda en la expedición. "
        "Extrae el texto del PDF para análisis. "
        "Ideal para fichas técnicas, datasheets, o documentos normativos encontrados con browse_webpage."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL completa del PDF a descargar. Ejemplo: 'https://example.com/ficha-tecnica.pdf'"
            },
            "descripcion": {
                "type": "string",
                "description": "Descripción breve del documento. Ejemplo: 'Ficha técnica del producto', 'Datasheet componente X'"
            }
        },
        "required": ["url"]
    },
    function=None,
    category="web"
)


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _sanitize_filename(filename: str) -> str:
    """Limpia un nombre de archivo eliminando caracteres no válidos."""
    # Eliminar caracteres no válidos
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Eliminar espacios múltiples
    filename = re.sub(r'\s+', '_', filename)
    # Limitar longitud
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    return filename


def _generate_filename_from_url(url: str, descripcion: str = None) -> str:
    """Genera un nombre de archivo basado en la URL y descripción."""
    parsed = urlparse(url)
    path = parsed.path

    # Intentar obtener nombre del path
    if path:
        original_name = os.path.basename(path)
        if original_name and original_name.lower().endswith('.pdf'):
            base_name = _sanitize_filename(original_name)
        else:
            # Usar hash de URL si no hay nombre válido
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            base_name = f"documento_{url_hash}.pdf"
    else:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        base_name = f"documento_{url_hash}.pdf"

    # Añadir timestamp para evitar colisiones
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(base_name)
    final_name = f"{name}_{timestamp}{ext}"

    return final_name


def _extract_text_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extrae texto de un PDF usando PyMuPDF (fitz).

    Returns:
        Dict con 'text', 'pages', 'success', 'error'
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {
            'success': False,
            'error': 'PyMuPDF no instalado. Ejecuta: pip install PyMuPDF',
            'text': '',
            'pages': 0
        }

    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        page_count = len(doc)

        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Página {page_num} ---\n{page_text}")

        doc.close()

        full_text = '\n\n'.join(text_parts)

        return {
            'success': True,
            'text': full_text,
            'pages': page_count,
            'chars': len(full_text)
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error extrayendo texto del PDF: {str(e)}',
            'text': '',
            'pages': 0
        }


# ============================================================================
# IMPLEMENTACIÓN PRINCIPAL
# ============================================================================

def fetch_pdf(url: str, descripcion: str = None, expedition_id: int = None,
              documents_path: str = None, **kwargs) -> Dict[str, Any]:
    """
    Descarga un PDF desde una URL, lo guarda y extrae su texto.

    Args:
        url: URL completa del PDF a descargar
        descripcion: Descripción opcional del documento
        expedition_id: ID de la expedición (inyectado por registry/contexto)
        documents_path: Ruta donde guardar documentos (inyectado por registry/contexto)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con formato:
        {
            'success': True/False,
            'data': {
                'url': str,
                'filename': str,
                'filepath': str,
                'size_bytes': int,
                'text_extraction': {
                    'success': bool,
                    'text': str (primeros 5000 chars),
                    'full_text_chars': int,
                    'pages': int
                }
            },
            'error': str (si success=False)
        }
    """
    try:
        # Validar URL
        if not url or not isinstance(url, str):
            return {
                'success': False,
                'error': 'URL debe ser un string no vacío'
            }

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            return {
                'success': False,
                'error': 'URL debe empezar con http:// o https://'
            }

        logger.info(f"[FETCH_PDF] Descargando PDF desde: {url}")

        # Configurar headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,*/*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }

        # Descargar PDF
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True, stream=True)
        response.raise_for_status()

        # Verificar que es un PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and 'application/x-pdf' not in content_type:
            # Verificar por magic bytes si content-type no es confiable
            first_bytes = response.content[:5]
            if first_bytes != b'%PDF-':
                return {
                    'success': False,
                    'error': f'La URL no retornó un PDF válido. Content-Type: {content_type}'
                }

        # Determinar directorio de destino
        if documents_path:
            save_dir = documents_path
        elif expedition_id:
            # Ruta por defecto para expediciones
            save_dir = f"/var/www/ProyectoMarc/data/media_expediciones/{expedition_id}/etape_1_classification/documents"
        else:
            # Ruta temporal si no hay contexto de expedición
            save_dir = "/var/www/ProyectoMarc/data/temp_pdfs"

        # Crear directorio si no existe
        os.makedirs(save_dir, exist_ok=True)

        # Generar nombre de archivo
        filename = _generate_filename_from_url(url, descripcion)
        filepath = os.path.join(save_dir, filename)

        # Guardar archivo
        with open(filepath, 'wb') as f:
            f.write(response.content)

        file_size = os.path.getsize(filepath)
        logger.info(f"[FETCH_PDF] PDF guardado: {filepath} ({file_size} bytes)")

        # Extraer texto del PDF
        text_result = _extract_text_from_pdf(filepath)

        # Preparar respuesta
        result = {
            'success': True,
            'data': {
                'url': url,
                'descripcion': descripcion or 'Sin descripción',
                'filename': filename,
                'filepath': filepath,
                'size_bytes': file_size,
                'size_readable': f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB",
                'text_extraction': {
                    'success': text_result['success'],
                    'pages': text_result.get('pages', 0),
                    'full_text_chars': text_result.get('chars', 0),
                    # Incluir solo los primeros 5000 caracteres para no sobrecargar
                    'text_preview': text_result.get('text', '')[:5000],
                    'text_truncated': len(text_result.get('text', '')) > 5000
                }
            },
            'message': f'PDF descargado exitosamente: {filename}'
        }

        if not text_result['success']:
            result['data']['text_extraction']['error'] = text_result.get('error', 'Error desconocido')
            result['message'] += f'. Nota: {text_result.get("error", "No se pudo extraer texto")}'

        return result

    except requests.exceptions.Timeout:
        logger.error(f"[FETCH_PDF] Timeout descargando {url}")
        return {
            'success': False,
            'error': f'Timeout después de 30 segundos. El servidor tardó demasiado en responder.'
        }

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"[FETCH_PDF] HTTP Error {status_code} en {url}")

        if status_code == 403:
            return {
                'success': False,
                'error': f'Acceso prohibido (403). El sitio bloquea la descarga del PDF.'
            }
        elif status_code == 404:
            return {
                'success': False,
                'error': f'PDF no encontrado (404). La URL no existe.'
            }
        else:
            return {
                'success': False,
                'error': f'Error HTTP {status_code} al descargar el PDF.'
            }

    except requests.exceptions.ConnectionError:
        logger.error(f"[FETCH_PDF] Connection error a {url}")
        return {
            'success': False,
            'error': f'Error de conexión. No se puede alcanzar el servidor.'
        }

    except IOError as e:
        logger.error(f"[FETCH_PDF] Error de I/O guardando PDF: {e}")
        return {
            'success': False,
            'error': f'Error guardando el archivo PDF: {str(e)}'
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[FETCH_PDF] Error inesperado: {error_msg}", exc_info=True)
        return {
            'success': False,
            'error': f'Error descargando PDF: {error_msg}'
        }


TOOL_DEFINITION.function = fetch_pdf
