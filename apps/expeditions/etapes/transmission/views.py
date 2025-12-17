"""
Vues pour l'étape de Transmission Électronique.
Étape 3 du processus douanier.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from apps.expeditions.models import Expedition


class TransmissionView(LoginRequiredMixin, View):
    """Vue principale de l'étape de transmission."""

    template_name = 'expeditions/etapes/transmission.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier que l'étape 2 est terminée
        etape_2 = expedition.get_etape(2)
        if etape_2.statut != 'termine':
            messages.warning(request, 'Veuillez d\'abord terminer la génération des documents.')
            return redirect('apps_expeditions:documents', pk=pk)

        etape = expedition.get_etape(3)

        context = {
            'expedition': expedition,
            'etape': etape,
            'page_title': f'Transmission - {expedition.reference}',
        }

        return render(request, self.template_name, context)
