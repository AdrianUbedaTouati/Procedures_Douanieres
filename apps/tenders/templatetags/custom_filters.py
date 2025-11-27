# -*- coding: utf-8 -*-
"""
Custom template filters for TenderAI.
"""

from django import template

register = template.Library()


@register.filter
def is_list(value):
    """
    Verifica si un valor es una lista.

    Uso: {% if value|is_list %}
    """
    return isinstance(value, list)


@register.filter
def is_dict(value):
    """
    Verifica si un valor es un diccionario.

    Uso: {% if value|is_dict %}
    """
    return isinstance(value, dict)


@register.filter
def is_string(value):
    """
    Verifica si un valor es una cadena de texto.

    Uso: {% if value|is_string %}
    """
    return isinstance(value, str)
