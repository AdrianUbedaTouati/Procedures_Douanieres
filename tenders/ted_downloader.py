# -*- coding: utf-8 -*-
"""
Servicio para descargar licitaciones desde la API de TED y guardarlas en la BD.
Adaptado de Agent_IA/src/descarga_xml.py
"""

import requests
from pathlib import Path
from datetime import date, timedelta
import re
import time
from typing import Optional, Dict, Any, List
from django.conf import settings
from .models import Tender
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# URLs y configuración
SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

# Configuración por defecto
DEFAULT_CPV = "classification-cpv=72*"  # Servicios de TI (todos los códigos 72*)
DEFAULT_PLACE = "place-of-performance=ESP"
DEFAULT_NOTICE_TYPE = "notice-type=cn-standard"
DEFAULT_DAYS_BACK = 30
DEFAULT_WINDOW_DAYS = 7
DEFAULT_MAX_DOWNLOAD = 50
TIMEOUT = 60
DOWNLOAD_DELAY = 1.2  # segundos entre requests
MAX_RETRIES = 3  # Número máximo de reintentos
BACKOFF_FACTOR = 2  # Factor de backoff exponencial

# Regex para números de publicación
PUBNUM_RE = re.compile(r"\b\d{6,8}-\d{4}\b")


def create_session_with_retries() -> requests.Session:
    """
    Crea una sesión de requests con reintentos automáticos configurados.
    Maneja errores de conexión, timeouts y errores DNS.
    """
    session = requests.Session()

    # Configurar estrategia de reintentos
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
        raise_on_status=False
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Headers comunes
    session.headers.update({
        'User-Agent': 'TenderAI-Platform/1.0 (Python requests)',
        'Accept': 'application/json',
    })

    return session


def http_post(url: str, session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
    """POST con delay para respetar rate limits y manejo de errores"""
    time.sleep(DOWNLOAD_DELAY)

    if session is None:
        session = create_session_with_retries()

    try:
        response = session.post(url, **kwargs)
        return response
    except requests.exceptions.RequestException as e:
        # Mejorar el mensaje de error
        error_msg = str(e)
        if "Failed to resolve" in error_msg or "getaddrinfo failed" in error_msg:
            raise ConnectionError(
                f"No se pudo resolver el nombre de dominio. "
                f"Verifica tu conexión a Internet y configuración de DNS. "
                f"Error original: {error_msg}"
            )
        elif "Connection refused" in error_msg:
            raise ConnectionError(
                f"Conexión rechazada por el servidor. "
                f"Verifica tu firewall o configuración de proxy. "
                f"Error original: {error_msg}"
            )
        else:
            raise ConnectionError(f"Error de conexión: {error_msg}")


def http_get(url: str, session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
    """GET con delay para respetar rate limits y manejo de errores"""
    time.sleep(DOWNLOAD_DELAY)

    if session is None:
        session = create_session_with_retries()

    try:
        response = session.get(url, **kwargs)
        return response
    except requests.exceptions.RequestException as e:
        # Mejorar el mensaje de error
        error_msg = str(e)
        if "Failed to resolve" in error_msg or "getaddrinfo failed" in error_msg:
            raise ConnectionError(
                f"No se pudo resolver el nombre de dominio. "
                f"Verifica tu conexión a Internet y configuración de DNS. "
                f"Error original: {error_msg}"
            )
        elif "Connection refused" in error_msg:
            raise ConnectionError(
                f"Conexión rechazada por el servidor. "
                f"Verifica tu firewall o configuración de proxy. "
                f"Error original: {error_msg}"
            )
        else:
            raise ConnectionError(f"Error de conexión: {error_msg}")


def date_range_clause(start_d: date, end_d: date) -> str:
    """Sintaxis Expert: publication-date=(YYYYMMDD <> YYYYMMDD)"""
    return f"publication-date=({start_d:%Y%m%d} <> {end_d:%Y%m%d})"


def expert_query_with_range(start_d: date, end_d: date, cpv_expr: str, place: str, notice_type: str) -> str:
    """Construir query en sintaxis Expert"""
    parts = [notice_type, cpv_expr, place, date_range_clause(start_d, end_d)]
    return " and ".join(parts)


def extract_publication_numbers(obj: Any) -> List[str]:
    """
    Recorre el JSON y extrae cualquier string con pinta de número de publicación
    (eForms 8 dígitos o TEDXML 6).
    """
    found: List[str] = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            for m in PUBNUM_RE.findall(x):
                found.append(m)

    walk(obj)

    # Únicos conservando orden
    seen, uniq = set(), []
    for nd in found:
        if nd not in seen:
            seen.add(nd)
            uniq.append(nd)
    return uniq


def download_xml_content(pub_number: str) -> bytes:
    """
    Descarga el XML de un aviso por número de publicación.
    Formato: https://ted.europa.eu/en/notice/{publication-number}/xml
    """
    url = f"https://ted.europa.eu/en/notice/{pub_number}/xml"
    r = http_get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


def parse_xml_to_tender(xml_content: bytes, pub_number: str) -> Optional[Dict[str, Any]]:
    """
    Parsea el XML y extrae los datos necesarios para crear un Tender.
    Esta es una implementación básica - ajusta según la estructura real del XML.
    """
    try:
        root = ET.fromstring(xml_content)

        # Namespaces comunes en TED XML
        ns = {
            'ted': 'http://publications.europa.eu/resource/schema/ted/R2.0.9/publication',
            'n2016': 'http://publications.europa.eu/resource/schema/ted/2016/nuts',
        }

        # Extraer datos básicos (ajustar según estructura real)
        tender_data = {
            'ojs_notice_id': pub_number,
            'title': '',
            'description': '',
            'short_description': '',
            'budget_amount': None,
            'currency': 'EUR',
            'cpv_codes': [],
            'nuts_regions': [],
            'contract_type': 'services',
            'buyer_name': '',
            'buyer_type': '',
            'publication_date': date.today(),
            'tender_deadline_date': None,
            'procedure_type': 'open',
        }

        # Intentar extraer título
        for title_elem in root.iter():
            if 'TITLE' in title_elem.tag.upper():
                if title_elem.text:
                    tender_data['title'] = title_elem.text[:500]
                    break

        # Intentar extraer códigos CPV
        for cpv_elem in root.iter():
            if 'CPV' in cpv_elem.tag.upper():
                cpv_code = cpv_elem.get('CODE', '')
                if cpv_code and cpv_code not in tender_data['cpv_codes']:
                    tender_data['cpv_codes'].append(cpv_code[:4])  # Primeros 4 dígitos

        # Intentar extraer regiones NUTS
        for nuts_elem in root.iter():
            if 'NUTS' in nuts_elem.tag.upper():
                nuts_code = nuts_elem.get('CODE', '')
                if nuts_code and nuts_code not in tender_data['nuts_regions']:
                    tender_data['nuts_regions'].append(nuts_code)

        # Si no tenemos título, usar el pub_number
        if not tender_data['title']:
            tender_data['title'] = f"Licitación {pub_number}"

        # Si no tenemos descripción, usar el título
        tender_data['short_description'] = tender_data['title'][:500]
        tender_data['description'] = tender_data['title']

        # Buyer name por defecto
        if not tender_data['buyer_name']:
            tender_data['buyer_name'] = 'Organismo público (por determinar)'

        return tender_data

    except Exception as e:
        print(f"Error parseando XML {pub_number}: {e}")
        return None


def search_tenders_by_date_windows(
    days_back: int = DEFAULT_DAYS_BACK,
    cpv_expr: str = DEFAULT_CPV,
    place: str = DEFAULT_PLACE,
    notice_type: str = DEFAULT_NOTICE_TYPE,
    window_days: int = DEFAULT_WINDOW_DAYS,
    max_results: int = DEFAULT_MAX_DOWNLOAD,
    progress_callback=None,
    session: Optional[requests.Session] = None
) -> Dict[str, Any]:
    """
    Busca licitaciones en ventanas de fechas.
    Retorna: dict con pub_numbers, total_range, analyzed_range, remaining_range
    """
    # Crear sesión si no se proporciona
    if session is None:
        session = create_session_with_retries()

    all_nd: List[str] = []
    today = date.today()
    total_start = today - timedelta(days=days_back)
    total_end = today

    analyzed_start: Optional[date] = None
    analyzed_end: Optional[date] = None
    remaining_start: Optional[date] = None
    remaining_end: Optional[date] = None

    win_end = total_end
    while win_end > total_start:
        win_start = max(total_start, win_end - timedelta(days=window_days))
        q = expert_query_with_range(win_start, win_end, cpv_expr, place, notice_type)

        if progress_callback:
            progress_callback({
                'type': 'window',
                'start': str(win_start),
                'end': str(win_end),
                'total': len(all_nd)
            })

        payload = {"query": q, "fields": ["ND"]}
        resp = http_post(SEARCH_URL, session=session, json=payload, timeout=TIMEOUT)

        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            raise RuntimeError(f"Search API error {resp.status_code}: {err}")

        data = resp.json()
        nd_page = extract_publication_numbers(data)

        # Deduplicar
        added = 0
        for nd in nd_page:
            if nd not in all_nd:
                all_nd.append(nd)
                added += 1

        if added:
            analyzed_end = analyzed_end or win_end
            analyzed_start = win_start

        if progress_callback:
            progress_callback({
                'type': 'window_result',
                'added': added,
                'total': len(all_nd)
            })

        # Si ya tenemos suficientes, parar
        if len(all_nd) >= max_results * 3:
            remaining_start = total_start
            remaining_end = win_start - timedelta(days=1)
            break

        # Siguiente ventana
        win_end = win_start - timedelta(days=1)

    if remaining_start is None:
        remaining_start, remaining_end = None, None

    return {
        "pub_numbers": all_nd,
        "total_range": (total_start, total_end),
        "analyzed_range": (analyzed_start or total_end, analyzed_end or total_end),
        "remaining_range": (remaining_start, remaining_end),
    }


def download_and_save_tenders(
    days_back: int = DEFAULT_DAYS_BACK,
    max_download: int = DEFAULT_MAX_DOWNLOAD,
    cpv_codes: Optional[List[str]] = None,
    place: Optional[str] = None,
    notice_type: Optional[str] = None,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Función principal: busca, descarga y guarda licitaciones en la BD.

    Args:
        days_back: Días hacia atrás para buscar
        max_download: Máximo de licitaciones a descargar
        cpv_codes: Lista de códigos CPV para filtrar (ej: ['72', '7226'])
        place: País/región (ej: 'ESP', 'FRA'). Si es None, usa DEFAULT_PLACE
        notice_type: Tipo de aviso (ej: 'cn-standard'). Si es None, usa DEFAULT_NOTICE_TYPE
        progress_callback: Función opcional para reportar progreso

    Returns:
        Dict con estadísticas: total_found, downloaded, saved, errors
    """
    # Crear sesión reutilizable con reintentos
    session = create_session_with_retries()

    # Construir expresión CPV
    if cpv_codes:
        cpv_expr = " or ".join([f"classification-cpv={code}*" for code in cpv_codes])
    else:
        cpv_expr = DEFAULT_CPV

    # Usar valores proporcionados o defaults
    place_expr = f"place-of-performance={place}" if place else DEFAULT_PLACE
    notice_type_expr = f"notice-type={notice_type}" if notice_type else DEFAULT_NOTICE_TYPE

    # 1. Buscar licitaciones
    if progress_callback:
        progress_callback({'type': 'start', 'message': '🚀 Conectando con TED API...'})

    try:
        search_res = search_tenders_by_date_windows(
            days_back=days_back,
            cpv_expr=cpv_expr,
            place=place_expr,
            notice_type=notice_type_expr,
            max_results=max_download,
            progress_callback=progress_callback,
            session=session
        )
    except ConnectionError as e:
        # Error de conexión detectado
        if progress_callback:
            progress_callback({
                'type': 'error',
                'message': str(e)
            })
        return {
            "total_found": 0,
            "downloaded": 0,
            "saved": 0,
            "errors": [str(e)],
            "date_range": (date.today(), date.today()),
        }
    except Exception as e:
        # Otro tipo de error
        error_msg = f"Error en la búsqueda: {str(e)}"
        if progress_callback:
            progress_callback({
                'type': 'error',
                'message': error_msg
            })
        return {
            "total_found": 0,
            "downloaded": 0,
            "saved": 0,
            "errors": [error_msg],
            "date_range": (date.today(), date.today()),
        }

    pub_numbers = search_res["pub_numbers"][:max_download]
    total_found = len(search_res["pub_numbers"])

    if progress_callback:
        progress_callback({
            'type': 'search_complete',
            'total_found': total_found,
            'to_download': len(pub_numbers)
        })

    # 2. Descargar y guardar
    downloaded = 0
    saved = 0
    errors = []

    for idx, pub_num in enumerate(pub_numbers, 1):
        try:
            if progress_callback:
                progress_callback({
                    'type': 'download',
                    'current': idx,
                    'total': len(pub_numbers),
                    'pub_number': pub_num
                })

            # Verificar si ya existe
            if Tender.objects.filter(ojs_notice_id=pub_num).exists():
                if progress_callback:
                    progress_callback({
                        'type': 'skip',
                        'pub_number': pub_num,
                        'reason': 'Ya existe en la base de datos'
                    })
                continue

            # Descargar XML
            xml_content = download_xml_content(pub_num)
            downloaded += 1

            # Parsear
            tender_data = parse_xml_to_tender(xml_content, pub_num)
            if not tender_data:
                errors.append(f"{pub_num}: Error parseando XML")
                if progress_callback:
                    progress_callback({
                        'type': 'error',
                        'pub_number': pub_num,
                        'message': 'Error parseando XML'
                    })
                continue

            # Guardar en BD
            tender = Tender.objects.create(**tender_data)
            saved += 1

            if progress_callback:
                progress_callback({
                    'type': 'saved',
                    'pub_number': pub_num,
                    'title': tender.title[:80],
                    'current': idx,
                    'total': len(pub_numbers),
                    'saved_count': saved
                })

        except ConnectionError as e:
            error_msg = f"{pub_num}: {str(e)}"
            errors.append(error_msg)
            if progress_callback:
                progress_callback({
                    'type': 'error',
                    'pub_number': pub_num,
                    'message': str(e)
                })
        except Exception as e:
            error_msg = f"{pub_num}: {str(e)}"
            errors.append(error_msg)
            if progress_callback:
                progress_callback({
                    'type': 'error',
                    'pub_number': pub_num,
                    'message': str(e)
                })

    if progress_callback:
        progress_callback({
            'type': 'complete',
            'saved': saved,
            'downloaded': downloaded,
            'errors': len(errors)
        })

    return {
        "total_found": total_found,
        "downloaded": downloaded,
        "saved": saved,
        "errors": errors,
        "date_range": search_res["total_range"],
    }
