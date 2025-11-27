# -*- coding: utf-8 -*-
"""
Renderizador de XML eForms a HTML - Versión Completa.
Muestra TODA la información del XML sin omitir ningún campo.

Versión 3.0 - Renderizado completo de todo el árbol XML
"""

from lxml import etree
from typing import Optional


def render_xml_to_html(xml_content: str, notice_id: str) -> str:
    """
    Convierte el XML eForms completo a HTML estructurado.
    Muestra TODOS los elementos y atributos sin omitir nada.

    Args:
        xml_content: Contenido del XML eForms
        notice_id: ID del aviso (ej: 754920-2025)

    Returns:
        HTML renderizado del documento completo
    """
    if not xml_content:
        return '<div class="alert alert-warning">No hay contenido XML disponible.</div>'

    try:
        # Parsear XML
        root = etree.fromstring(xml_content.encode('utf-8'))

        # Generar HTML del árbol completo
        html_parts = []
        html_parts.append('<div id="notice" class="eforms-notice-complete">')
        html_parts.append(f'<div class="xml-header"><h3>Documento Completo XML - {notice_id}</h3></div>')
        html_parts.append('<div class="xml-content">')

        # Renderizar todo el árbol XML recursivamente
        html_parts.append(_render_element(root, level=0))

        html_parts.append('</div>')
        html_parts.append('</div>')

        # Agregar estilos CSS inline para el renderizado
        css = """
        <style>
        .eforms-notice-complete {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }
        .xml-header {
            background: #2c3e50;
            color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .xml-header h3 {
            margin: 0;
            font-size: 18px;
        }
        .xml-content {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }
        .xml-element {
            margin: 8px 0;
            padding: 8px 12px;
            background: white;
            border-left: 3px solid #3498db;
            border-radius: 3px;
        }
        .xml-element-name {
            font-weight: 600;
            color: #2c3e50;
            font-size: 13px;
            margin-bottom: 4px;
        }
        .xml-element-namespace {
            font-size: 11px;
            color: #7f8c8d;
            font-style: italic;
            margin-left: 8px;
        }
        .xml-element-text {
            color: #27ae60;
            margin-left: 20px;
            padding: 6px 10px;
            background: #e8f8f5;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .xml-attributes {
            margin: 6px 0 6px 20px;
            padding: 6px 10px;
            background: #fff3cd;
            border-left: 2px solid #ffc107;
            border-radius: 3px;
        }
        .xml-attribute {
            color: #e67e22;
            font-size: 12px;
            margin: 3px 0;
        }
        .xml-attribute-name {
            font-weight: 600;
            color: #d35400;
        }
        .xml-attribute-value {
            color: #8e44ad;
            font-family: 'Courier New', monospace;
        }
        .xml-children {
            margin-left: 20px;
            border-left: 1px dashed #bdc3c7;
            padding-left: 15px;
        }
        .xml-empty {
            color: #95a5a6;
            font-style: italic;
            margin-left: 20px;
            font-size: 12px;
        }
        </style>
        """

        return css + '\n'.join(html_parts)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <div class="alert alert-danger">
            <strong>Error renderizando XML:</strong> {str(e)}
            <br><br>
            <details>
                <summary>Detalles técnicos</summary>
                <pre style="font-size: 11px; margin-top: 10px;">{error_detail}</pre>
            </details>
        </div>
        '''


def _render_element(element, level=0) -> str:
    """
    Renderiza un elemento XML y todos sus hijos recursivamente.

    Args:
        element: Elemento XML (lxml.etree.Element)
        level: Nivel de profundidad (para indentación)

    Returns:
        HTML del elemento y todos sus descendientes
    """
    html_parts = []

    # Extraer nombre del tag (sin namespace)
    tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag

    # Extraer namespace si existe
    namespace = ''
    if '}' in element.tag:
        namespace = element.tag.split('}')[0].replace('{', '')

    # Texto del elemento (limpiado)
    text = element.text.strip() if element.text and element.text.strip() else ''

    # Inicio del elemento
    html_parts.append('<div class="xml-element">')

    # Nombre del elemento con namespace
    element_header = f'<div class="xml-element-name">&lt;{tag_name}&gt;'
    if namespace:
        element_header += f'<span class="xml-element-namespace">({namespace})</span>'
    element_header += '</div>'
    html_parts.append(element_header)

    # Atributos
    if element.attrib:
        html_parts.append('<div class="xml-attributes">')
        html_parts.append('<strong style="font-size: 11px; color: #e67e22;">Atributos:</strong>')
        for attr_name, attr_value in element.attrib.items():
            html_parts.append(
                f'<div class="xml-attribute">'
                f'<span class="xml-attribute-name">@{attr_name}</span> = '
                f'<span class="xml-attribute-value">"{attr_value}"</span>'
                f'</div>'
            )
        html_parts.append('</div>')

    # Texto del elemento (si es un nodo hoja con contenido)
    if text:
        html_parts.append(f'<div class="xml-element-text">{_escape_html(text)}</div>')

    # Elementos hijos
    children = list(element)
    if children:
        html_parts.append('<div class="xml-children">')
        for child in children:
            html_parts.append(_render_element(child, level + 1))
        html_parts.append('</div>')
    elif not text:
        # Elemento vacío sin texto ni hijos
        html_parts.append('<div class="xml-empty">(vacío)</div>')

    # Cierre del elemento
    html_parts.append('</div>')

    return '\n'.join(html_parts)


def _escape_html(text: str) -> str:
    """
    Escapa caracteres HTML especiales para evitar inyección.

    Args:
        text: Texto a escapar

    Returns:
        Texto escapado
    """
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )
