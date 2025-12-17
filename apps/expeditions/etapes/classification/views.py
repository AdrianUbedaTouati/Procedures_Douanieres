"""
Vues pour l'étape de Classification Douanière.
Étape 1 du processus douanier.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

from apps.expeditions.models import Expedition, ExpeditionDocument
from .forms import ClassificationUploadForm, ClassificationManuelleForm
from .services import ClassificationService


class ClassificationView(LoginRequiredMixin, View):
    """Vue principale de l'étape de classification."""

    template_name = 'expeditions/etapes/classification.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )
        etape = expedition.get_etape(1)

        # Récupérer les documents de classification
        documents = expedition.documents.filter(
            type__in=['photo', 'fiche_technique']
        )

        context = {
            'expedition': expedition,
            'etape': etape,
            'documents': documents,
            'upload_form': ClassificationUploadForm(),
            'manuel_form': ClassificationManuelleForm(),
            'page_title': f'Classification - {expedition.reference}',
        }

        # Si la classification a déjà été faite, pré-remplir le formulaire manuel
        if etape.donnees.get('code_sh'):
            context['classification_result'] = etape.donnees
            context['manuel_form'] = ClassificationManuelleForm(initial={
                'code_sh': etape.donnees.get('code_sh', ''),
                'code_nc': etape.donnees.get('code_nc', ''),
                'code_taric': etape.donnees.get('code_taric', ''),
            })

        return render(request, self.template_name, context)


class ClassificationUploadView(LoginRequiredMixin, View):
    """Upload de document pour la classification."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        form = ClassificationUploadForm(request.POST, request.FILES)

        if form.is_valid():
            fichier = form.cleaned_data['fichier']
            type_doc = form.cleaned_data['type_document']

            # Créer le document
            document = ExpeditionDocument.objects.create(
                expedition=expedition,
                type=type_doc,
                fichier=fichier,
                nom_original=fichier.name,
                etape=expedition.get_etape(1)
            )

            messages.success(request, 'Document téléchargé avec succès.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'document_id': document.id,
                    'message': 'Document téléchargé'
                })

        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)

            messages.error(request, 'Erreur lors du téléchargement.')

        return redirect('apps_expeditions:classification', pk=pk)


class ClassificationAnalyseView(LoginRequiredMixin, View):
    """Lancer l'analyse IA pour la classification."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )
        etape = expedition.get_etape(1)

        # Récupérer le document à analyser
        document = expedition.documents.filter(
            type__in=['photo', 'fiche_technique']
        ).last()

        if not document:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Veuillez d\'abord télécharger un document.'
                }, status=400)

            messages.error(request, 'Veuillez d\'abord télécharger un document.')
            return redirect('apps_expeditions:classification', pk=pk)

        try:
            # Lancer la classification via le service
            service = ClassificationService(request.user, expedition)
            result = service.analyser_document(document)

            # Sauvegarder les résultats dans l'étape
            etape.donnees = result
            etape.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'result': result
                })

            messages.success(request, 'Classification terminée.')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)

            messages.error(request, f'Erreur lors de la classification: {e}')

        return redirect('apps_expeditions:classification', pk=pk)


class ClassificationValiderView(LoginRequiredMixin, View):
    """Valider la classification (automatique ou manuelle)."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )
        etape = expedition.get_etape(1)

        # Vérifier si c'est une validation manuelle
        form = ClassificationManuelleForm(request.POST)

        if form.is_valid():
            donnees = {
                'code_sh': form.cleaned_data['code_sh'],
                'code_nc': form.cleaned_data.get('code_nc', ''),
                'code_taric': form.cleaned_data.get('code_taric', ''),
                'justification': form.cleaned_data.get('justification', ''),
                'mode': 'manuel' if form.cleaned_data.get('justification') else 'automatique',
                'valide': True,
            }

            # Conserver les données de confiance si elles existent
            if etape.donnees.get('confiance_sh'):
                donnees['confiance_sh'] = etape.donnees.get('confiance_sh')
                donnees['confiance_nc'] = etape.donnees.get('confiance_nc')
                donnees['confiance_taric'] = etape.donnees.get('confiance_taric')
                donnees['justification_ia'] = etape.donnees.get('justification', '')

            # Marquer l'étape comme terminée
            etape.marquer_termine(donnees)

            messages.success(
                request,
                f'Classification validée: SH {donnees["code_sh"]}'
            )

            # Rediriger vers l'étape suivante ou le détail
            return redirect('apps_expeditions:detail', pk=pk)

        messages.error(request, 'Veuillez corriger les erreurs du formulaire.')
        return redirect('apps_expeditions:classification', pk=pk)
