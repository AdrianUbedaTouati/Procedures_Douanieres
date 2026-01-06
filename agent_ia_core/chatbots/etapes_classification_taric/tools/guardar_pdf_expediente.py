# -*- coding: utf-8 -*-
"""
Tool: guardar_pdf_expediente

Guarda un PDF descargado (mediante fetch_pdf) en la expedición para que
el usuario pueda consultarlo desde la interfaz web.
"""

from typing import Dict, Any
from agent_ia_core.chatbots.shared import ToolDefinition
import logging
import os
import shutil

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="guardar_pdf_expediente",
    description=(
        "Guarda un PDF útil en la expedición para que el usuario pueda consultarlo. "
        "Usa esta herramienta después de fetch_pdf cuando el documento sea relevante "
        "para la clasificación TARIC (fichas técnicas, datasheets, normativas, etc.). "
        "El documento aparecerá en la interfaz del usuario junto al chat."
    ),
    parameters={
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Ruta completa del PDF descargado (obtenida de fetch_pdf). Ejemplo: '/var/www/.../documento.pdf'"
            },
            "titulo": {
                "type": "string",
                "description": "Título descriptivo del documento. Ejemplo: 'Ficha técnica del producto XYZ'"
            },
            "url_origen": {
                "type": "string",
                "description": "URL de donde se descargó el PDF (obtenida de fetch_pdf)"
            },
            "razon": {
                "type": "string",
                "description": "Por qué este documento es útil para la clasificación. Ejemplo: 'Contiene especificaciones técnicas del producto'"
            }
        },
        "required": ["filepath", "titulo", "url_origen"]
    },
    function=None,
    category="classification"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def guardar_pdf_expediente(
    filepath: str,
    titulo: str,
    url_origen: str,
    razon: str = "",
    expedition_id: int = None,
    etape_id: int = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Guarda un PDF descargado en la base de datos de la expedición.

    Args:
        filepath: Ruta completa del PDF descargado
        titulo: Título descriptivo del documento
        url_origen: URL de origen del PDF
        razon: Razón por la que el documento es útil
        expedition_id: ID de la expedición (inyectado por el contexto)
        etape_id: ID de la etapa (inyectado por el contexto)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con resultado de la operación
    """
    try:
        # Validar parámetros
        if not filepath or not isinstance(filepath, str):
            return {
                'success': False,
                'error': 'filepath es requerido y debe ser un string'
            }

        if not titulo or not isinstance(titulo, str):
            return {
                'success': False,
                'error': 'titulo es requerido y debe ser un string'
            }

        if not url_origen or not isinstance(url_origen, str):
            return {
                'success': False,
                'error': 'url_origen es requerido y debe ser un string'
            }

        # Verificar que el archivo existe
        if not os.path.exists(filepath):
            return {
                'success': False,
                'error': f'El archivo no existe: {filepath}'
            }

        # Verificar que es un PDF
        if not filepath.lower().endswith('.pdf'):
            return {
                'success': False,
                'error': 'El archivo debe ser un PDF'
            }

        # Verificar que tenemos contexto de expedición
        if not expedition_id and not etape_id:
            return {
                'success': False,
                'error': 'No hay contexto de expedición. Esta tool debe ejecutarse dentro de una sesión de clasificación.'
            }

        logger.info(f"[GUARDAR_PDF] Guardando PDF en expedición: {titulo}")

        # Importar modelos de Django
        try:
            import django
            if not django.conf.settings.configured:
                django.setup()

            from apps.expeditions.models import WebDocument, ExpeditionEtape
            from django.core.files import File
        except ImportError as e:
            return {
                'success': False,
                'error': f'Error importando modelos Django: {str(e)}'
            }

        # Obtener la etapa
        try:
            if etape_id:
                etape = ExpeditionEtape.objects.get(id=etape_id)
            else:
                # Buscar etapa 1 (classification) de la expedición
                etape = ExpeditionEtape.objects.get(
                    expedition_id=expedition_id,
                    numero=1
                )
        except ExpeditionEtape.DoesNotExist:
            return {
                'success': False,
                'error': f'No se encontró la etapa de clasificación para la expedición {expedition_id}'
            }

        # Obtener información del archivo
        file_size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        # Extraer texto del PDF para el preview
        texto_extraido = ""
        paginas = 0
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            paginas = len(doc)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            # Guardar solo los primeros 2000 caracteres como preview
            texto_extraido = '\n'.join(text_parts)[:2000]
        except Exception as e:
            logger.warning(f"[GUARDAR_PDF] No se pudo extraer texto: {e}")

        # Crear el WebDocument
        with open(filepath, 'rb') as f:
            web_doc = WebDocument(
                etape=etape,
                url_origen=url_origen,
                titulo=titulo[:255],  # Limitar longitud
                nom_fichier=filename,
                razon_guardado=razon[:500] if razon else "",
                texto_extraido=texto_extraido,
                tamano_bytes=file_size,
                paginas=paginas
            )
            web_doc.fichier.save(filename, File(f), save=True)

        logger.info(f"[GUARDAR_PDF] PDF guardado exitosamente: {web_doc.id} - {titulo}")

        return {
            'success': True,
            'data': {
                'id': web_doc.id,
                'titulo': web_doc.titulo,
                'url_origen': web_doc.url_origen,
                'nom_fichier': web_doc.nom_fichier,
                'tamano': web_doc.tamano_legible,
                'paginas': web_doc.paginas,
                'fichier_url': web_doc.fichier.url if web_doc.fichier else None,
                'expedition_id': etape.expedition_id,
                'dominio': web_doc.dominio_origen
            },
            'message': f'PDF guardado exitosamente: "{titulo}". El usuario puede consultarlo en la interfaz.'
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[GUARDAR_PDF] Error: {error_msg}", exc_info=True)
        return {
            'success': False,
            'error': f'Error guardando PDF: {error_msg}'
        }


TOOL_DEFINITION.function = guardar_pdf_expediente
