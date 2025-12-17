"""
Vues pour l'étape de Gestion OEA.
Étape 5 du processus douanier.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from apps.expeditions.models import Expedition


class OeaView(LoginRequiredMixin, View):
    """Vue principale de l'étape OEA."""

    template_name = 'expeditions/etapes/oea.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier que l'étape 4 est terminée
        etape_4 = expedition.get_etape(4)
        if etape_4.statut != 'termine':
            messages.warning(request, 'Veuillez d\'abord terminer le paiement.')
            return redirect('apps_expeditions:paiement', pk=pk)

        etape = expedition.get_etape(5)

        context = {
            'expedition': expedition,
            'etape': etape,
            'page_title': f'OEA - {expedition.reference}',
        }

        return render(request, self.template_name, context)
