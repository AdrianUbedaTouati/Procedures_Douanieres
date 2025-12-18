"""
Ollama Health Check Service
Verifica que Ollama esté instalado, corriendo y con los modelos necesarios
"""
import requests
import subprocess
from typing import Dict, Any, List
from datetime import datetime


class OllamaHealthChecker:
    """
    Service to check Ollama installation and health status
    """

    BASE_URL = "http://localhost:11434"
    RECOMMENDED_CHAT_MODELS = [
        "qwen2.5:72b",
        "llama3.3:70b",
        "llama3.1:70b",
        "deepseek-r1:14b",
        "mistral:7b"
    ]
    RECOMMENDED_EMBEDDING_MODELS = [
        "nomic-embed-text",
        "mxbai-embed-large"
    ]

    @staticmethod
    def _get_ollama_command():
        """
        Get the correct Ollama command path for Windows or Unix

        Returns:
            str: Path to ollama executable
        """
        import platform
        import os

        system = platform.system()

        if system == "Windows":
            # Try common Windows installation paths
            possible_paths = [
                r"C:\Program Files\Ollama\ollama.exe",
                r"C:\Program Files (x86)\Ollama\ollama.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe"),
                "ollama.exe",  # Try from PATH
                "ollama"  # Try from PATH without extension
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    return path

            # If not found in paths, try from PATH
            return "ollama"
        else:
            return "ollama"

    @staticmethod
    def check_ollama_installed() -> Dict[str, Any]:
        """
        Check if Ollama is installed on the system

        Returns:
            Dict with status and version info
        """
        try:
            ollama_cmd = OllamaHealthChecker._get_ollama_command()

            result = subprocess.run(
                [ollama_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                return {
                    "installed": True,
                    "version": version,
                    "message": f"Ollama instalado: {version}",
                    "command": ollama_cmd
                }
            else:
                return {
                    "installed": False,
                    "version": None,
                    "message": "Ollama no está instalado",
                    "command": None
                }

        except FileNotFoundError:
            return {
                "installed": False,
                "version": None,
                "message": "Ollama no está instalado en el sistema. Descarga desde https://ollama.com",
                "command": None
            }
        except subprocess.TimeoutExpired:
            return {
                "installed": False,
                "version": None,
                "message": "Timeout al verificar Ollama",
                "command": None
            }
        except Exception as e:
            return {
                "installed": False,
                "version": None,
                "message": f"Error verificando Ollama: {str(e)}",
                "command": None
            }

    @staticmethod
    def check_ollama_running() -> Dict[str, Any]:
        """
        Check if Ollama server is running

        Returns:
            Dict with server status
        """
        try:
            response = requests.get(f"{OllamaHealthChecker.BASE_URL}/", timeout=2)

            if response.status_code == 200:
                return {
                    "running": True,
                    "url": OllamaHealthChecker.BASE_URL,
                    "message": f"Servidor Ollama corriendo en {OllamaHealthChecker.BASE_URL}"
                }
            else:
                return {
                    "running": False,
                    "url": OllamaHealthChecker.BASE_URL,
                    "message": f"Servidor respondió con código {response.status_code}"
                }

        except requests.exceptions.ConnectionError:
            return {
                "running": False,
                "url": OllamaHealthChecker.BASE_URL,
                "message": "Servidor Ollama no está corriendo. Ejecuta: ollama serve"
            }
        except requests.exceptions.Timeout:
            return {
                "running": False,
                "url": OllamaHealthChecker.BASE_URL,
                "message": "Timeout al conectar con el servidor"
            }
        except Exception as e:
            return {
                "running": False,
                "url": OllamaHealthChecker.BASE_URL,
                "message": f"Error conectando: {str(e)}"
            }

    @staticmethod
    def get_installed_models() -> Dict[str, Any]:
        """
        Get list of installed Ollama models

        Returns:
            Dict with models list
        """
        try:
            ollama_cmd = OllamaHealthChecker._get_ollama_command()

            result = subprocess.run(
                [ollama_cmd, "list"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')

                # Skip header line
                models = []
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            models.append({
                                "name": parts[0],
                                "id": parts[1] if len(parts) > 1 else "",
                                "size": parts[2] if len(parts) > 2 else "",
                                "modified": " ".join(parts[3:]) if len(parts) > 3 else ""
                            })

                return {
                    "success": True,
                    "models": models,
                    "count": len(models),
                    "message": f"Se encontraron {len(models)} modelos instalados"
                }
            else:
                return {
                    "success": False,
                    "models": [],
                    "count": 0,
                    "message": "Error listando modelos. Asegúrate de que Ollama esté instalado y en el PATH."
                }

        except FileNotFoundError:
            return {
                "success": False,
                "models": [],
                "count": 0,
                "message": "Ollama no está instalado. Descarga desde https://ollama.com"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "models": [],
                "count": 0,
                "message": "Timeout al obtener modelos. Verifica que Ollama esté corriendo."
            }
        except Exception as e:
            error_msg = str(e)
            # Check if error is related to connection refused
            if "returncode" in error_msg or result.returncode != 0:
                return {
                    "success": False,
                    "models": [],
                    "count": 0,
                    "message": "Servidor Ollama no está corriendo. Inicia Ollama desde el menú de Windows o ejecuta 'ollama serve' en una terminal."
                }
            return {
                "success": False,
                "models": [],
                "count": 0,
                "message": f"Error obteniendo modelos: {error_msg}"
            }

    @staticmethod
    def check_model_installed(model_name: str) -> bool:
        """
        Check if a specific model is installed

        Args:
            model_name: Name of the model (e.g., "qwen2.5:72b")

        Returns:
            True if installed, False otherwise
        """
        models_info = OllamaHealthChecker.get_installed_models()

        if models_info["success"]:
            for model in models_info["models"]:
                installed_name = model["name"]

                # Exact match
                if installed_name == model_name:
                    return True

                # Match without :tag (e.g., "nomic-embed-text" matches "nomic-embed-text:latest")
                if installed_name.startswith(model_name + ":"):
                    return True

                # Match model_name with :tag against installed without tag
                if ":" in model_name:
                    base_name = model_name.split(":")[0]
                    if installed_name.startswith(base_name + ":"):
                        return True

        return False

    @staticmethod
    def test_model(model_name: str, test_prompt: str = "Hola") -> Dict[str, Any]:
        """
        Test if a model can generate responses

        Args:
            model_name: Name of the model to test
            test_prompt: Simple prompt for testing

        Returns:
            Dict with test results
        """
        try:
            # Use Ollama API to generate
            payload = {
                "model": model_name,
                "prompt": test_prompt,
                "stream": False
            }

            start_time = datetime.now()

            response = requests.post(
                f"{OllamaHealthChecker.BASE_URL}/api/generate",
                json=payload,
                timeout=30
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if response.status_code == 200:
                data = response.json()

                return {
                    "success": True,
                    "model": model_name,
                    "response": data.get("response", "")[:200],  # First 200 chars
                    "duration_seconds": round(duration, 2),
                    "tokens": data.get("eval_count", 0),
                    "tokens_per_second": round(data.get("eval_count", 0) / duration, 2) if duration > 0 else 0,
                    "message": f"Modelo {model_name} funciona correctamente"
                }
            else:
                return {
                    "success": False,
                    "model": model_name,
                    "message": f"Error {response.status_code}: {response.text[:200]}"
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "model": model_name,
                "message": "Timeout - El modelo tardó más de 30 segundos en responder"
            }
        except Exception as e:
            return {
                "success": False,
                "model": model_name,
                "message": f"Error probando modelo: {str(e)}"
            }

    @staticmethod
    def full_health_check(user_chat_model: str = None, user_embedding_model: str = None) -> Dict[str, Any]:
        """
        Perform a complete health check of Ollama installation

        Args:
            user_chat_model: User's configured chat model
            user_embedding_model: User's configured embedding model

        Returns:
            Dict with complete health status
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {}
        }

        # Check 1: Is Ollama installed?
        install_check = OllamaHealthChecker.check_ollama_installed()
        results["checks"]["installation"] = install_check

        if not install_check["installed"]:
            results["overall_status"] = "not_installed"
            results["message"] = "Ollama no está instalado. Ejecuta instalar_ollama.bat"
            return results

        # Check 2: Is server running?
        server_check = OllamaHealthChecker.check_ollama_running()
        results["checks"]["server"] = server_check

        if not server_check["running"]:
            results["overall_status"] = "server_not_running"
            results["message"] = "Servidor Ollama no está corriendo. Ejecuta: ollama serve"
            return results

        # Check 3: Get installed models
        models_check = OllamaHealthChecker.get_installed_models()
        results["checks"]["models"] = models_check

        if models_check["count"] == 0:
            results["overall_status"] = "no_models"
            results["message"] = "No hay modelos instalados. Descarga uno con: ollama pull qwen2.5:72b"
            return results

        # Check 4: Verify user's configured models are installed
        if user_chat_model:
            chat_model_installed = OllamaHealthChecker.check_model_installed(user_chat_model)
            results["checks"]["user_chat_model"] = {
                "model": user_chat_model,
                "installed": chat_model_installed,
                "message": f"Modelo de chat '{user_chat_model}' {'instalado' if chat_model_installed else 'NO instalado'}"
            }

            if not chat_model_installed:
                results["overall_status"] = "user_model_missing"
                results["message"] = f"Tu modelo de chat '{user_chat_model}' no está instalado. Descárgalo con: ollama pull {user_chat_model}"
                return results

        if user_embedding_model:
            embed_model_installed = OllamaHealthChecker.check_model_installed(user_embedding_model)
            results["checks"]["user_embedding_model"] = {
                "model": user_embedding_model,
                "installed": embed_model_installed,
                "message": f"Modelo de embeddings '{user_embedding_model}' {'instalado' if embed_model_installed else 'NO instalado'}"
            }

            if not embed_model_installed:
                results["overall_status"] = "user_model_missing"
                results["message"] = f"Tu modelo de embeddings '{user_embedding_model}' no está instalado. Descárgalo con: ollama pull {user_embedding_model}"
                return results

        # All checks passed
        results["overall_status"] = "healthy"
        results["message"] = "Ollama está correctamente configurado y listo para usar"

        return results

    @staticmethod
    def get_recommendations() -> Dict[str, Any]:
        """
        Get model recommendations based on what's available

        Returns:
            Dict with recommendations
        """
        models_info = OllamaHealthChecker.get_installed_models()

        installed_chat_models = []
        installed_embedding_models = []

        if models_info["success"]:
            for model in models_info["models"]:
                model_name = model["name"]

                # Check if it's a recommended chat model
                for rec_model in OllamaHealthChecker.RECOMMENDED_CHAT_MODELS:
                    if model_name.startswith(rec_model.split(":")[0]):
                        installed_chat_models.append(model_name)
                        break

                # Check if it's a recommended embedding model
                for rec_model in OllamaHealthChecker.RECOMMENDED_EMBEDDING_MODELS:
                    if model_name.startswith(rec_model.split(":")[0]):
                        installed_embedding_models.append(model_name)
                        break

        return {
            "installed_chat_models": installed_chat_models,
            "installed_embedding_models": installed_embedding_models,
            "recommended_chat_models": OllamaHealthChecker.RECOMMENDED_CHAT_MODELS,
            "recommended_embedding_models": OllamaHealthChecker.RECOMMENDED_EMBEDDING_MODELS,
            "message": f"Encontrados {len(installed_chat_models)} modelos de chat y {len(installed_embedding_models)} de embeddings instalados"
        }
