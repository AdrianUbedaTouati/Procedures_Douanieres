"""
Services pour la generation de documents douaniers.
Utilise WeasyPrint pour la generation PDF.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class DocumentGenerationService:
    """
    Service principal pour la generation des documents douaniers.
    Supporte DAU (FR_DZ) et D10/D12 (DZ_FR).
    """

    DOCUMENT_TYPES = {
        'dau': {
            'name': 'Document Administratif Unique',
            'template': 'expeditions/documents/pdf/dau_template.html',
            'direction': 'FR_DZ',
        },
        'd10': {
            'name': 'Declaration D10 - Mise a la consommation',
            'template': 'expeditions/documents/pdf/d10_template.html',
            'direction': 'DZ_FR',
        },
        'd12': {
            'name': 'Declaration D12 - Admission temporaire',
            'template': 'expeditions/documents/pdf/d12_template.html',
            'direction': 'DZ_FR',
        },
    }

    def __init__(self, expedition, user):
        """
        Initialise le service de generation.

        Args:
            expedition: L'objet Expedition
            user: L'utilisateur Django
        """
        self.expedition = expedition
        self.user = user
        self.etape = expedition.get_etape(2)
        self.documents_data = self.etape.documents_data
        self.classification_data = expedition.get_etape(1).classification_data

    def generate_document(self, doc_type: str) -> Dict[str, Any]:
        """
        Genere un document PDF du type specifie.

        Args:
            doc_type: 'dau', 'd10', ou 'd12'

        Returns:
            dict: {success: bool, file_path: str, error: str}
        """
        if doc_type not in self.DOCUMENT_TYPES:
            return {'success': False, 'error': f'Type de document inconnu: {doc_type}'}

        doc_info = self.DOCUMENT_TYPES[doc_type]

        # Verify direction matches
        if self.expedition.direction != doc_info['direction']:
            return {
                'success': False,
                'error': f"Le document {doc_type.upper()} n'est pas applicable "
                         f"pour la direction {self.expedition.get_direction_display()}"
            }

        try:
            # Prepare context data
            context = self._prepare_context(doc_type)

            # Render HTML template
            html_content = render_to_string(doc_info['template'], context)

            # Generate PDF using WeasyPrint
            pdf_content = self._generate_pdf(html_content, doc_type)

            # Save the document
            saved_doc = self._save_document(pdf_content, doc_type)

            # Update generation status
            self._update_generation_status(doc_type)

            return {
                'success': True,
                'document': saved_doc,
                'file_path': saved_doc.fichier.url,
                'filename': saved_doc.nom_original,
            }

        except Exception as e:
            logger.exception(f"Error generating {doc_type}: {e}")
            return {'success': False, 'error': str(e)}

    def _prepare_context(self, doc_type: str) -> Dict[str, Any]:
        """Prepare le contexte pour le template PDF."""

        # Ensure CIF value is calculated
        self.documents_data.calculate_cif_value()
        self.documents_data.get_transport_mode_code()
        self.documents_data.save()

        # Base context with all data
        context = {
            'expedition': self.expedition,
            'user': self.user,
            'documents_data': self.documents_data,
            'classification': self.classification_data,
            'generation_date': datetime.now(),
            'doc_type': doc_type,
        }

        # Add calculated values
        context['cif_value'] = self.documents_data.cif_value
        context['transport_mode_code'] = self.documents_data.transport_mode_code

        # Format TARIC code with dots
        if self.classification_data and self.classification_data.code_taric:
            code = self.classification_data.code_taric
            if len(code) == 10:
                context['formatted_taric'] = f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"
            else:
                context['formatted_taric'] = code
        else:
            context['formatted_taric'] = ''

        # Document-specific preparations
        if doc_type == 'dau':
            context.update(self._prepare_dau_context())
        elif doc_type in ('d10', 'd12'):
            context.update(self._prepare_d10_d12_context(doc_type))

        return context

    def _prepare_dau_context(self) -> Dict[str, Any]:
        """Prepare contexte specifique DAU (export EU)."""
        dd = self.documents_data
        cd = self.classification_data

        # Get transport mode label
        transport_mode_labels = {
            'sea': 'Maritime',
            'air': 'Aerien',
            'road': 'Routier',
            'rail': 'Ferroviaire',
            'multimodal': 'Multimodal',
        }

        return {
            # Exporter (from user profile)
            'exporter': {
                'name': self.user.company_name or f"{self.user.first_name} {self.user.last_name}",
                'address': self.user.address_line1 or '',
                'postal_code': self.user.postal_code or '',
                'city': self.user.city or '',
                'country': self.user.country or 'France',
                'eori': self.user.eori_number or '',
                'vat': self.user.vat_number or '',
            },

            # Consignee
            'consignee': {
                'name': dd.consignee_name or '',
                'address': dd.consignee_address or '',
                'postal_code': dd.consignee_postal_code or '',
                'city': dd.consignee_city or '',
                'country': dd.consignee_country or '',
                'country_code': dd.consignee_country_code or '',
                'tax_id': dd.consignee_tax_id or '',
            },

            # Origin
            'origin': {
                'origin_country': dd.country_of_origin or 'France',
                'origin_code': dd.country_of_origin_code or 'FR',
                'dispatch_country': dd.country_of_dispatch or 'France',
                'dispatch_code': dd.country_of_dispatch_code or 'FR',
            },

            # Transport
            'transport': {
                'mode': dd.transport_mode or '',
                'mode_code': dd.transport_mode_code or '',
                'mode_label': transport_mode_labels.get(dd.transport_mode, ''),
                'vessel_name': dd.vessel_name or '',
                'document_type': dd.transport_document_type or '',
                'document_ref': dd.transport_document_ref or '',
                'document_date': dd.transport_document_date,
                'port_loading': dd.port_of_loading or '',
                'port_discharge': dd.port_of_discharge or '',
            },

            # Commercial
            'commercial': {
                'incoterms': dd.incoterms or 'CIF',
                'incoterms_location': dd.incoterms_location or '',
            },

            # Invoice
            'invoice': {
                'number': dd.invoice_number or '',
                'date': dd.invoice_date,
                'total': dd.invoice_total or 0,
                'currency': dd.invoice_currency or 'EUR',
            },

            # Goods
            'goods': {
                'description': self.expedition.description or self.expedition.nom_article,
                'taric_code': cd.code_taric if cd else '',
                'packages': dd.number_of_packages or 1,
                'package_type': dd.package_type or 'Carton',
                'quantity': dd.quantity or '',
                'unit': dd.unit_of_measure or '',
                'gross_weight': dd.gross_weight_kg or 0,
                'net_weight': dd.net_weight_kg or 0,
            },

            # Values
            'values': {
                'fob': dd.fob_value or dd.invoice_total or 0,
                'cif': dd.cif_value or dd.invoice_total or 0,
                'statistical': dd.cif_value or dd.invoice_total or 0,
            },

            # Customs
            'customs': {
                'procedure_code': dd.customs_procedure_code or '10 00',
                'duty_rate': cd.droits_douane if cd else '0%',
                'duty_amount': '0.00',
                'total_duties': '0.00',
            },
        }

    def _prepare_d10_d12_context(self, doc_type: str) -> Dict[str, Any]:
        """Prepare contexte specifique D10/D12 (import Algerie)."""
        dd = self.documents_data
        cd = self.classification_data

        # Get transport mode label
        transport_mode_labels = {
            'sea': 'Maritime',
            'air': 'Aerien',
            'road': 'Routier',
            'rail': 'Ferroviaire',
            'multimodal': 'Multimodal',
        }

        # Calculate DZD values (approximate exchange rate)
        exchange_rate = Decimal('150.00')  # 1 EUR = 150 DZD approx
        fob = dd.fob_value or dd.invoice_total or Decimal('0')
        freight = dd.freight_cost or Decimal('0')
        insurance = dd.insurance_cost or Decimal('0')
        cif = dd.cif_value or fob

        fob_dzd = fob * exchange_rate if fob else Decimal('0')
        freight_dzd = freight * exchange_rate if freight else Decimal('0')
        insurance_dzd = insurance * exchange_rate if insurance else Decimal('0')
        cif_dzd = cif * exchange_rate if cif else Decimal('0')

        # Calculate duties (approximate)
        duty_rate = Decimal('0.30')  # 30% default
        tva_rate = Decimal('0.19')  # 19% TVA Algeria
        duty_amount = cif_dzd * duty_rate
        tva_base = cif_dzd + duty_amount
        tva_amount = tva_base * tva_rate
        total_duties = duty_amount + tva_amount

        context = {
            # Exporter (from user profile)
            'exporter': {
                'name': self.user.company_name or f"{self.user.first_name} {self.user.last_name}",
                'address': self.user.address_line1 or '',
                'postal_code': self.user.postal_code or '',
                'city': self.user.city or '',
                'country': self.user.country or 'France',
                'eori': self.user.eori_number or '',
            },

            # Consignee/Importer
            'consignee': {
                'name': dd.consignee_name or '',
                'address': dd.consignee_address or '',
                'postal_code': dd.consignee_postal_code or '',
                'city': dd.consignee_city or '',
                'country': dd.consignee_country or 'Algerie',
                'country_code': dd.consignee_country_code or 'DZ',
                'tax_id': dd.consignee_tax_id or '',
            },

            # Origin
            'origin': {
                'origin_country': dd.country_of_origin or 'France',
                'origin_code': dd.country_of_origin_code or 'FR',
                'dispatch_country': dd.country_of_dispatch or 'France',
                'dispatch_code': dd.country_of_dispatch_code or 'FR',
            },

            # Transport
            'transport': {
                'mode': dd.transport_mode or '',
                'mode_code': dd.transport_mode_code or '',
                'mode_label': transport_mode_labels.get(dd.transport_mode, ''),
                'vessel_name': dd.vessel_name or '',
                'document_type': dd.transport_document_type or '',
                'document_ref': dd.transport_document_ref or '',
                'document_date': dd.transport_document_date,
                'port_loading': dd.port_of_loading or '',
                'port_discharge': dd.port_of_discharge or '',
            },

            # Commercial
            'commercial': {
                'incoterms': dd.incoterms or 'CIF',
                'incoterms_location': dd.incoterms_location or '',
            },

            # Invoice
            'invoice': {
                'number': dd.invoice_number or '',
                'date': dd.invoice_date,
                'total': dd.invoice_total or 0,
                'currency': dd.invoice_currency or 'EUR',
            },

            # Goods
            'goods': {
                'description': self.expedition.description or self.expedition.nom_article,
                'taric_code': cd.code_taric if cd else '',
                'packages': dd.number_of_packages or 1,
                'package_type': dd.package_type or 'Carton',
                'quantity': dd.quantity or '',
                'unit': dd.unit_of_measure or '',
                'gross_weight': dd.gross_weight_kg or 0,
                'net_weight': dd.net_weight_kg or 0,
            },

            # Values
            'values': {
                'fob': fob,
                'freight': freight,
                'insurance': insurance,
                'cif': cif,
                'fob_dzd': f"{fob_dzd:,.2f}",
                'freight_dzd': f"{freight_dzd:,.2f}",
                'insurance_dzd': f"{insurance_dzd:,.2f}",
                'cif_dzd': f"{cif_dzd:,.2f}",
                'exchange_rate': f"{exchange_rate:.2f}",
            },

            # Customs
            'customs': {
                'bureau': 'Alger Port',
                'procedure_code': dd.customs_procedure_code or ('10 00' if doc_type == 'd10' else '20 00'),
                'duty_rate': cd.droits_douane if cd else '30%',
                'duty_amount': f"{duty_amount:,.2f}",
                'tcp_rate': '0%',
                'tcp_amount': '0.00',
                'tva_rate': cd.tva if cd else '19%',
                'tva_base': f"{tva_base:,.2f}",
                'tva_amount': f"{tva_amount:,.2f}",
                'total_duties': f"{total_duties:,.2f}",
            },

            # Document type specific
            'is_d10': doc_type == 'd10',
            'is_d12': doc_type == 'd12',
        }

        return context

    def _generate_pdf(self, html_content: str, doc_type: str) -> bytes:
        """Genere le PDF a partir du HTML en utilisant WeasyPrint."""
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration

            font_config = FontConfiguration()

            # Get base URL for static files
            base_url = str(settings.BASE_DIR)

            # Default CSS for forms
            default_css = CSS(string='''
                @page {
                    size: A4;
                    margin: 10mm;
                }
                body {
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 9pt;
                    line-height: 1.3;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                td, th {
                    border: 1px solid #000;
                    padding: 3px 5px;
                    vertical-align: top;
                }
                .box-number {
                    font-size: 7pt;
                    color: #666;
                    position: absolute;
                    top: 1px;
                    left: 2px;
                }
                .box-label {
                    font-size: 7pt;
                    color: #666;
                    text-transform: uppercase;
                }
                .box-content {
                    font-size: 9pt;
                    margin-top: 2px;
                }
                .header {
                    text-align: center;
                    font-weight: bold;
                    font-size: 12pt;
                    margin-bottom: 10px;
                }
                .signature-box {
                    height: 30mm;
                    border: 1px solid #000;
                    padding: 5px;
                }
                .no-border {
                    border: none !important;
                }
                .text-center {
                    text-align: center;
                }
                .text-right {
                    text-align: right;
                }
                .bold {
                    font-weight: bold;
                }
                .small {
                    font-size: 7pt;
                }
            ''', font_config=font_config)

            # Generate PDF
            html = HTML(string=html_content, base_url=base_url)
            pdf_bytes = html.write_pdf(stylesheets=[default_css], font_config=font_config)

            return pdf_bytes

        except ImportError:
            logger.error("WeasyPrint not installed. Install with: pip install weasyprint")
            raise ImportError("WeasyPrint is required for PDF generation. Please install it.")

    def _save_document(self, pdf_content: bytes, doc_type: str):
        """Sauvegarde le document genere."""
        from apps.expeditions.models import ExpeditionDocument

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ref = self.expedition.reference.replace('-', '_')
        filename = f"{doc_type.upper()}_{ref}_{timestamp}.pdf"

        # Create document record
        document = ExpeditionDocument.objects.create(
            etape=self.etape,
            type=doc_type,
            nom_original=filename,
        )

        # Save file
        document.fichier.save(filename, ContentFile(pdf_content))

        return document

    def _update_generation_status(self, doc_type: str):
        """Met a jour le statut de generation."""
        if doc_type == 'dau':
            self.documents_data.dau_genere = True
        elif doc_type == 'd10':
            self.documents_data.d10_genere = True
        elif doc_type == 'd12':
            self.documents_data.d12_genere = True

        self.documents_data.save()

    def get_generation_status(self) -> Dict[str, Any]:
        """Retourne le statut de generation pour chaque document."""
        if self.expedition.direction == 'FR_DZ':
            total = 1
            generated = 1 if self.documents_data.dau_genere else 0
        else:
            total = 1
            generated = 1 if self.documents_data.d10_genere else 0

        return {
            'dau': self.documents_data.dau_genere,
            'd10': self.documents_data.d10_genere,
            'd12': self.documents_data.d12_genere,
            'total': total,
            'generated': generated,
        }

    def get_required_documents(self) -> list:
        """Retourne la liste des documents requis selon la direction avec leurs details."""
        from apps.expeditions.models import ExpeditionDocument

        # Get existing generated documents
        generated_docs = ExpeditionDocument.objects.filter(
            etape=self.etape,
            type__in=['dau', 'd10', 'd12']
        )
        generated_map = {doc.type: doc for doc in generated_docs}

        if self.expedition.direction == 'FR_DZ':
            # France -> Algeria: DAU (EU Export)
            dau_doc = generated_map.get('dau')
            return [{
                'type': 'dau',
                'label': 'DAU - Document Administratif Unique',
                'description': 'Declaration d\'exportation europeenne',
                'generated': self.documents_data.dau_genere,
                'doc_id': dau_doc.pk if dau_doc else None,
            }]
        else:
            # Algeria -> France: D10 (Algerian Import)
            d10_doc = generated_map.get('d10')
            return [{
                'type': 'd10',
                'label': 'D10 - Mise a la consommation',
                'description': 'Declaration d\'importation algerienne',
                'generated': self.documents_data.d10_genere,
                'doc_id': d10_doc.pk if d10_doc else None,
            }]

    def all_documents_generated(self) -> bool:
        """Verifie si tous les documents requis ont ete generes."""
        if self.expedition.direction == 'FR_DZ':
            return self.documents_data.dau_genere
        else:
            return self.documents_data.d10_genere

    def get_generated_documents(self):
        """Retourne les documents deja generes."""
        from apps.expeditions.models import ExpeditionDocument
        return ExpeditionDocument.objects.filter(
            etape=self.etape,
            type__in=['dau', 'd10', 'd12']
        ).order_by('-created_at')
