# archivo: prueba.py
# -*- coding: utf-8 -*-

"""
Busca avisos en TED (Search API v3) y descarga sus XML por número de publicación.

Incluye:
  - Pausa fija de 1.2 s antes de CADA request (POST/GET)
  - "Paginación por ventanas de fechas" (sin usar size/from) para traer >10 resultados
  - Rango basado en últimos N días (DAYS_BACK) con ventanas de WINDOW_DAYS
  - Reporte de cobertura temporal: rango total, rango analizado y rango pendiente si se corta por límite
  - Sin filtro de 'deadline' (el endpoint público no documenta un campo de búsqueda para ello)

Requisitos:
  (.venv) pip install requests
"""

from __future__ import annotations
import requests
from pathlib import Path
from datetime import date, timedelta
import re
import time
from typing import Optional, Tuple, Dict, Any, List

SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

# --- CONFIG BÁSICA ---
CPV_EXPERT = "classification-cpv=7226*"       # servicios software (prefijo 7226*)
PLACE = "place-of-performance=ESP"            # España
NOTICE_TYPE = "notice-type=cn-standard"       # ofertas/Contract Notice

# --- CONTROL DE FECHAS (solo últimos N días) ---
DAYS_BACK = 1            # consulta desde hoy - N días hasta hoy
WINDOW_DAYS = 1           # tamaño de ventana para “paginar” por fechas

# --- DESCARGA Y LÍMITES ---
SAVE_DIR = Path("ted_xml") # carpeta destino para XML
MAX_TO_DOWNLOAD = 50       # límite de descargas por ejecución
TIMEOUT = 60

# --- PAUSA ENTRE REQUESTS ---
DOWNLOAD_DELAY = 1.2       # segundos de pausa ANTES de cada request (POST/GET)

# ------------------------------------------------
# HTTP helpers (con pausa fija)
# ------------------------------------------------

def http_post(url: str, **kwargs) -> requests.Response:
    time.sleep(DOWNLOAD_DELAY)
    return requests.post(url, **kwargs)

def http_get(url: str, **kwargs) -> requests.Response:
    time.sleep(DOWNLOAD_DELAY)
    return requests.get(url, **kwargs)

# ------------------------------------------------
# Construcción de expert queries
# ------------------------------------------------

def date_range_clause(start_d: date, end_d: date) -> str:
    """Sintaxis Expert: publication-date=(YYYYMMDD <> YYYYMMDD)"""
    return f"publication-date=({start_d:%Y%m%d} <> {end_d:%Y%m%d})"

def expert_query_with_range(start_d: date, end_d: date, cpv_expr: str) -> str:
    parts = [NOTICE_TYPE, cpv_expr, PLACE, date_range_clause(start_d, end_d)]
    return " and ".join(parts)

# ------------------------------------------------
# Parseo y utilidades
# ------------------------------------------------

PUBNUM_RE = re.compile(r"\b\d{6,8}-\d{4}\b")

def extract_publication_numbers(obj: Any) -> list[str]:
    """
    Recorre el JSON y extrae cualquier string con pinta de número de publicación
    (eForms 8 dígitos o TEDXML 6). No dependemos de nombres de campos.
    """
    found: list[str] = []
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, str):
            for m in PUBNUM_RE.findall(x): found.append(m)
    walk(obj)
    # únicos conservando orden
    seen, uniq = set(), []
    for nd in found:
        if nd not in seen:
            seen.add(nd)
            uniq.append(nd)
    return uniq

def download_xml(nd: str, dest_dir: Path) -> Path:
    """
    Descarga el XML directo de un aviso por número de publicación.
    Formato: https://ted.europa.eu/en/notice/{publication-number}/xml
    """
    url = f"https://ted.europa.eu/en/notice/{nd}/xml"
    r = http_get(url, timeout=TIMEOUT)
    r.raise_for_status()
    dest = dest_dir / f"{nd}.xml"
    dest.write_bytes(r.content)
    return dest

# ------------------------------------------------
# Búsqueda por ventanas y cobertura temporal
# ------------------------------------------------

def search_nds_by_date_windows(days_back: int, cpv_expr: str) -> Dict[str, Any]:
    """
    Hace múltiples llamadas a la Search API, dividiendo [hoy-days_back, hoy] en
    ventanas de WINDOW_DAYS días. Devuelve:
      {
        "pub_numbers": [...],
        "total_range": (start, end),
        "analyzed_range": (an_start, an_end),
        "remaining_range": (rem_start, rem_end)  # si se corta por límite
      }
    """
    all_nd: list[str] = []
    today = date.today()
    total_start = today - timedelta(days=days_back)
    total_end = today

    analyzed_start: Optional[date] = None
    analyzed_end: Optional[date] = None
    remaining_start: Optional[date] = None
    remaining_end: Optional[date] = None

    win_end = total_end
    while win_end > total_start:
        win_start = max(total_start, win_end - timedelta(days=WINDOW_DAYS))
        q = expert_query_with_range(win_start, win_end, cpv_expr=cpv_expr)
        print(f"Ventana: {win_start} <> {win_end} -> expert query:", q)

        payload = {"query": q, "fields": ["ND"]}
        resp = http_post(SEARCH_URL, json=payload, timeout=TIMEOUT)
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            raise RuntimeError(f"Search API error {resp.status_code}: {err}")

        data = resp.json()
        nd_page = extract_publication_numbers(data)

        # deduplicar manteniendo orden
        added = 0
        for nd in nd_page:
            if nd not in all_nd:
                all_nd.append(nd)
                added += 1

        if added:
            analyzed_end = analyzed_end or win_end
            analyzed_start = win_start

        print(f"  -> ND nuevos: {added} (total acumulado: {len(all_nd)})")

        # Si ya tenemos suficientes para descargar, paramos y guardamos rango restante
        if len(all_nd) >= MAX_TO_DOWNLOAD * 3:
            remaining_start = total_start
            remaining_end = win_start - timedelta(days=1)
            break

        # Pasar a la ventana anterior
        win_end = win_start - timedelta(days=1)

    # Si no se cortó por límite y se recorrió todo el rango
    if remaining_start is None:
        remaining_start, remaining_end = None, None

    return {
        "pub_numbers": all_nd,
        "total_range": (total_start, total_end),
        "analyzed_range": (analyzed_start or total_end, analyzed_end or total_end),
        "remaining_range": (remaining_start, remaining_end),
    }

# ------------------------------------------------
# MAIN
# ------------------------------------------------

def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Buscar ND en ventanas (últimos N días)
    try:
        search_res = search_nds_by_date_windows(DAYS_BACK, cpv_expr=CPV_EXPERT)
        pub_numbers: list[str] = search_res["pub_numbers"]
        total_start, total_end = search_res["total_range"]
        an_start, an_end = search_res["analyzed_range"]
        rem_start, rem_end = search_res["remaining_range"]
        print(f"Encontrados {len(pub_numbers)} ND (acumulado por ventanas).")
    except Exception as e:
        print("Error en búsqueda:", e)
        return

    # 2) Descargar XML (limitado por MAX_TO_DOWNLOAD)
    ok = fail = 0
    for nd in pub_numbers[:MAX_TO_DOWNLOAD]:
        try:
            p = download_xml(nd, SAVE_DIR)
            ok += 1
            print("Descargado:", p)
        except Exception as e:
            fail += 1
            print(f"Fallo descargando {nd}: {e}")

    # 3) Reporte de cobertura temporal
    print("\n=== Cobertura temporal ===")
    print(f"Rango total analizable:     {total_start:%Y-%m-%d} <> {total_end:%Y-%m-%d}")
    print(f"Rango realmente analizado:  {an_start:%Y-%m-%d} <> {an_end:%Y-%m-%d}")
    if ok >= MAX_TO_DOWNLOAD and rem_end is not None:
        print(f"Rango pendiente (no analizado): {total_start:%Y-%m-%d} <> {rem_end:%Y-%m-%d}")
    else:
        print("Rango pendiente: (ninguno; se cubrió el rango solicitado)")

    print("\n=== Resumen descargas ===")
    print(f"XML descargados: {ok} | fallidos: {fail}")
    print(f"Carpeta: {SAVE_DIR.resolve()}")

if __name__ == "__main__":
    main()
