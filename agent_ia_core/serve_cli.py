# -*- coding: utf-8 -*-
"""
CLI interactivo para consultas al sistema RAG eForms.
Permite hacer preguntas al agente y ver respuestas con citas.
"""

from __future__ import annotations
import sys
from pathlib import Path
import logging
from typing import Optional, Dict, Any

# Importar módulos propios
sys.path.append(str(Path(__file__).parent))
from agent_graph import create_agent
from config import (
    LLM_PROVIDER,
    LLM_MODEL,
    DEFAULT_K,
    USE_GRADING,
    USE_XML_VERIFICATION
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EFormsRAGCLI:
    """
    CLI interactivo para el sistema RAG eForms.
    """

    def __init__(
        self,
        k_retrieve: int = DEFAULT_K,
        use_grading: bool = USE_GRADING,
        use_verification: bool = USE_XML_VERIFICATION,
        verbose: bool = False
    ):
        """
        Inicializa el CLI.

        Args:
            k_retrieve: Número de documentos a recuperar
            use_grading: Activar grading de relevancia
            use_verification: Activar verificación XML
            verbose: Mostrar información detallada
        """
        self.k_retrieve = k_retrieve
        self.use_grading = use_grading
        self.use_verification = use_verification
        self.verbose = verbose

        # Banner de bienvenida
        self._print_banner()

        # Inicializar agente
        print(f"\n🔧 Inicializando agente RAG...")
        print(f"   Proveedor LLM: {LLM_PROVIDER}")
        print(f"   Modelo: {LLM_MODEL}")
        print(f"   Documentos a recuperar: {k_retrieve}")
        print(f"   Grading: {'✓' if use_grading else '✗'}")
        print(f"   Verificación XML: {'✓' if use_verification else '✗'}")

        try:
            self.agent = create_agent(
                k_retrieve=k_retrieve,
                use_grading=use_grading,
                use_verification=use_verification
            )
            print("✅ Agente inicializado correctamente\n")
        except Exception as e:
            print(f"❌ Error inicializando agente: {e}")
            sys.exit(1)

    def _print_banner(self):
        """Imprime el banner de bienvenida."""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           eForms RAG - Sistema de Consulta de                ║
║              Licitaciones Públicas de la UE                   ║
║                                                               ║
║   Agente basado en LangGraph con verificación determinista   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def run(self):
        """
        Ejecuta el bucle principal del CLI.
        """
        print("💬 Escribe tu pregunta sobre licitaciones eForms")
        print("   Comandos especiales:")
        print("   - /help: Mostrar ayuda")
        print("   - /config: Mostrar configuración actual")
        print("   - /exit o /quit: Salir")
        print()

        while True:
            try:
                # Leer pregunta del usuario
                question = input("🔍 Pregunta: ").strip()

                if not question:
                    continue

                # Comandos especiales
                if question.startswith("/"):
                    if question in ["/exit", "/quit"]:
                        print("\n👋 ¡Hasta luego!")
                        break
                    elif question == "/help":
                        self._print_help()
                        continue
                    elif question == "/config":
                        self._print_config()
                        continue
                    else:
                        print(f"❌ Comando desconocido: {question}")
                        print("   Usa /help para ver comandos disponibles")
                        continue

                # Ejecutar consulta
                print("\n⏳ Procesando consulta...")
                result = self.agent.query(question)

                # Mostrar respuesta
                self._print_result(result)

            except KeyboardInterrupt:
                print("\n\n👋 Interrupción del usuario. ¡Hasta luego!")
                break
            except Exception as e:
                logger.error(f"Error procesando consulta: {e}", exc_info=True)
                print(f"\n❌ Error: {e}")
                print("   Por favor, intenta de nuevo.\n")

    def _print_result(self, result: Dict[str, Any]):
        """
        Imprime el resultado de una consulta.

        Args:
            result: Diccionario con respuesta y metadatos
        """
        print("\n" + "="*70)
        print("📝 RESPUESTA:")
        print("="*70)
        print(result["answer"])
        print()

        # Mostrar documentos usados si verbose
        if self.verbose and result.get("documents"):
            print("-"*70)
            print(f"📚 DOCUMENTOS USADOS ({len(result['documents'])}):")
            print("-"*70)
            for i, doc in enumerate(result["documents"], 1):
                print(f"{i}. [{doc['section']}] {doc['ojs_notice_id']}")
                if doc.get("content"):
                    preview = doc["content"][:100].replace("\n", " ")
                    print(f"   {preview}...")
            print()

        # Mostrar campos verificados
        if result.get("verified_fields"):
            print("-"*70)
            print(f"✅ CAMPOS VERIFICADOS ({len(result['verified_fields'])}):")
            print("-"*70)
            for field in result["verified_fields"]:
                print(f"• {field['name']}: {field['value']}")
                if self.verbose:
                    print(f"  └─ Fuente: {field['source']}")
                    print(f"  └─ XPath: {field['xpath']}")
            print()

        # Metadatos si verbose
        if self.verbose:
            print("-"*70)
            print("ℹ️  METADATOS:")
            print("-"*70)
            print(f"• Ruta: {result.get('route', 'N/A')}")
            print(f"• Iteraciones: {result.get('iterations', 0)}")
            print()

        print("="*70)
        print()

    def _print_help(self):
        """Imprime la ayuda del CLI."""
        help_text = """
╔═══════════════════════════════════════════════════════════════╗
║                          AYUDA                                ║
╚═══════════════════════════════════════════════════════════════╝

COMANDOS DISPONIBLES:
  /help         Mostrar esta ayuda
  /config       Mostrar configuración actual del agente
  /exit, /quit  Salir del programa

EJEMPLOS DE CONSULTAS:
  • ¿Cuál es el presupuesto de los servicios de SAP?
  • ¿Qué licitaciones hay en Valencia relacionadas con software?
  • Busca contratos de mantenimiento informático con presupuesto superior a 500.000 EUR
  • ¿Cuál es el deadline del aviso 00668461-2025?
  • ¿Qué criterios de adjudicación tienen las licitaciones de desarrollo de software?

FORMATO DE RESPUESTAS:
  Las respuestas incluyen citas en el formato:
  [ID_AVISO | sección | archivo_xml]

  Ejemplo: [00668461-2025 | budget | 668461-2025.xml]

FILTROS (experimentales):
  Puedes mencionar filtros específicos en tu pregunta:
  • Región: "en Valencia", "en Madrid"
  • CPV: "CPV 72267100"
  • Presupuesto: "más de 1 millón EUR"
  • Fecha: "publicados en 2025"
"""
        print(help_text)

    def _print_config(self):
        """Imprime la configuración actual."""
        config_text = f"""
╔═══════════════════════════════════════════════════════════════╗
║                     CONFIGURACIÓN ACTUAL                      ║
╚═══════════════════════════════════════════════════════════════╝

PROVEEDOR LLM:
  • Proveedor: {LLM_PROVIDER}
  • Modelo: {LLM_MODEL}

PARÁMETROS DE RECUPERACIÓN:
  • Documentos (k): {self.k_retrieve}
  • Grading activado: {self.use_grading}
  • Verificación XML activada: {self.use_verification}

MODO:
  • Verbose: {self.verbose}
"""
        print(config_text)


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CLI interactivo para consultas sobre licitaciones eForms"
    )
    parser.add_argument(
        "-k", "--k-retrieve",
        type=int,
        default=DEFAULT_K,
        help=f"Número de documentos a recuperar (default: {DEFAULT_K})"
    )
    parser.add_argument(
        "--no-grading",
        action="store_true",
        help="Desactivar grading de relevancia"
    )
    parser.add_argument(
        "--no-verification",
        action="store_true",
        help="Desactivar verificación XML"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar información detallada"
    )

    args = parser.parse_args()

    # Crear y ejecutar CLI
    cli = EFormsRAGCLI(
        k_retrieve=args.k_retrieve,
        use_grading=not args.no_grading,
        use_verification=not args.no_verification,
        verbose=args.verbose
    )

    cli.run()


if __name__ == "__main__":
    main()
