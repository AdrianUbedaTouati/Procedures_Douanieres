"""
Formulaires principaux pour le module Expéditions.

Les formulaires des étapes sont dans leurs modules respectifs:
- etapes/classification/forms.py
- etapes/documents/forms.py (à créer)
- etc.
"""

from django import forms
from .models import Expedition


class ExpeditionForm(forms.ModelForm):
    """Formulaire de création/modification d'une expédition."""

    class Meta:
        model = Expedition
        fields = ['nom_article', 'description', 'direction']
        widgets = {
            'nom_article': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Ordinateur portable Dell XPS 15'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description détaillée du produit...'
            }),
            'direction': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'nom_article': 'Nom de l\'article',
            'description': 'Description (optionnel)',
            'direction': 'Direction de l\'expédition',
        }
