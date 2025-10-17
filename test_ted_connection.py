# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar la conexión con TED API
"""

import socket
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import io

# Configurar salida UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_dns_resolution():
    """Test 1: Verificar resolución DNS"""
    print("\n" + "="*60)
    print("TEST 1: Resolución DNS")
    print("="*60)

    hosts = [
        "api.ted.europa.eu",
        "ted.europa.eu",
        "google.com"  # Control
    ]

    for host in hosts:
        try:
            ip = socket.gethostbyname(host)
            print(f"✓ {host} → {ip}")
        except socket.gaierror as e:
            print(f"✗ {host} → ERROR: {e}")

    return True


def test_basic_connectivity():
    """Test 2: Conectividad básica con requests"""
    print("\n" + "="*60)
    print("TEST 2: Conectividad básica")
    print("="*60)

    urls = [
        "https://ted.europa.eu",
        "https://api.ted.europa.eu",
        "https://www.google.com"  # Control
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"✓ {url} → Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"✗ {url} → ERROR: {e}")

    return True


def test_api_search():
    """Test 3: Probar endpoint de búsqueda de TED API"""
    print("\n" + "="*60)
    print("TEST 3: TED API Search Endpoint")
    print("="*60)

    url = "https://api.ted.europa.eu/v3/notices/search"

    # Query simple
    payload = {
        "query": "place-of-performance=ESP",
        "fields": ["ND"]
    }

    try:
        print(f"URL: {url}")
        print(f"Payload: {payload}")

        response = requests.post(url, json=payload, timeout=30)
        print(f"✓ Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response OK - Keys: {list(data.keys())}")
        else:
            print(f"✗ Error: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"✗ ERROR: {e}")
        print(f"   Tipo: {type(e).__name__}")

    return True


def test_with_retries():
    """Test 4: Probar con reintentos automáticos"""
    print("\n" + "="*60)
    print("TEST 4: Conexión con reintentos automáticos")
    print("="*60)

    # Crear sesión con reintentos
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    url = "https://api.ted.europa.eu/v3/notices/search"
    payload = {
        "query": "place-of-performance=ESP",
        "fields": ["ND"]
    }

    try:
        print(f"Intentando POST a {url}...")
        response = session.post(url, json=payload, timeout=30)
        print(f"✓ Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response OK")
        else:
            print(f"✗ Error: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"✗ ERROR: {e}")
        print(f"   Tipo: {type(e).__name__}")

    return True


def test_proxy_settings():
    """Test 5: Verificar configuración de proxy"""
    print("\n" + "="*60)
    print("TEST 5: Configuración de Proxy")
    print("="*60)

    import os

    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']

    has_proxy = False
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"  {var} = {value}")
            has_proxy = True

    if not has_proxy:
        print("  No hay variables de proxy configuradas")

    return True


def main():
    print("\n" + "#"*60)
    print("#  DIAGNÓSTICO DE CONEXIÓN A TED API")
    print("#"*60)

    try:
        test_dns_resolution()
        test_basic_connectivity()
        test_proxy_settings()
        test_api_search()
        test_with_retries()

        print("\n" + "#"*60)
        print("#  DIAGNÓSTICO COMPLETADO")
        print("#"*60)
        print("\nSi todos los tests pasan, la conexión funciona correctamente.")
        print("Si hay errores, revisa:")
        print("  1. Tu conexión a Internet")
        print("  2. Configuración de firewall")
        print("  3. Configuración de proxy (si aplica)")
        print("  4. Configuración DNS")

    except Exception as e:
        print(f"\n✗ ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
