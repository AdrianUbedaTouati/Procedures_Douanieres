"""
Multi-provider LLM support for TenderAI Platform
Supports: Google Gemini, OpenAI, NVIDIA NIM
"""
import os
from typing import Optional, Dict, Any


class LLMProviderFactory:
    """Factory for creating LLM instances based on provider type"""

    @staticmethod
    def get_llm(provider: str, api_key: str = None, model_name: Optional[str] = None, **kwargs):
        """
        Get LLM instance for the specified provider

        Args:
            provider: Provider name ('gemini', 'openai', 'nvidia', 'ollama')
            api_key: API key for the provider (not needed for Ollama)
            model_name: Optional custom model name
            **kwargs: Additional provider-specific arguments

        Returns:
            LLM instance compatible with LangChain
        """
        if provider == 'gemini':
            return LLMProviderFactory._get_gemini_llm(api_key, model_name, **kwargs)
        elif provider == 'openai':
            return LLMProviderFactory._get_openai_llm(api_key, model_name, **kwargs)
        elif provider == 'nvidia':
            return LLMProviderFactory._get_nvidia_llm(api_key, model_name, **kwargs)
        elif provider == 'ollama':
            return LLMProviderFactory._get_ollama_llm(model_name, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def _get_gemini_llm(api_key: str, model_name: Optional[str] = None, **kwargs):
        """Get Google Gemini LLM instance"""
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = model_name or "gemini-2.0-flash-exp"
        os.environ['GOOGLE_API_KEY'] = api_key

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=kwargs.get('temperature', 0),
            **{k: v for k, v in kwargs.items() if k != 'temperature'}
        )

    @staticmethod
    def _get_openai_llm(api_key: str, model_name: Optional[str] = None, **kwargs):
        """Get OpenAI LLM instance"""
        from langchain_openai import ChatOpenAI

        model = model_name or "gpt-4o-mini"
        os.environ['OPENAI_API_KEY'] = api_key

        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=kwargs.get('temperature', 0),
            **{k: v for k, v in kwargs.items() if k != 'temperature'}
        )

    @staticmethod
    def _get_nvidia_llm(api_key: str, model_name: Optional[str] = None, **kwargs):
        """Get NVIDIA NIM LLM instance"""
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        model = model_name or "meta/llama-3.1-8b-instruct"
        os.environ['NVIDIA_API_KEY'] = api_key

        return ChatNVIDIA(
            model=model,
            api_key=api_key,
            temperature=kwargs.get('temperature', 0),
            **{k: v for k, v in kwargs.items() if k != 'temperature'}
        )

    @staticmethod
    def _get_ollama_llm(model_name: Optional[str] = None, **kwargs):
        """Get Ollama local LLM instance"""
        from langchain_ollama import ChatOllama

        model = model_name or "qwen2.5:72b"

        return ChatOllama(
            model=model,
            base_url="http://localhost:11434",
            temperature=kwargs.get('temperature', 0.7),
            **{k: v for k, v in kwargs.items() if k != 'temperature'}
        )

    @staticmethod
    def get_embeddings(provider: str, api_key: str = None, model_name: Optional[str] = None):
        """
        Get embeddings instance for the specified provider

        Args:
            provider: Provider name ('gemini', 'openai', 'nvidia', 'ollama')
            api_key: API key for the provider (not needed for Ollama)
            model_name: Optional custom model name

        Returns:
            Embeddings instance compatible with LangChain
        """
        if provider == 'gemini':
            return LLMProviderFactory._get_gemini_embeddings(api_key, model_name)
        elif provider == 'openai':
            return LLMProviderFactory._get_openai_embeddings(api_key, model_name)
        elif provider == 'nvidia':
            return LLMProviderFactory._get_nvidia_embeddings(api_key, model_name)
        elif provider == 'ollama':
            return LLMProviderFactory._get_ollama_embeddings(model_name)
        else:
            raise ValueError(f"Unsupported embeddings provider: {provider}")

    @staticmethod
    def _get_gemini_embeddings(api_key: str, model_name: Optional[str] = None):
        """Get Google Gemini embeddings"""
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        model = model_name or "models/embedding-001"
        os.environ['GOOGLE_API_KEY'] = api_key

        return GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=api_key
        )

    @staticmethod
    def _get_openai_embeddings(api_key: str, model_name: Optional[str] = None):
        """Get OpenAI embeddings"""
        from langchain_openai import OpenAIEmbeddings

        model = model_name or "text-embedding-3-small"
        os.environ['OPENAI_API_KEY'] = api_key

        return OpenAIEmbeddings(
            model=model,
            api_key=api_key
        )

    @staticmethod
    def _get_nvidia_embeddings(api_key: str, model_name: Optional[str] = None):
        """Get NVIDIA NIM embeddings"""
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        model = model_name or "nvidia/nv-embedqa-e5-v5"
        os.environ['NVIDIA_API_KEY'] = api_key

        return NVIDIAEmbeddings(
            model=model,
            api_key=api_key
        )

    @staticmethod
    def _get_ollama_embeddings(model_name: Optional[str] = None):
        """Get Ollama local embeddings"""
        from langchain_ollama import OllamaEmbeddings

        model = model_name or "nomic-embed-text"

        return OllamaEmbeddings(
            model=model,
            base_url="http://localhost:11434"
        )

    @staticmethod
    def get_provider_info(provider: str) -> Dict[str, Any]:
        """
        Get information about a provider

        Args:
            provider: Provider name

        Returns:
            Dict with provider information (name, models, docs_url, etc.)
        """
        provider_info = {
            'gemini': {
                'name': 'Google Gemini',
                'llm_models': ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'],
                'embedding_models': ['models/embedding-001', 'models/text-embedding-004'],
                'docs_url': 'https://ai.google.dev/gemini-api/docs',
                'api_key_url': 'https://aistudio.google.com/apikey',
                'free_tier': True,
                'description': 'Modelo multimodal de Google con generación de texto rápida y eficiente'
            },
            'openai': {
                'name': 'OpenAI',
                'llm_models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'embedding_models': ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
                'docs_url': 'https://platform.openai.com/docs',
                'api_key_url': 'https://platform.openai.com/api-keys',
                'free_tier': False,
                'description': 'Modelos GPT de OpenAI con capacidades avanzadas de razonamiento'
            },
            'nvidia': {
                'name': 'NVIDIA NIM',
                'llm_models': ['meta/llama-3.1-8b-instruct', 'meta/llama-3.1-70b-instruct', 'mistralai/mixtral-8x7b-instruct-v0.1'],
                'embedding_models': ['nvidia/nv-embedqa-e5-v5', 'nvidia/nv-embed-v1'],
                'docs_url': 'https://build.nvidia.com/explore/discover',
                'api_key_url': 'https://build.nvidia.com/settings/api-keys',
                'free_tier': True,
                'description': 'Modelos open-source optimizados en infraestructura NVIDIA'
            },
            'ollama': {
                'name': 'Ollama (Local)',
                'llm_models': ['qwen2.5:72b', 'llama3.3:70b', 'llama3.1:70b', 'deepseek-r1:14b', 'mistral:7b'],
                'embedding_models': ['nomic-embed-text', 'mxbai-embed-large'],
                'docs_url': 'https://ollama.com/library',
                'api_key_url': None,
                'free_tier': True,
                'description': 'Modelos LLM ejecutándose localmente en tu máquina. Máxima privacidad, costo cero, sin límites de uso'
            }
        }

        return provider_info.get(provider, {})
