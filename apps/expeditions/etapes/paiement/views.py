"""
Vues pour l'étape de Paiement des Droits.
Étape 4 du processus douanier.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from apps.expeditions.models import Expedition


class PaiementView(LoginRequiredMixin, View):
    """Vue principale de l'étape de paiement."""

    template_name = 'expeditions/etapes/paiement.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier que l'étape 3 est terminée
        etape_3 = expedition.get_etape(3)
        if etape_3.statut != 'termine':
            messages.warning(request, 'Veuillez d\'abord terminer la transmission.')
            return redirect('apps_expeditions:transmission', pk=pk)

        etape = expedition.get_etape(4)

        context = {
            'expedition': expedition,
            'etape': etape,
            'page_title': f'Paiement - {expedition.reference}',
        }

        return render(request, self.template_name, context)
