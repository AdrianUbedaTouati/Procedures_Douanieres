# -*- coding: utf-8 -*-
"""
Tool para analizar documentos (imagenes y PDFs) usando GPT-4o Vision.

Estrategia para PDFs:
1. Primero intenta extraer texto con PyPDF2 (gratis)
2. Si el texto es insuficiente (<100 chars), convierte a imagenes y usa Vision

Envia las imagenes a GPT-4o con detail:low para extraer informacion
relevante para la clasificacion TARIC.
"""
import base64
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Modelo recomendado para vision (mas barato que mini para imagenes)
VISION_MODEL = "gpt-4o-2024-08-06"
VISION_DETAIL = "low"  # 85 tokens fijos por imagen

# Minimo de caracteres para considerar que la extraccion de texto fue exitosa
MIN_TEXT_LENGTH = 100


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """
    Codifica una imagen a base64.

    Args:
        image_path: Ruta absoluta a la imagen

    Returns:
        String base64 o None si hay error
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.standard_b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error codificando imagen {image_path}: {e}")
        return None


def get_image_media_type(filename: str) -> str:
    """Obtiene el media type segun la extension."""
    ext = filename.lower().split('.')[-1]
    media_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }
    return media_types.get(ext, 'image/jpeg')


def extract_text_from_pdf(pdf_path: str, max_pages: int = 5) -> Tuple[str, bool]:
    """
    Extrae texto de un PDF usando PyPDF2.

    Args:
        pdf_path: Ruta al archivo PDF
        max_pages: Numero maximo de paginas a procesar

    Returns:
        Tuple (texto_extraido, exito)
    """
    try:
        import PyPDF2

        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text_parts = []

            num_pages = min(len(reader.pages), max_pages)
            for i in range(num_pages):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text_parts.append(f"--- Pagina {i+1} ---\n{page_text}")

            full_text = "\n\n".join(text_parts)

            # Verificar si el texto extraido es suficiente
            if len(full_text.strip()) >= MIN_TEXT_LENGTH:
                logger.info(f"PDF texto extraido: {len(full_text)} caracteres de {num_pages} paginas")
                return full_text, True
            else:
                logger.warning(f"PDF texto insuficiente: {len(full_text)} chars (min: {MIN_TEXT_LENGTH})")
                return full_text, False

    except ImportError:
        logger.error("PyPDF2 no instalado. Ejecutar: pip install PyPDF2")
        return "", False
    except Exception as e:
        logger.error(f"Error extrayendo texto de PDF {pdf_path}: {e}")
        return "", False


def convert_pdf_to_images(pdf_path: str, max_pages: int = 5) -> List[str]:
    """
    Convierte un PDF a imagenes (una por pagina).
    Solo se usa cuando la extraccion de texto falla.

    Args:
        pdf_path: Ruta al archivo PDF
        max_pages: Numero maximo de paginas a convertir

    Returns:
        Lista de rutas a las imagenes temporales generadas
    """
    try:
        from pdf2image import convert_from_path

        # Convertir PDF a imagenes
        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=max_pages,
            dpi=150,  # Resolucion moderada para low detail
            fmt='jpeg'
        )

        # Guardar imagenes temporales
        temp_paths = []
        pdf_name = Path(pdf_path).stem
        temp_dir = Path(pdf_path).parent / '.temp_pdf_images'
        temp_dir.mkdir(exist_ok=True)

        for i, image in enumerate(images):
            temp_path = temp_dir / f"{pdf_name}_page_{i+1}.jpg"
            image.save(str(temp_path), 'JPEG', quality=85)
            temp_paths.append(str(temp_path))
            logger.info(f"PDF pagina {i+1} convertida a imagen: {temp_path}")

        return temp_paths

    except ImportError:
        logger.error("pdf2image no instalado. Ejecutar: pip install pdf2image")
        logger.error("Tambien necesitas poppler: apt install poppler-utils")
        return []
    except Exception as e:
        logger.error(f"Error convirtiendo PDF {pdf_path}: {e}")
        return []


def analyze_images_with_vision(
    image_paths: List[str],
    prompt: str,
    api_key: str,
    model: str = VISION_MODEL,
    detail: str = VISION_DETAIL
) -> Dict[str, Any]:
    """
    Analiza una o varias imagenes con GPT-4o Vision.

    Args:
        image_paths: Lista de rutas a imagenes
        prompt: Instrucciones para el analisis
        api_key: OpenAI API key
        model: Modelo a usar (default: gpt-4o-2024-08-06)
        detail: Nivel de detalle (low/high)

    Returns:
        Dict con el resultado del analisis
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Construir el contenido del mensaje con las imagenes
        content = [{"type": "text", "text": prompt}]

        for image_path in image_paths:
            base64_image = encode_image_to_base64(image_path)
            if base64_image:
                media_type = get_image_media_type(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{base64_image}",
                        "detail": detail
                    }
                })
                logger.info(f"Imagen anadida al analisis: {Path(image_path).name}")

        # Verificar que hay al menos una imagen
        if len(content) == 1:
            return {
                'success': False,
                'error': 'No se pudieron cargar las imagenes',
                'analysis': None
            }

        # Llamar a la API de OpenAI
        logger.info(f"Enviando {len(content)-1} imagen(es) a {model} con detail={detail}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=1500
        )

        analysis = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(f"Analisis completado. Tokens usados: {tokens_used}")

        return {
            'success': True,
            'analysis': analysis,
            'tokens_used': tokens_used,
            'images_analyzed': len(content) - 1,
            'model': model,
            'detail': detail
        }

    except ImportError:
        logger.error("openai no instalado. Ejecutar: pip install openai")
        return {
            'success': False,
            'error': 'Libreria openai no instalada',
            'analysis': None
        }
    except Exception as e:
        logger.error(f"Error en analisis vision: {e}")
        return {
            'success': False,
            'error': str(e),
            'analysis': None
        }


def cleanup_temp_images(temp_paths: List[str]):
    """Elimina las imagenes temporales generadas de PDFs."""
    for path in temp_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"No se pudo eliminar {path}: {e}")

    # Intentar eliminar el directorio temporal si esta vacio
    if temp_paths:
        temp_dir = Path(temp_paths[0]).parent
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except Exception:
            pass


def evaluate_pdf_text_quality(
    pdf_text: str,
    product_name: str,
    api_key: str,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Evalua si el texto extraido del PDF es suficiente para clasificar
    o si se necesita analisis visual.

    Args:
        pdf_text: Texto extraido del PDF
        product_name: Nombre del producto
        api_key: OpenAI API key
        model: Modelo a usar

    Returns:
        Dict con 'needs_vision' (bool) y 'reason' (str)
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        evaluation_prompt = f"""Evalua el siguiente texto extraido de un documento PDF para clasificacion aduanera TARIC.

PRODUCTO: {product_name}

TEXTO EXTRAIDO:
{pdf_text[:2000]}

PREGUNTA: ¿El texto contiene informacion suficiente para clasificar el producto, o detectas indicios de que hay imagenes/diagramas/tablas importantes que no se han capturado?

Responde SOLO con un JSON:
{{
    "needs_vision": true/false,
    "reason": "explicacion breve",
    "info_found": ["lista de info encontrada"],
    "info_missing": ["lista de info que podria estar en imagenes"]
}}

Criterios para needs_vision=true:
- El texto menciona "ver imagen", "ver diagrama", "ver figura"
- Hay referencias a tablas de especificaciones que no aparecen
- El texto parece incompleto o tiene huecos
- Es una ficha tecnica pero faltan especificaciones clave
- El producto necesita identificacion visual (ropa, electronica, etc.)

Criterios para needs_vision=false:
- El texto contiene descripcion clara del producto
- Hay especificaciones tecnicas suficientes
- Se mencionan materiales/composicion
- No hay indicios de imagenes importantes omitidas
"""

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": evaluation_prompt}],
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()

        # Intentar parsear JSON
        import json
        # Limpiar posibles markdown
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        result = json.loads(response_text)
        logger.info(f"Evaluacion PDF: needs_vision={result.get('needs_vision')}, reason={result.get('reason')}")

        return {
            'success': True,
            'needs_vision': result.get('needs_vision', False),
            'reason': result.get('reason', ''),
            'info_found': result.get('info_found', []),
            'info_missing': result.get('info_missing', [])
        }

    except json.JSONDecodeError as e:
        logger.warning(f"No se pudo parsear respuesta de evaluacion: {e}")
        # En caso de duda, usar vision
        return {
            'success': False,
            'needs_vision': True,
            'reason': 'No se pudo evaluar el texto, usando vision por precaucion'
        }
    except Exception as e:
        logger.error(f"Error evaluando texto PDF: {e}")
        return {
            'success': False,
            'needs_vision': True,
            'reason': f'Error en evaluacion: {str(e)}'
        }


def analyze_text_only(
    prompt: str,
    api_key: str,
    model: str = "gpt-4o-mini"  # Modelo de texto mas barato
) -> Dict[str, Any]:
    """
    Analiza texto usando GPT-4o-mini (sin vision).
    Se usa cuando solo hay texto extraido de PDFs.

    Args:
        prompt: Texto a analizar
        api_key: OpenAI API key
        model: Modelo a usar (default: gpt-4o-mini para texto)

    Returns:
        Dict con el resultado del analisis
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        logger.info(f"Analizando texto con {model}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1500
        )

        analysis = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(f"Analisis de texto completado. Tokens usados: {tokens_used}")

        return {
            'success': True,
            'analysis': analysis,
            'tokens_used': tokens_used,
            'images_analyzed': 0,
            'model': model,
            'method': 'text_only'
        }

    except ImportError:
        logger.error("openai no instalado. Ejecutar: pip install openai")
        return {
            'success': False,
            'error': 'Libreria openai no instalada',
            'analysis': None
        }
    except Exception as e:
        logger.error(f"Error en analisis de texto: {e}")
        return {
            'success': False,
            'error': str(e),
            'analysis': None
        }


def analyze_documents(
    expedition_id: int,
    document_ids: List[int] = None,
    user=None
) -> Dict[str, Any]:
    """
    Analiza los documentos de una expedicion para extraer informacion
    relevante para la clasificacion TARIC.

    Args:
        expedition_id: ID de la expedicion
        document_ids: Lista de IDs de documentos a analizar (opcional, si no se pasa analiza todos)
        user: Usuario Django (necesario para obtener la API key)

    Returns:
        Dict con el analisis de los documentos
    """
    try:
        from django.conf import settings
        from apps.expeditions.models import Expedition, ExpeditionDocument
        from apps.authentication.models import User

        # Obtener la expedicion
        expedition = Expedition.objects.filter(pk=expedition_id).first()
        if not expedition:
            return {
                'success': False,
                'error': f'Expedicion {expedition_id} no encontrada',
                'analysis': None
            }

        # Obtener el usuario y su API key
        if user is None:
            user = expedition.user

        if not user or user.llm_provider != 'openai':
            return {
                'success': False,
                'error': 'Se requiere un usuario con proveedor OpenAI configurado',
                'analysis': None
            }

        api_key = user.llm_api_key
        if not api_key:
            return {
                'success': False,
                'error': 'El usuario no tiene API key de OpenAI configurada',
                'analysis': None
            }

        # Obtener la etapa de clasificacion (etapa 1)
        etape = expedition.get_etape(1)
        if not etape:
            return {
                'success': False,
                'error': 'Etapa de clasificacion no encontrada',
                'analysis': None
            }

        # Obtener los documentos
        if document_ids:
            documents = etape.documents.filter(pk__in=document_ids)
        else:
            documents = etape.documents.all()

        if not documents.exists():
            return {
                'success': False,
                'error': 'No hay documentos para analizar',
                'analysis': None
            }

        # Separar imagenes y PDFs
        image_paths = []
        pdf_temp_images = []
        pdf_texts = []  # Texto extraido de PDFs
        documents_info = []

        for doc in documents:
            if not doc.fichier:
                continue

            file_path = doc.fichier.path

            if doc.is_image:
                image_paths.append(file_path)
                documents_info.append({
                    'id': doc.id,
                    'name': doc.nom_original,
                    'type': 'image'
                })
            elif doc.is_pdf:
                # Primero intentar extraer texto
                pdf_text, text_success = extract_text_from_pdf(file_path, max_pages=5)

                if text_success:
                    # Texto extraido - evaluar si es suficiente o necesita vision
                    product_name = expedition.nom_article or 'No especificado'
                    evaluation = evaluate_pdf_text_quality(pdf_text, product_name, api_key)

                    if evaluation.get('needs_vision', False):
                        # El LLM determino que necesita vision
                        logger.info(f"PDF {doc.nom_original}: LLM recomienda vision - {evaluation.get('reason')}")
                        pdf_images = convert_pdf_to_images(file_path, max_pages=3)
                        if pdf_images:
                            pdf_temp_images.extend(pdf_images)
                            image_paths.extend(pdf_images)
                            documents_info.append({
                                'id': doc.id,
                                'name': doc.nom_original,
                                'type': 'pdf',
                                'method': 'vision_after_evaluation',
                                'evaluation_reason': evaluation.get('reason'),
                                'pages_converted': len(pdf_images)
                            })
                        else:
                            # Fallback a texto si no se puede convertir
                            pdf_texts.append({
                                'name': doc.nom_original,
                                'text': pdf_text
                            })
                            documents_info.append({
                                'id': doc.id,
                                'name': doc.nom_original,
                                'type': 'pdf',
                                'method': 'text_fallback',
                                'chars_extracted': len(pdf_text)
                            })
                    else:
                        # Texto suficiente - no necesita Vision
                        pdf_texts.append({
                            'name': doc.nom_original,
                            'text': pdf_text
                        })
                        documents_info.append({
                            'id': doc.id,
                            'name': doc.nom_original,
                            'type': 'pdf',
                            'method': 'text_extraction',
                            'chars_extracted': len(pdf_text),
                            'info_found': evaluation.get('info_found', [])
                        })
                        logger.info(f"PDF {doc.nom_original}: texto suficiente ({len(pdf_text)} chars)")
                else:
                    # Texto insuficiente desde el inicio - convertir a imagenes
                    pdf_images = convert_pdf_to_images(file_path, max_pages=3)
                    if pdf_images:
                        pdf_temp_images.extend(pdf_images)
                        image_paths.extend(pdf_images)
                        documents_info.append({
                            'id': doc.id,
                            'name': doc.nom_original,
                            'type': 'pdf',
                            'method': 'vision',
                            'pages_converted': len(pdf_images)
                        })
                        logger.info(f"PDF {doc.nom_original}: convertido a {len(pdf_images)} imagenes")
                    else:
                        documents_info.append({
                            'id': doc.id,
                            'name': doc.nom_original,
                            'type': 'pdf',
                            'method': 'failed',
                            'error': 'No se pudo extraer texto ni convertir a imagenes'
                        })

        # Verificar que hay algo que analizar
        if not image_paths and not pdf_texts:
            return {
                'success': False,
                'error': 'No se encontraron documentos validos para analizar',
                'analysis': None
            }

        # Construir el prompt de analisis
        product_name = expedition.nom_article or 'No especificado'
        product_description = expedition.description or 'No especificada'

        # Obtener direccion de la expedicion (origen -> destino)
        direction = expedition.direction
        if direction == 'FR_DZ':
            pais_origen = 'Francia (Union Europea)'
            pais_destino = 'Argelia'
            tipo_operacion = 'EXPORTACION desde la UE'
        elif direction == 'DZ_FR':
            pais_origen = 'Argelia'
            pais_destino = 'Francia (Union Europea)'
            tipo_operacion = 'IMPORTACION a la UE'
        else:
            pais_origen = 'No especificado'
            pais_destino = 'No especificado'
            tipo_operacion = 'No especificado'

        # Construir seccion de texto de PDFs si hay
        pdf_text_section = ""
        if pdf_texts:
            pdf_text_section = "\n\nTEXTO EXTRAIDO DE DOCUMENTOS PDF:\n"
            for pdf_info in pdf_texts:
                # Limitar texto a 3000 chars por PDF para no exceder contexto
                text = pdf_info['text'][:3000]
                if len(pdf_info['text']) > 3000:
                    text += "\n[... texto truncado ...]"
                pdf_text_section += f"\n=== {pdf_info['name']} ===\n{text}\n"

        # Determinar si hay imagenes para analizar
        has_images = len(image_paths) > 0

        if has_images:
            # Prompt para analisis con imagenes (y posiblemente texto de PDFs)
            analysis_prompt = f"""Eres un experto en clasificacion aduanera TARIC de la Union Europea.
Analiza la informacion proporcionada para clasificar este producto.

EXPEDICION:
- Tipo de operacion: {tipo_operacion}
- Pais de origen: {pais_origen}
- Pais de destino: {pais_destino}

PRODUCTO:
- Nombre: {product_name}
- Descripcion: {product_description}
{pdf_text_section}

## PARTE 1: ANALISIS DEL PRODUCTO

Analiza las imagenes y extrae:

1. **Tipo de producto**: Que es exactamente (categoria general y especifica)
2. **Materiales/Composicion**: De que esta hecho (%, si es visible)
3. **Funcion principal**: Para que sirve, uso previsto
4. **Caracteristicas tecnicas**: Dimensiones, peso, especificaciones visibles
5. **Origen**: Pais de fabricacion si aparece (Made in...)
6. **Marcas/Etiquetas**: Marcas comerciales, certificaciones (CE, ISO...)
7. **Componentes**: Partes o accesorios visibles

## PARTE 2: PROPUESTA DE CLASIFICACION TARIC

Basandote en el analisis anterior, proporciona:

### CODIGO TARIC PROPUESTO
Proporciona hasta 3 codigos TARIC candidatos, ordenados por probabilidad:

**Propuesta 1** (mas probable):
- Codigo TARIC (10 digitos): XXXXXXXXXX
- Codigo NC (8 digitos): XXXXXXXX
- Codigo SH (6 digitos): XXXXXX
- Descripcion oficial: [descripcion de la partida]
- Probabilidad de acierto: XX%
- Justificacion: [explica por que este codigo es el mas adecuado]

**Propuesta 2** (alternativa):
- Codigo TARIC: ...
- Probabilidad: XX%
- Justificacion: ...

**Propuesta 3** (si aplica):
- Codigo TARIC: ...
- Probabilidad: XX%
- Justificacion: ...

### DUDAS O INFORMACION FALTANTE
Si tienes dudas o necesitas mas informacion para una clasificacion mas precisa, indica:
- Que informacion adicional necesitarias
- Que caracteristicas del producto no has podido determinar
- Que preguntas harias al usuario para mejorar la clasificacion

### NOTAS IMPORTANTES PARA ESTA EXPEDICION ({tipo_operacion})
- Menciona si hay restricciones, licencias o certificados especiales para este tipo de producto
- Indica si existen acuerdos comerciales entre {pais_origen} y {pais_destino} que afecten los aranceles
- Senala si el producto requiere controles especiales (sanitarios, fitosanitarios, seguridad, etc.)
- Para EXPORTACION: menciona si hay restricciones de exportacion desde la UE
- Para IMPORTACION: menciona si hay contingentes, antidumping o medidas especiales

IMPORTANTE:
- Combina la informacion de las imagenes con el texto de los documentos PDF
- Solo reporta informacion que puedas confirmar
- Se preciso y honesto sobre tu nivel de certeza
- Si no estas seguro, indica claramente tus dudas
- Ten en cuenta que es una operacion {pais_origen} -> {pais_destino}
"""
            # Analizar con GPT-4o Vision
            result = analyze_images_with_vision(
                image_paths=image_paths,
                prompt=analysis_prompt,
                api_key=api_key
            )
        else:
            # Solo texto de PDFs - no necesita Vision, usar modelo de texto
            analysis_prompt = f"""Eres un experto en clasificacion aduanera TARIC de la Union Europea.
Analiza la informacion proporcionada para clasificar este producto.

EXPEDICION:
- Tipo de operacion: {tipo_operacion}
- Pais de origen: {pais_origen}
- Pais de destino: {pais_destino}

PRODUCTO:
- Nombre: {product_name}
- Descripcion: {product_description}
{pdf_text_section}

## PARTE 1: ANALISIS DEL PRODUCTO

Extrae del texto:

1. **Tipo de producto**: Que es exactamente (categoria general y especifica)
2. **Materiales/Composicion**: De que esta hecho (%, si aparece)
3. **Funcion principal**: Para que sirve, uso previsto
4. **Caracteristicas tecnicas**: Dimensiones, peso, especificaciones
5. **Origen**: Pais de fabricacion si aparece
6. **Marcas/Etiquetas**: Marcas comerciales, certificaciones (CE, ISO...)
7. **Componentes**: Partes o accesorios mencionados

## PARTE 2: PROPUESTA DE CLASIFICACION TARIC

Basandote en el analisis anterior, proporciona:

### CODIGO TARIC PROPUESTO
Proporciona hasta 3 codigos TARIC candidatos, ordenados por probabilidad:

**Propuesta 1** (mas probable):
- Codigo TARIC (10 digitos): XXXXXXXXXX
- Codigo NC (8 digitos): XXXXXXXX
- Codigo SH (6 digitos): XXXXXX
- Descripcion oficial: [descripcion de la partida]
- Probabilidad de acierto: XX%
- Justificacion: [explica por que este codigo es el mas adecuado]

**Propuesta 2** (alternativa):
- Codigo TARIC: ...
- Probabilidad: XX%
- Justificacion: ...

**Propuesta 3** (si aplica):
- Codigo TARIC: ...
- Probabilidad: XX%
- Justificacion: ...

### DUDAS O INFORMACION FALTANTE
Si tienes dudas o necesitas mas informacion para una clasificacion mas precisa, indica:
- Que informacion adicional necesitarias
- Que caracteristicas del producto no has podido determinar
- Que preguntas harias al usuario para mejorar la clasificacion

### NOTAS IMPORTANTES PARA ESTA EXPEDICION ({tipo_operacion})
- Menciona si hay restricciones, licencias o certificados especiales para este tipo de producto
- Indica si existen acuerdos comerciales entre {pais_origen} y {pais_destino} que afecten los aranceles
- Senala si el producto requiere controles especiales (sanitarios, fitosanitarios, seguridad, etc.)
- Para EXPORTACION: menciona si hay restricciones de exportacion desde la UE
- Para IMPORTACION: menciona si hay contingentes, antidumping o medidas especiales

IMPORTANTE:
- Solo reporta informacion que aparezca en el texto
- Si algo no esta mencionado, indica "No especificado"
- Se preciso y honesto sobre tu nivel de certeza
- Ten en cuenta que es una operacion {pais_origen} -> {pais_destino}
- Si no estas seguro, indica claramente tus dudas
"""
            # Usar modelo de texto (sin vision) - mas barato
            result = analyze_text_only(
                prompt=analysis_prompt,
                api_key=api_key
            )

        # Limpiar imagenes temporales de PDFs
        if pdf_temp_images:
            cleanup_temp_images(pdf_temp_images)

        # Agregar informacion adicional al resultado
        result['expedition_id'] = expedition_id
        result['documents_analyzed'] = documents_info
        result['product_name'] = product_name
        result['pdf_texts_extracted'] = len(pdf_texts)

        return result

    except Exception as e:
        logger.error(f"Error en analyze_documents: {e}")
        return {
            'success': False,
            'error': str(e),
            'analysis': None
        }


# Definicion de la tool para el registry
TOOL_DEFINITION = {
    'name': 'analyze_documents',
    'description': (
        "Analiza las fotos y documentos PDF de la expedicion usando vision por IA (GPT-4o). "
        "Extrae informacion del producto (tipo, materiales, funcion, especificaciones, origen) "
        "y PROPONE CODIGOS TARIC con probabilidad de acierto y justificacion. "
        "Tambien indica dudas o informacion faltante para mejorar la clasificacion. "
        "Usa esta tool cuando el usuario haya subido documentos para obtener una propuesta de clasificacion."
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'expedition_id': {
                'type': 'integer',
                'description': 'ID de la expedicion cuyos documentos se analizaran'
            },
            'document_ids': {
                'type': 'array',
                'items': {'type': 'integer'},
                'description': 'Lista de IDs de documentos especificos a analizar (opcional, si no se pasa analiza todos)'
            }
        },
        'required': ['expedition_id']
    },
    'function': analyze_documents,
    'category': 'classification'
}
