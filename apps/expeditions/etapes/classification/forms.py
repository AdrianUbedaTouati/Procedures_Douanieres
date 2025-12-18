"""
Formulaires pour l'étape de Classification Douanière.
"""

from django import forms


class ClassificationUploadForm(forms.Form):
    """Formulaire d'upload pour la classification."""

    UPLOAD_TYPES = [
        ('photo', 'Photo du produit'),
        ('fiche_technique', 'Fiche technique (PDF)'),
    ]

    type_document = forms.ChoiceField(
        choices=UPLOAD_TYPES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='photo',
        label='Type de document'
    )

    fichier = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf'
        }),
        label='Fichier',
        help_text='Formats acceptés: JPG, PNG, PDF'
    )

    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            # Vérifier la taille (max 10 MB)
            if fichier.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Le fichier ne doit pas dépasser 10 MB.')

            # Vérifier l'extension
            ext = fichier.name.split('.')[-1].lower()
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f'Extension non autorisée. Formats acceptés: {", ".join(allowed_extensions)}'
                )

        return fichier


class ClassificationManuelleForm(forms.Form):
    """Formulaire de modification manuelle de la classification."""

    code_sh = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 8471.30'
        }),
        label='Code SH (6 chiffres)',
        help_text='Code du Système Harmonisé'
    )

    code_nc = forms.CharField(
        max_length=12,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 8471.30.00'
        }),
        label='Code NC (8 chiffres)',
        help_text='Nomenclature Combinée (UE)'
    )

    code_taric = forms.CharField(
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 8471.30.00.00'
        }),
        label='Code TARIC (10 chiffres)',
        help_text='Tarif Intégré des Communautés Européennes'
    )

    justification = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Raison de la modification...'
        }),
        required=False,
        label='Justification de la modification'
    )
