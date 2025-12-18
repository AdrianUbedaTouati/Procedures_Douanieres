# -*- coding: utf-8 -*-
"""
Comando de Django para verificar que todos los modelos de OpenAI funcionan.
Uso: python manage.py verify_openai_models --api-key=sk-...
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Verifica que todos los modelos de OpenAI disponibles funcionan correctamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-key',
            type=str,
            help='API key de OpenAI (o usa la variable de entorno OPENAI_API_KEY)',
        )

    def handle(self, *args, **options):
        api_key = options.get('api_key') or settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None

        if not api_key:
            self.stdout.write(
                self.style.ERROR('ERROR: No se proporcionó API key de OpenAI.')
            )
            self.stdout.write('Usa: python manage.py verify_openai_models --api-key=sk-...')
            self.stdout.write('O configura la variable de entorno OPENAI_API_KEY')
            return

        # Modelos a verificar
        models_to_test = [
            ('gpt-4o', 'GPT-4o'),
            ('gpt-4o-mini', 'GPT-4o-mini'),
            ('gpt-4-turbo', 'GPT-4 Turbo'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ]

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('VERIFICACION DE MODELOS OPENAI'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        results = []

        for model_id, model_name in models_to_test:
            self.stdout.write(f'Probando {model_name} ({model_id})...', ending=' ')
            sys.stdout.flush()

            success, message, tokens, cost = self._test_model(api_key, model_id)

            if success:
                self.stdout.write(self.style.SUCCESS('OK'))
                self.stdout.write(f'  -> Tokens: {tokens}, Costo: {cost}')
                results.append((model_name, 'OK', tokens, cost))
            else:
                self.stdout.write(self.style.ERROR('FALLO'))
                self.stdout.write(f'  -> Error: {message}')
                results.append((model_name, 'FALLO', 0, message))

            self.stdout.write('')

        # Resumen
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('RESUMEN')
        self.stdout.write('=' * 70)

        successful = sum(1 for r in results if r[1] == 'OK')
        total = len(results)

        for model_name, status, tokens, extra in results:
            if status == 'OK':
                self.stdout.write(
                    f'  {model_name:30} -> {self.style.SUCCESS("OK")} ({tokens} tokens, {extra})'
                )
            else:
                self.stdout.write(
                    f'  {model_name:30} -> {self.style.ERROR("FALLO")}'
                )

        self.stdout.write('')
        self.stdout.write(f'Modelos exitosos: {successful}/{total}')
        self.stdout.write('=' * 70)

    def _test_model(self, api_key, model):
        """
        Hace una llamada simple de prueba a un modelo de OpenAI.

        Returns:
            (success, message, tokens, cost)
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            # Llamada simple de prueba
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Eres un asistente útil."},
                    {"role": "user", "content": "Di 'OK' si funcionas correctamente."}
                ],
                max_tokens=10,
                temperature=0
            )

            # Extraer información
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens

            # Calcular costo aproximado
            cost = self._calculate_cost(model, response.usage.prompt_tokens, response.usage.completion_tokens)

            return True, answer, tokens, f'€{cost:.6f}'

        except Exception as e:
            return False, str(e), 0, '€0.000000'

    def _calculate_cost(self, model, input_tokens, output_tokens):
        """
        Calcula el costo aproximado en euros de una llamada.

        Precios aproximados (enero 2025):
        - gpt-4o: $2.50/1M input, $10.00/1M output
        - gpt-4o-mini: $0.15/1M input, $0.60/1M output
        - gpt-4-turbo: $10.00/1M input, $30.00/1M output
        - gpt-3.5-turbo: $0.50/1M input, $1.50/1M output
        """
        # Precios en USD por 1M tokens
        prices = {
            'gpt-4o': {'input': 2.50, 'output': 10.00},
            'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
            'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
        }

        if model not in prices:
            return 0.0

        # Conversión USD -> EUR (aproximado)
        usd_to_eur = 0.93

        # Calcular costo en USD
        cost_usd = (
            (input_tokens / 1_000_000) * prices[model]['input'] +
            (output_tokens / 1_000_000) * prices[model]['output']
        )

        # Convertir a EUR
        return cost_usd * usd_to_eur
