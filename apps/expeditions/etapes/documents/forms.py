"""
Formulaires pour l'etape 2: Generation de Documents.
Collecte les donnees specifiques a chaque expedition.
"""

from django import forms
from apps.expeditions.models import DocumentsData


class DocumentsDataForm(forms.ModelForm):
    """Formulaire principal pour les donnees du document."""

    class Meta:
        model = DocumentsData
        exclude = [
            'etape', 'dau_genere', 'd10_genere', 'd12_genere',
            'form_completed', 'cif_value', 'statistical_value',
            'transport_mode_code'
        ]
        widgets = {
            # Consignee
            'consignee_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom ou raison sociale'
            }),
            'consignee_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Adresse complete'
            }),
            'consignee_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'consignee_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code postal'
            }),
            'consignee_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pays'
            }),
            'consignee_country_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DZ',
                'maxlength': 2,
                'style': 'text-transform: uppercase;'
            }),
            'consignee_tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'NIF ou EORI'
            }),
            'consignee_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du contact'
            }),
            'consignee_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+213 xxx xxx xxx'
            }),
            'consignee_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            # Invoice
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'FAC-2026-001'
            }),
            'invoice_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'invoice_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'invoice_currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            # Product details
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '1'
            }),
            'unit_of_measure': forms.Select(attrs={
                'class': 'form-select'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'gross_weight_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': '0.000'
            }),
            'net_weight_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': '0.000'
            }),
            'number_of_packages': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '1'
            }),
            'package_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Carton, Palette, Caisse...'
            }),
            # Transport
            'transport_mode': forms.Select(attrs={
                'class': 'form-select',
                'id': 'transport_mode_select'
            }),
            'transport_document_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'transport_document_ref': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numero B/L, AWB, CMR...'
            }),
            'transport_document_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'vessel_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du navire ou numero de vol'
            }),
            'port_of_loading': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Marseille, Paris CDG...'
            }),
            'port_of_discharge': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alger, Oran...'
            }),
            'expected_arrival_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            # Commercial
            'incoterms': forms.Select(attrs={
                'class': 'form-select'
            }),
            'incoterms_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alger, Marseille...'
            }),
            'freight_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'insurance_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            # Origin
            'country_of_origin': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'country_of_origin_code': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2,
                'style': 'text-transform: uppercase;'
            }),
            'country_of_dispatch': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'country_of_dispatch_code': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2,
                'style': 'text-transform: uppercase;'
            }),
            # Customs
            'customs_procedure_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10 00'
            }),
            'customs_procedure_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mise a la consommation'
            }),
            'fob_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, direction='FR_DZ', user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.direction = direction
        self.user = user

        # Pre-fill with user defaults
        if user and not self.instance.pk:
            if hasattr(user, 'default_incoterms') and user.default_incoterms:
                self.fields['incoterms'].initial = user.default_incoterms
            if hasattr(user, 'default_currency') and user.default_currency:
                self.fields['invoice_currency'].initial = user.default_currency

        # Set default consignee country based on direction
        if direction == 'FR_DZ':
            if not self.instance.consignee_country:
                self.fields['consignee_country'].initial = 'Algerie'
                self.fields['consignee_country_code'].initial = 'DZ'
        else:  # DZ_FR
            if not self.instance.consignee_country:
                self.fields['consignee_country'].initial = 'France'
                self.fields['consignee_country_code'].initial = 'FR'
            # Swap default origin for DZ_FR
            if not self.instance.country_of_origin:
                self.fields['country_of_origin'].initial = 'Algerie'
                self.fields['country_of_origin_code'].initial = 'DZ'
                self.fields['country_of_dispatch'].initial = 'Algerie'
                self.fields['country_of_dispatch_code'].initial = 'DZ'

        # Adjust required fields based on direction
        self._set_required_fields()

    def _set_required_fields(self):
        """Define required fields based on document type."""
        required_fields = [
            'consignee_name',
            'consignee_address',
            'consignee_city',
            'consignee_country',
            'invoice_number',
            'invoice_date',
            'invoice_total',
            'quantity',
            'gross_weight_kg',
            'net_weight_kg',
            'transport_mode',
            'incoterms',
            'country_of_origin',
        ]

        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def clean(self):
        cleaned_data = super().clean()

        # Validate weights
        gross = cleaned_data.get('gross_weight_kg')
        net = cleaned_data.get('net_weight_kg')
        if gross and net and net > gross:
            self.add_error('net_weight_kg',
                           'Le poids net ne peut pas etre superieur au poids brut')

        # Set FOB value if not provided
        if not cleaned_data.get('fob_value'):
            cleaned_data['fob_value'] = cleaned_data.get('invoice_total')

        # Uppercase country codes
        for field in ['consignee_country_code', 'country_of_origin_code', 'country_of_dispatch_code']:
            if cleaned_data.get(field):
                cleaned_data[field] = cleaned_data[field].upper()

        return cleaned_data


class UserCustomsProfileForm(forms.Form):
    """Formulaire pour completer le profil douanier de l'utilisateur."""

    company_name = forms.CharField(
        max_length=255,
        label="Nom de l'entreprise",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Raison sociale'
        })
    )
    company_legal_form = forms.CharField(
        max_length=50,
        required=False,
        label="Forme juridique",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'SARL, SAS, EURL...'
        })
    )
    address_line1 = forms.CharField(
        max_length=255,
        label="Adresse",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numero et rue'
        })
    )
    city = forms.CharField(
        max_length=100,
        label="Ville",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    postal_code = forms.CharField(
        max_length=20,
        label="Code postal",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    country = forms.CharField(
        max_length=100,
        label="Pays",
        initial="France",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    eori_number = forms.CharField(
        max_length=17,
        required=False,
        label="Numero EORI",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'FR12345678901234'
        }),
        help_text="Requis pour les exportations EU"
    )
    nif_number = forms.CharField(
        max_length=20,
        required=False,
        label="NIF (Algerie)",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Requis pour les importations en Algerie"
    )
    vat_number = forms.CharField(
        max_length=20,
        required=False,
        label="Numero TVA",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'FR12345678901'
        })
    )
    siret_number = forms.CharField(
        max_length=14,
        required=False,
        label="SIRET",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678901234'
        })
    )
    default_incoterms = forms.ChoiceField(
        choices=[
            ('CIF', 'CIF - Cost Insurance Freight'),
            ('FOB', 'FOB - Free On Board'),
            ('EXW', 'EXW - Ex Works'),
            ('DAP', 'DAP - Delivered At Place'),
            ('DDP', 'DDP - Delivered Duty Paid'),
            ('FCA', 'FCA - Free Carrier'),
            ('CPT', 'CPT - Carriage Paid To'),
            ('CFR', 'CFR - Cost and Freight'),
        ],
        initial='CIF',
        label="Incoterms par defaut",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    default_currency = forms.ChoiceField(
        choices=[
            ('EUR', 'Euro (EUR)'),
            ('DZD', 'Dinar algerien (DZD)'),
            ('USD', 'Dollar US (USD)'),
        ],
        initial='EUR',
        label="Devise par defaut",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned_data = super().clean()

        # At least one customs identifier is required
        eori = cleaned_data.get('eori_number')
        nif = cleaned_data.get('nif_number')

        if not eori and not nif:
            raise forms.ValidationError(
                "Veuillez fournir au moins un identifiant douanier (EORI ou NIF)."
            )

        return cleaned_data
