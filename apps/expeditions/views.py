"""
Vues principales pour le module Expéditions.
Gestion des expéditions (liste, création, détail, suppression).

Les vues des étapes sont dans leurs modules respectifs:
- etapes/classification/
- etapes/documents/
- etapes/transmission/
- etapes/paiement/
- etapes/oea/
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse

from .models import Expedition
from .forms import ExpeditionForm


class ExpeditionListView(LoginRequiredMixin, ListView):
    """Liste des expéditions de l'utilisateur."""

    model = Expedition
    template_name = 'expeditions/expedition_list.html'
    context_object_name = 'expeditions'
    paginate_by = 10

    def get_queryset(self):
        return Expedition.objects.filter(user=self.request.user).prefetch_related('etapes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Mes Expéditions'

        # Statistiques
        expeditions = self.get_queryset()
        context['stats'] = {
            'total': expeditions.count(),
            'en_cours': expeditions.filter(statut='en_cours').count(),
            'terminees': expeditions.filter(statut='termine').count(),
            'erreurs': expeditions.filter(statut='erreur').count(),
        }

        return context


class ExpeditionCreateView(LoginRequiredMixin, CreateView):
    """Créer une nouvelle expédition."""

    model = Expedition
    form_class = ExpeditionForm
    template_name = 'expeditions/expedition_form.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.statut = 'en_cours'
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Expédition {self.object.reference} créée avec succès.'
        )
        return response

    def get_success_url(self):
        return reverse('apps_expeditions:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Nouvelle Expédition'
        return context


class ExpeditionDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une expédition avec ses étapes."""

    model = Expedition
    template_name = 'expeditions/expedition_detail.html'
    context_object_name = 'expedition'

    def get_queryset(self):
        return Expedition.objects.filter(user=self.request.user).prefetch_related('etapes', 'etapes__documents')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Expédition {self.object.reference}'
        context['etapes'] = self.object.etapes.all().order_by('numero')
        # Les documents sont maintenant dans les étapes
        return context


class ExpeditionDeleteView(LoginRequiredMixin, DeleteView):
    """Supprimer une expédition."""

    model = Expedition
    success_url = reverse_lazy('apps_expeditions:list')

    def get_queryset(self):
        return Expedition.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        expedition = self.get_object()
        messages.success(request, f'Expédition {expedition.reference} supprimée.')
        return super().delete(request, *args, **kwargs)
