# -*- coding: utf-8 -*-
"""
Renderizador de XML eForms a HTML legible.
Muestra TODA la información del XML en formato legible para humanos.

Versión 4.0 - Formato legible similar a TED Europa
"""

from lxml import etree
from typing import List, Dict, Any


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
    Convierte el XML eForms a HTML legible para humanos.
    Muestra TODA la información de forma estructurada y clara.

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

        # Extraer toda la información estructurada
        data = _extract_all_data(root)

        # Generar HTML legible
        html_parts = []
        html_parts.append(_render_styles())
        html_parts.append('<div class="eforms-document">')
        html_parts.append(f'<h2 class="doc-title">{notice_id} - Licitación</h2>')

        # Renderizar cada sección
        html_parts.append(_render_section("Información General", data.get('general', {})))
        html_parts.append(_render_section("Comprador", data.get('buyer', {})))
        html_parts.append(_render_section("Procedimiento", data.get('procedure', {})))
        html_parts.append(_render_section("Objeto del Contrato", data.get('contract_object', {})))

        # Lotes
        if data.get('lots'):
            html_parts.append('<h3 class="section-title">Lotes</h3>')
            for i, lot in enumerate(data['lots'], 1):
                html_parts.append(_render_section(f"Lote {i}", lot))

        # Organizaciones
        if data.get('organizations'):
            html_parts.append('<h3 class="section-title">Organizaciones</h3>')
            for i, org in enumerate(data['organizations'], 1):
                html_parts.append(_render_section(f"Organización {i}", org))

        # Información adicional (todo lo demás del XML)
        if data.get('additional'):
            html_parts.append(_render_section("Información Adicional Completa", data['additional']))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

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


def _extract_all_data(root) -> Dict[str, Any]:
    """
    Extrae TODA la información del XML de forma estructurada.

    Returns:
        Diccionario con toda la información organizada por secciones
    """
    data = {
        'general': {},
        'buyer': {},
        'procedure': {},
        'contract_object': {},
        'lots': [],
        'organizations': [],
        'additional': {}
    }

    # Información general
    data['general']['ID del Anuncio'] = _get_text(root, './/cbc:ID[@schemeName="notice-id"]')
    data['general']['UUID'] = _get_text(root, './/cbc:UUID')
    data['general']['Fecha de Emisión'] = _get_text(root, './/cbc:IssueDate')
    data['general']['Hora de Emisión'] = _get_text(root, './/cbc:IssueTime')
    data['general']['Versión UBL'] = _get_text(root, './/cbc:UBLVersionID')
    data['general']['Versión Personalización'] = _get_text(root, './/cbc:CustomizationID')

    # Información del comprador
    buyer_party = root.find('.//cac:ContractingParty/cac:Party', namespaces=EFORMS_NS)
    if buyer_party is not None:
        data['buyer']['Nombre'] = _get_text(buyer_party, './/cac:PartyName/cbc:Name')
        data['buyer']['ID'] = _get_text(buyer_party, './/cac:PartyIdentification/cbc:ID')
        data['buyer']['Correo Electrónico'] = _get_text(buyer_party, './/cac:Contact/cbc:ElectronicMail')
        data['buyer']['Teléfono'] = _get_text(buyer_party, './/cac:Contact/cbc:Telephone')
        data['buyer']['Fax'] = _get_text(buyer_party, './/cac:Contact/cbc:Telefax')
        data['buyer']['URL'] = _get_text(buyer_party, './/cbc:WebsiteURI')

        # Dirección
        address = buyer_party.find('.//cac:PostalAddress', namespaces=EFORMS_NS)
        if address is not None:
            data['buyer']['Calle'] = _get_text(address, './/cbc:StreetName')
            data['buyer']['Ciudad'] = _get_text(address, './/cbc:CityName')
            data['buyer']['Código Postal'] = _get_text(address, './/cbc:PostalZone')
            data['buyer']['País'] = _get_text(address, './/cac:Country/cbc:Name')

    # Información del procedimiento
    proc_project = root.find('.//cac:ProcurementProject', namespaces=EFORMS_NS)
    if proc_project is not None:
        data['procedure']['Título'] = _get_text(proc_project, './/cbc:Name')
        data['procedure']['Descripción'] = _get_text(proc_project, './/cbc:Description')
        data['procedure']['ID del Procedimiento'] = _get_text(root, './/cbc:UUID')

        # Tipo de contrato
        data['procedure']['Tipo de Contrato'] = _get_text(proc_project, './/cbc:ProcurementTypeCode')

        # Presupuesto estimado
        budget = _get_text(proc_project, './/cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount')
        currency = _get_attr(proc_project, './/cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount', 'currencyID')
        if budget:
            data['procedure']['Presupuesto Estimado'] = f"{budget} {currency}" if currency else budget

    # Proceso de licitación
    tender_process = root.find('.//cac:TenderingProcess', namespaces=EFORMS_NS)
    if tender_process is not None:
        data['procedure']['Tipo de Procedimiento'] = _get_text(tender_process, './/cbc:ProcedureCode')
        data['procedure']['Justificación del Procedimiento'] = _get_text(tender_process, './/cac:ProcessJustification/cbc:Description')

        # Fechas límite
        data['procedure']['Fecha Límite de Recepción'] = _get_text(tender_process, './/cac:TenderSubmissionDeadlinePeriod/cbc:EndDate')
        data['procedure']['Hora Límite de Recepción'] = _get_text(tender_process, './/cac:TenderSubmissionDeadlinePeriod/cbc:EndTime')

    # Objeto del contrato
    if proc_project is not None:
        # CPV Codes
        cpv_codes = []
        for cpv in proc_project.findall('.//cac:AdditionalCommodityClassification/cbc:ItemClassificationCode', namespaces=EFORMS_NS):
            code = cpv.text
            name = cpv.get('name', '')
            cpv_codes.append(f"{code} - {name}" if name else code)
        if cpv_codes:
            data['contract_object']['Códigos CPV'] = cpv_codes

        # NUTS codes
        nuts_codes = []
        for nuts in proc_project.findall('.//cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode', namespaces=EFORMS_NS):
            nuts_codes.append(nuts.text)
        if nuts_codes:
            data['contract_object']['Códigos NUTS'] = nuts_codes

    # Lotes
    lots = root.findall('.//cac:ProcurementProjectLot', namespaces=EFORMS_NS)
    for lot in lots:
        lot_data = {}
        lot_data['ID del Lote'] = _get_text(lot, './/cbc:ID')

        lot_project = lot.find('.//cac:ProcurementProject', namespaces=EFORMS_NS)
        if lot_project is not None:
            lot_data['Título'] = _get_text(lot_project, './/cbc:Name')
            lot_data['Descripción'] = _get_text(lot_project, './/cbc:Description')

            # Presupuesto del lote
            budget = _get_text(lot_project, './/cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount')
            currency = _get_attr(lot_project, './/cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount', 'currencyID')
            if budget:
                lot_data['Presupuesto Estimado'] = f"{budget} {currency}" if currency else budget

        # Criterios de adjudicación
        award_criteria = lot.findall('.//cac:TenderingTerms/cac:AwardingTerms/cac:AwardingCriterion', namespaces=EFORMS_NS)
        if award_criteria:
            criteria_list = []
            for criterion in award_criteria:
                name = _get_text(criterion, './/cbc:Name')
                desc = _get_text(criterion, './/cbc:Description')
                weight = _get_text(criterion, './/cbc:Weight')
                criteria_list.append(f"{name}: {desc} (Peso: {weight})" if weight else f"{name}: {desc}")
            lot_data['Criterios de Adjudicación'] = criteria_list

        data['lots'].append(lot_data)

    # Organizaciones
    organizations = root.findall('.//efac:Organization', namespaces=EFORMS_NS)
    for org in organizations:
        org_data = {}

        company = org.find('.//efac:Company', namespaces=EFORMS_NS)
        if company is not None:
            org_data['ID'] = _get_text(company, './/cac:PartyIdentification/cbc:ID')
            org_data['Nombre'] = _get_text(company, './/cac:PartyName/cbc:Name')
            org_data['Correo Electrónico'] = _get_text(company, './/cac:Contact/cbc:ElectronicMail')
            org_data['Teléfono'] = _get_text(company, './/cac:Contact/cbc:Telephone')
            org_data['URL'] = _get_text(company, './/cbc:WebsiteURI')

            # Dirección
            address = company.find('.//cac:PostalAddress', namespaces=EFORMS_NS)
            if address is not None:
                org_data['Ciudad'] = _get_text(address, './/cbc:CityName')
                org_data['Código Postal'] = _get_text(address, './/cbc:PostalZone')
                org_data['País'] = _get_text(address, './/cac:Country/cbc:Name')

        data['organizations'].append(org_data)

    # Información adicional (recorrer TODO el XML recursivamente)
    data['additional'] = _extract_additional_info(root)

    return data


def _extract_additional_info(element, path="") -> Dict[str, Any]:
    """
    Extrae TODA la información adicional del XML recursivamente.
    Esto captura cualquier campo que no esté en las secciones principales.
    """
    info = {}

    for child in element:
        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        full_path = f"{path}/{tag_name}" if path else tag_name

        # Si tiene texto y no tiene hijos, es un valor
        if child.text and child.text.strip() and len(child) == 0:
            info[full_path] = child.text.strip()

        # Si tiene atributos, guardarlos
        if child.attrib:
            for attr_name, attr_value in child.attrib.items():
                info[f"{full_path}@{attr_name}"] = attr_value

        # Recursión para hijos
        if len(child) > 0:
            child_info = _extract_additional_info(child, full_path)
            info.update(child_info)

    return info


def _render_section(title: str, data: Dict[str, Any]) -> str:
    """Renderiza una sección de datos en HTML."""
    if not data or all(not v for v in data.values()):
        return ''

    html = f'<div class="section"><h3 class="section-title">{title}</h3><div class="section-content">'

    for key, value in data.items():
        if not value:
            continue

        if isinstance(value, list):
            html += f'<div class="field"><span class="field-label">{key}:</span><ul class="field-list">'
            for item in value:
                html += f'<li>{_escape_html(str(item))}</li>'
            html += '</ul></div>'
        else:
            html += f'<div class="field"><span class="field-label">{key}:</span> <span class="field-value">{_escape_html(str(value))}</span></div>'

    html += '</div></div>'
    return html


def _render_styles() -> str:
    """Genera los estilos CSS para el documento."""
    return """
    <style>
    .eforms-document {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 14px;
        line-height: 1.8;
        color: #2c3e50;
        max-width: 1200px;
    }
    .doc-title {
        font-size: 24px;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 30px;
        padding-bottom: 15px;
        border-bottom: 3px solid #3498db;
    }
    .section {
        margin-bottom: 30px;
        background: white;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #ecf0f1;
    }
    .section-content {
        margin-left: 10px;
    }
    .field {
        margin: 12px 0;
        padding: 8px 0;
    }
    .field-label {
        font-weight: 600;
        color: #34495e;
        display: inline-block;
        min-width: 200px;
    }
    .field-value {
        color: #555;
    }
    .field-list {
        margin: 8px 0 8px 220px;
        padding-left: 20px;
    }
    .field-list li {
        margin: 5px 0;
        color: #555;
    }
    </style>
    """


def _get_text(element, xpath: str, default: str = '') -> str:
    """Obtiene texto de un elemento XML usando XPath."""
    try:
        result = element.find(xpath, namespaces=EFORMS_NS)
        if result is not None and result.text:
            return result.text.strip()
        return default
    except:
        return default


def _get_attr(element, xpath: str, attr_name: str, default: str = '') -> str:
    """Obtiene un atributo de un elemento XML usando XPath."""
    try:
        result = element.find(xpath, namespaces=EFORMS_NS)
        if result is not None:
            return result.get(attr_name, default)
        return default
    except:
        return default


def _escape_html(text: str) -> str:
    """Escapa caracteres HTML especiales."""
    return (str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )
