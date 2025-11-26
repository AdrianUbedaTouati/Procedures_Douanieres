# -*- coding: utf-8 -*-
"""
Renderizador de XML eForms a HTML similar a TED Europa.
Convierte el XML almacenado en un formato visual legible.
"""

from lxml import etree
from typing import Optional


# Namespaces eForms
EFORMS_NS = {
    'can': 'urn:oasis:names:specification:ubl:schema:xsd:ContractAwardNotice-2',
    'cn': 'urn:oasis:names:specification:ubl:schema:xsd:ContractNotice-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'efac': 'http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1',
    'efext': 'http://data.europa.eu/p27/eforms-ubl-extensions/1',
    'efbc': 'http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1',
}


def render_xml_to_html(xml_content: str, notice_id: str) -> str:
    """
    Convierte el XML eForms a HTML renderizado similar a TED.

    Args:
        xml_content: Contenido del XML eForms
        notice_id: ID del aviso (ej: 754920-2025)

    Returns:
        HTML renderizado del documento
    """
    if not xml_content:
        return '<div class="alert alert-warning">No hay contenido XML disponible.</div>'

    try:
        # Parsear XML
        root = etree.fromstring(xml_content.encode('utf-8'))

        # Determinar tipo de documento
        doc_type = root.tag.split('}')[-1] if '}' in root.tag else root.tag

        # Generar HTML
        html_parts = []
        html_parts.append('<div id="notice" class="eforms-notice">')

        # Header
        html_parts.append(_render_header(root, notice_id, doc_type))

        # Sección 1: Comprador
        html_parts.append(_render_section_buyer(root))

        # Sección 2: Procedimiento
        html_parts.append(_render_section_procedure(root))

        # Sección 5: Lotes
        html_parts.append(_render_section_lots(root))

        # Sección 8: Organizaciones
        html_parts.append(_render_section_organizations(root))

        # Información del anuncio
        html_parts.append(_render_section_notice_info(root, notice_id))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    except Exception as e:
        return f'<div class="alert alert-danger">Error renderizando XML: {str(e)}</div>'


def _render_header(root, notice_id: str, doc_type: str) -> str:
    """Renderiza el encabezado del documento."""
    title = _get_text(root, './/cbc:Title', 'Sin título')

    html = f'''
    <div class="header">
        <div class="header-content">
            <span class="bold">{notice_id} - Licitación</span>
            <div class="bold">{title}</div>
            <div class="bold">Anuncio de contrato o de concesión. Régimen normal</div>
        </div>
    </div>
    '''
    return html


def _render_section_buyer(root) -> str:
    """Renderiza la sección 1. Comprador."""
    buyer_name = _get_text(root, './/cac:ContractingParty//cac:Party//cbc:Name', 'N/A')
    buyer_email = _get_text(root, './/cac:ContractingParty//cac:Party//cbc:ElectronicMail', '')

    html = f'''
    <div class="h2" id="section1_1">
        1. <span>Comprador</span>
    </div>
    <div class="section-content">
        <div class="sublevel__number">
            <span class="bold">1.1. </span>
        </div>
        <div class="sublevel__content">
            <span class="bold">Comprador</span>
        </div>
        <div>
            <span class="label">Denominación oficial</span><span>:&nbsp;</span><span class="data">{buyer_name}</span>
        </div>
    '''

    if buyer_email:
        html += f'''
        <div>
            <span class="label">Correo electrónico</span><span>:&nbsp;</span>
            <span class="data"><a href="mailto:{buyer_email}">{buyer_email}</a></span>
        </div>
        '''

    html += '</div>'
    return html


def _render_section_procedure(root) -> str:
    """Renderiza la sección 2. Procedimiento."""
    title = _get_text(root, './/cbc:Title', 'N/A')
    description = _get_text(root, './/cbc:Description', 'N/A')
    procedure_id = _get_text(root, './/cbc:UUID', 'N/A')

    html = f'''
    <div class="h2" id="section2_3">
        2. <span>Procedimiento</span>
    </div>
    <div class="section-content">
        <div class="sublevel__number">
            <span class="bold">2.1. </span>
        </div>
        <div class="sublevel__content">
            <span class="bold">Procedimiento</span>
        </div>
        <div>
            <span class="label">Título</span><span>:&nbsp;</span><span class="data">{title}</span>
        </div>
        <div>
            <span class="label">Descripción</span><span>:&nbsp;</span><span class="data">{description}</span>
        </div>
        <div>
            <span class="label">Identificador del procedimiento</span><span>:&nbsp;</span><span class="data">{procedure_id}</span>
        </div>
    </div>
    '''
    return html


def _render_section_lots(root) -> str:
    """Renderiza la sección 5. Lotes."""
    lots = root.findall('.//cac:ProcurementProjectLot', namespaces=EFORMS_NS)

    if not lots:
        return ''

    html = f'''
    <div class="h2" id="section5_9">
        5. <span>Lote</span>
    </div>
    '''

    for i, lot in enumerate(lots, 1):
        lot_id = _get_text(lot, './/cbc:ID', f'LOT-{i}')
        lot_title = _get_text(lot, './/cbc:Title', 'Sin título')
        lot_desc = _get_text(lot, './/cbc:Description', '')

        html += f'''
        <div class="section-content">
            <div class="sublevel__number">
                <span class="bold">5.{i}. </span>
            </div>
            <div class="sublevel__content">
                <span class="bold">Lote</span><span>:&nbsp;</span><span class="data">{lot_id}</span>
            </div>
            <div>
                <span class="label">Título</span><span>:&nbsp;</span><span class="data">{lot_title}</span>
            </div>
        '''

        if lot_desc:
            html += f'''
            <div>
                <span class="label">Descripción</span><span>:&nbsp;</span><span class="data">{lot_desc}</span>
            </div>
            '''

        html += '</div>'

    return html


def _render_section_organizations(root) -> str:
    """Renderiza la sección 8. Organizaciones."""
    organizations = root.findall('.//efac:Organization', namespaces=EFORMS_NS)

    if not organizations:
        # Buscar en otros lugares comunes
        organizations = root.findall('.//cac:Party', namespaces=EFORMS_NS)

    if not organizations:
        return ''

    html = f'''
    <div class="h2" id="section8_20">
        8. <span>Organizaciones</span>
    </div>
    '''

    for i, org in enumerate(organizations, 1):
        org_name = _get_text(org, './/cbc:Name', 'N/A')
        org_email = _get_text(org, './/cbc:ElectronicMail', '')
        org_phone = _get_text(org, './/cbc:Telephone', '')
        org_website = _get_text(org, './/cbc:WebsiteURI', '')

        html += f'''
        <div class="section-content">
            <div class="sublevel__number">
                <span class="bold">8.{i}. </span>
            </div>
            <div class="sublevel__content">
                <span class="bold">ORG-{i:04d}</span>
            </div>
            <div>
                <span class="label">Denominación oficial</span><span>:&nbsp;</span><span class="data">{org_name}</span>
            </div>
        '''

        if org_email:
            html += f'''
            <div>
                <span class="label">Correo electrónico</span><span>:&nbsp;</span>
                <span class="data"><a href="mailto:{org_email}">{org_email}</a></span>
            </div>
            '''

        if org_phone:
            html += f'''
            <div>
                <span class="label">Teléfono</span><span>:&nbsp;</span><span class="data">{org_phone}</span>
            </div>
            '''

        if org_website:
            html += f'''
            <div>
                <span class="label">Dirección de internet</span><span>:&nbsp;</span>
                <span class="data"><a href="{org_website}" target="_blank">{org_website}</a></span>
            </div>
            '''

        html += '</div>'

    return html


def _render_section_notice_info(root, notice_id: str) -> str:
    """Renderiza la información del anuncio."""
    issue_date = _get_text(root, './/cbc:IssueDate', 'N/A')
    issue_time = _get_text(root, './/cbc:IssueTime', '')

    html = f'''
    <div class="h2" id="section_23">
        <span>Información del anuncio</span>
    </div>
    <div class="section-content">
        <div>
            <span class="label">Número de publicación del anuncio</span><span>:&nbsp;</span><span class="data">{notice_id}</span>
        </div>
        <div>
            <span class="label">Fecha de publicación</span><span>:&nbsp;</span><span class="data">{issue_date}</span>
        </div>
    '''

    if issue_time:
        html += f'''
        <div>
            <span class="label">Hora de envío</span><span>:&nbsp;</span><span class="data">{issue_time}</span>
        </div>
        '''

    html += '</div>'
    return html


def _get_text(element, xpath: str, default: str = '') -> str:
    """
    Obtiene texto de un elemento XML usando XPath.

    Args:
        element: Elemento raíz donde buscar
        xpath: XPath para buscar
        default: Valor por defecto si no se encuentra

    Returns:
        Texto encontrado o default
    """
    try:
        result = element.find(xpath, namespaces=EFORMS_NS)
        if result is not None and result.text:
            return result.text.strip()
        return default
    except:
        return default
