"""
Vues pour l'étape de Génération des Documents.
Étape 2 du processus douanier.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from apps.expeditions.models import Expedition


class DocumentsView(LoginRequiredMixin, View):
    """Vue principale de l'étape de génération des documents."""

    template_name = 'expeditions/etapes/documents.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier que l'étape 1 est terminée
        etape_1 = expedition.get_etape(1)
        if etape_1.statut != 'termine':
            messages.warning(request, 'Veuillez d\'abord terminer la classification.')
            return redirect('apps_expeditions:classification', pk=pk)

        etape = expedition.get_etape(2)

        # Récupérer les données de classification depuis ClassificationData
        classification_data = etape_1.get_data()

        context = {
            'expedition': expedition,
            'etape': etape,
            'classification': classification_data,
            'page_title': f'Documents - {expedition.reference}',
        }

        return render(request, self.template_name, context)
