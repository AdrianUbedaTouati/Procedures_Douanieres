#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para ejecutar todos los tests del proyecto ChatBot IA.

Uso:
    python run_tests.py              # Ejecutar todos los tests
    python run_tests.py -v           # Modo verbose
    python run_tests.py --quick      # Solo tests rapidos (sin integracion)
    python run_tests.py --coverage   # Con reporte de cobertura
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

# Fix encoding en Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Configurar el entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Colores para la terminal (compatible con Windows)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Simbolos ASCII compatibles
CHECK = '[OK]'
CROSS = '[FAIL]'


def print_header():
    """Imprime el encabezado del script."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}   ChatBot IA - Test Suite{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")


def print_section(title):
    """Imprime un titulo de seccion."""
    print(f"\n{Colors.YELLOW}--- {title} ---{Colors.END}\n")


def run_django_check():
    """Ejecuta django check para verificar configuracion."""
    print_section("Verificando configuracion Django")
    result = subprocess.run(
        [sys.executable, 'manage.py', 'check'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"{Colors.GREEN}{CHECK} Configuracion Django correcta{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}{CROSS} Error en configuracion Django:{Colors.END}")
        print(result.stderr)
        return False


def run_tests(verbose=False, pattern=None, coverage=False):
    """Ejecuta los tests de Django."""
    print_section("Ejecutando Tests")

    cmd = [sys.executable, 'manage.py', 'test', 'tests']

    if verbose:
        cmd.append('-v')
        cmd.append('2')
    else:
        cmd.append('-v')
        cmd.append('1')

    if pattern:
        cmd.extend(['--pattern', pattern])

    # Mostrar el comando que se ejecutara
    print(f"{Colors.BLUE}Comando: {' '.join(cmd)}{Colors.END}\n")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def run_specific_tests(test_module, verbose=False):
    """Ejecuta tests de un modulo especifico."""
    print_section(f"Tests: {test_module}")

    cmd = [sys.executable, 'manage.py', 'test', f'tests.{test_module}']

    if verbose:
        cmd.append('-v')
        cmd.append('2')

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def run_quick_tests(verbose=False):
    """Ejecuta solo tests rapidos (sin integracion externa)."""
    print_section("Tests Rapidos (sin integracion)")

    modules = [
        'test_authentication',
        'test_core',
        'test_chat',
    ]

    all_passed = True
    for module in modules:
        passed = run_specific_tests(module, verbose)
        if not passed:
            all_passed = False

    return all_passed


def print_summary(passed, start_time):
    """Imprime el resumen de los tests."""
    duration = datetime.now() - start_time

    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}RESUMEN{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")

    if passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}{CHECK} TODOS LOS TESTS PASARON{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}{CROSS} ALGUNOS TESTS FALLARON{Colors.END}")

    print(f"\n{Colors.BLUE}Duracion: {duration.total_seconds():.2f} segundos{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Ejecutar tests del proyecto ChatBot IA'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Modo verbose (mas detalles)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Solo tests rapidos (sin integracion)'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generar reporte de cobertura'
    )
    parser.add_argument(
        '--module',
        type=str,
        help='Ejecutar solo un modulo de tests (ej: test_authentication)'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Solo verificar configuracion, sin ejecutar tests'
    )

    args = parser.parse_args()

    start_time = datetime.now()
    print_header()

    # Verificar configuracion Django
    if not run_django_check():
        print(f"\n{Colors.RED}Abortando: Configuracion Django invalida{Colors.END}\n")
        sys.exit(1)

    if args.check_only:
        print(f"\n{Colors.GREEN}Verificacion completada.{Colors.END}\n")
        sys.exit(0)

    # Ejecutar tests
    if args.module:
        passed = run_specific_tests(args.module, args.verbose)
    elif args.quick:
        passed = run_quick_tests(args.verbose)
    else:
        passed = run_tests(args.verbose, coverage=args.coverage)

    # Resumen
    print_summary(passed, start_time)

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
