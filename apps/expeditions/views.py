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

import io
import zipfile
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, Http404

from .models import Expedition, ExpeditionDocument
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


class DownloadDocumentsZipView(LoginRequiredMixin, View):
    """
    Télécharger tous les documents générés d'une étape en ZIP.
    Utilisé principalement pour l'étape 2 (Documents douaniers).
    """

    def get(self, request, pk, etape_numero):
        # Vérifier que l'expédition appartient à l'utilisateur
        expedition = get_object_or_404(
            Expedition,
            pk=pk,
            user=request.user
        )

        # Récupérer l'étape
        etape = expedition.etapes.filter(numero=etape_numero).first()
        if not etape:
            raise Http404("Étape non trouvée")

        # Récupérer les documents de l'étape (PDFs générés)
        documents = ExpeditionDocument.objects.filter(
            etape=etape,
            type__in=['dau', 'd10', 'd12', 'photo', 'fiche_technique', 'autre']
        )

        if not documents.exists():
            messages.warning(request, "Aucun document à télécharger.")
            return redirect('apps_expeditions:detail', pk=pk)

        # Créer le fichier ZIP en mémoire
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for doc in documents:
                if doc.fichier and doc.fichier.name:
                    try:
                        # Lire le contenu du fichier
                        doc.fichier.open('rb')
                        file_content = doc.fichier.read()
                        doc.fichier.close()

                        # Nom du fichier dans le ZIP
                        filename = doc.nom_original or doc.fichier.name.split('/')[-1]

                        # Ajouter au ZIP
                        zip_file.writestr(filename, file_content)
                    except Exception as e:
                        # Log l'erreur mais continue avec les autres fichiers
                        print(f"Erreur lors de l'ajout de {doc.nom_original}: {e}")
                        continue

        # Préparer la réponse
        zip_buffer.seek(0)

        # Nom du fichier ZIP
        zip_filename = f"{expedition.reference}_Etape{etape_numero}_Documents.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = zip_buffer.tell()

        return response
