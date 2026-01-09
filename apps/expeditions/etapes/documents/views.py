"""
Vues pour l'etape de Generation des Documents.
Etape 2 du processus douanier.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.urls import reverse

from apps.expeditions.models import Expedition, ExpeditionDocument
from .forms import DocumentsDataForm, UserCustomsProfileForm
from .services import DocumentGenerationService


class DocumentsView(LoginRequiredMixin, View):
    """Vue principale de l'etape de generation des documents."""

    template_name = 'expeditions/etapes/documents.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Verifier que l'etape 1 est terminee
        etape_1 = expedition.get_etape(1)
        if etape_1.statut != 'termine':
            messages.warning(request, 'Veuillez d\'abord terminer la classification.')
            return redirect('apps_expeditions:classification', pk=pk)

        etape = expedition.get_etape(2)
        documents_data = etape.documents_data
        classification_data = etape_1.classification_data

        # Check if user profile is complete
        profile_complete = request.user.has_complete_customs_profile()

        # Get generation service
        service = DocumentGenerationService(expedition, request.user)

        # Get existing generated documents
        generated_docs = service.get_generated_documents()

        context = {
            'expedition': expedition,
            'etape': etape,
            'classification': classification_data,
            'documents_data': documents_data,
            'profile_complete': profile_complete,
            'required_documents': service.get_required_documents(),
            'generation_status': service.get_generation_status(),
            'all_generated': service.all_documents_generated(),
            'form_completed': documents_data.form_completed,
            'generated_docs': generated_docs,
            'page_title': f'Documents - {expedition.reference}',
        }

        return render(request, self.template_name, context)


class DocumentsFormView(LoginRequiredMixin, View):
    """Vue pour le formulaire de saisie des donnees."""

    template_name = 'expeditions/etapes/documents_form.html'

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Check classification is complete
        etape_1 = expedition.get_etape(1)
        if etape_1.statut != 'termine':
            messages.warning(request, 'Veuillez d\'abord terminer la classification.')
            return redirect('apps_expeditions:classification', pk=pk)

        etape = expedition.get_etape(2)
        documents_data = etape.documents_data

        form = DocumentsDataForm(
            instance=documents_data,
            direction=expedition.direction,
            user=request.user
        )

        # Profile form for modal
        profile_form = UserCustomsProfileForm(initial={
            'company_name': request.user.company_name,
            'company_legal_form': request.user.company_legal_form,
            'address_line1': request.user.address_line1,
            'city': request.user.city,
            'postal_code': request.user.postal_code,
            'country': request.user.country,
            'eori_number': request.user.eori_number,
            'nif_number': request.user.nif_number,
            'vat_number': request.user.vat_number,
            'siret_number': request.user.siret_number,
            'default_incoterms': request.user.default_incoterms,
            'default_currency': request.user.default_currency,
        })

        context = {
            'expedition': expedition,
            'etape': etape,
            'form': form,
            'profile_form': profile_form,
            'profile_complete': request.user.has_complete_customs_profile(),
            'classification': etape_1.classification_data,
            'page_title': f'Donnees Document - {expedition.reference}',
        }

        return render(request, self.template_name, context)

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        etape = expedition.get_etape(2)
        documents_data = etape.documents_data

        form = DocumentsDataForm(
            request.POST,
            instance=documents_data,
            direction=expedition.direction,
            user=request.user
        )

        if form.is_valid():
            doc_data = form.save(commit=False)
            doc_data.form_completed = True
            doc_data.calculate_cif_value()
            doc_data.get_transport_mode_code()
            doc_data.save()

            messages.success(request, 'Donnees enregistrees avec succes.')
            return redirect('apps_expeditions:documents', pk=pk)

        # Re-render form with errors
        profile_form = UserCustomsProfileForm()
        etape_1 = expedition.get_etape(1)

        context = {
            'expedition': expedition,
            'etape': etape,
            'form': form,
            'profile_form': profile_form,
            'profile_complete': request.user.has_complete_customs_profile(),
            'classification': etape_1.classification_data,
            'page_title': f'Donnees Document - {expedition.reference}',
        }

        return render(request, self.template_name, context)


class DocumentsPreviewView(LoginRequiredMixin, View):
    """Vue de previsualisation avant generation."""

    template_name = 'expeditions/etapes/documents_preview.html'

    def get(self, request, pk, doc_type):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        service = DocumentGenerationService(expedition, request.user)

        # Validate doc_type
        if doc_type not in service.DOCUMENT_TYPES:
            messages.error(request, 'Type de document invalide.')
            return redirect('apps_expeditions:documents', pk=pk)

        # Check if form is completed
        etape = expedition.get_etape(2)
        if not etape.documents_data.form_completed:
            messages.warning(request, 'Veuillez d\'abord remplir le formulaire de donnees.')
            return redirect('apps_expeditions:documents_form', pk=pk)

        # Get preview context
        context = service._prepare_context(doc_type)
        context.update({
            'expedition': expedition,
            'doc_type': doc_type,
            'doc_info': service.DOCUMENT_TYPES[doc_type],
            'page_title': f'Apercu {doc_type.upper()} - {expedition.reference}',
        })

        return render(request, self.template_name, context)


class GenerateDocumentView(LoginRequiredMixin, View):
    """API pour generer un document PDF."""

    def post(self, request, pk, doc_type):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Check if form is completed
        etape = expedition.get_etape(2)
        if not etape.documents_data.form_completed:
            return JsonResponse({
                'success': False,
                'error': 'Veuillez d\'abord remplir le formulaire de donnees.'
            })

        # Check profile is complete
        if not request.user.has_complete_customs_profile():
            return JsonResponse({
                'success': False,
                'error': 'Veuillez completer votre profil entreprise avant de generer des documents.'
            })

        # Generate document
        service = DocumentGenerationService(expedition, request.user)
        result = service.generate_document(doc_type)

        if result['success']:
            messages.success(request, f'Document {doc_type.upper()} genere avec succes.')

        return JsonResponse(result)


class DownloadDocumentView(LoginRequiredMixin, View):
    """Vue pour telecharger un document genere."""

    def get(self, request, pk, doc_id):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        document = get_object_or_404(
            ExpeditionDocument,
            pk=doc_id,
            etape__expedition=expedition
        )

        # Return file
        response = FileResponse(
            document.fichier.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.nom_original}"'

        return response


class ViewDocumentView(LoginRequiredMixin, View):
    """Vue pour afficher un document dans le navigateur."""

    def get(self, request, pk, doc_id):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        document = get_object_or_404(
            ExpeditionDocument,
            pk=doc_id,
            etape__expedition=expedition
        )

        # Return file for inline viewing
        response = FileResponse(
            document.fichier.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{document.nom_original}"'

        return response


class ValidateDocumentsView(LoginRequiredMixin, View):
    """Vue pour valider l'etape et passer a l'etape suivante."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        service = DocumentGenerationService(expedition, request.user)

        # Check all required documents are generated
        if not service.all_documents_generated():
            return JsonResponse({
                'success': False,
                'error': 'Veuillez generer tous les documents requis avant de valider.'
            })

        # Mark etape as complete
        etape = expedition.get_etape(2)
        etape.marquer_termine()

        messages.success(request, 'Etape Documents validee. Passage a l\'etape de Transmission.')

        return JsonResponse({
            'success': True,
            'redirect_url': reverse('apps_expeditions:transmission', kwargs={'pk': pk})
        })


class UpdateUserProfileView(LoginRequiredMixin, View):
    """Vue pour mettre a jour le profil douanier utilisateur."""

    def post(self, request):
        form = UserCustomsProfileForm(request.POST)

        if form.is_valid():
            user = request.user
            user.company_name = form.cleaned_data['company_name']
            user.company_legal_form = form.cleaned_data.get('company_legal_form', '')
            user.address_line1 = form.cleaned_data['address_line1']
            user.city = form.cleaned_data['city']
            user.postal_code = form.cleaned_data['postal_code']
            user.country = form.cleaned_data['country']
            user.eori_number = form.cleaned_data.get('eori_number', '')
            user.nif_number = form.cleaned_data.get('nif_number', '')
            user.vat_number = form.cleaned_data.get('vat_number', '')
            user.siret_number = form.cleaned_data.get('siret_number', '')
            user.default_incoterms = form.cleaned_data['default_incoterms']
            user.default_currency = form.cleaned_data['default_currency']
            user.save()

            return JsonResponse({'success': True})

        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


class DeleteDocumentView(LoginRequiredMixin, View):
    """Vue pour supprimer un document genere."""

    def post(self, request, pk, doc_id):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        document = get_object_or_404(
            ExpeditionDocument,
            pk=doc_id,
            etape__expedition=expedition
        )

        # Get doc type before deleting
        doc_type = document.type

        # Delete file and record
        if document.fichier:
            document.fichier.delete()
        document.delete()

        # Update generation status
        etape = expedition.get_etape(2)
        if doc_type == 'dau':
            etape.documents_data.dau_genere = False
        elif doc_type == 'd10':
            etape.documents_data.d10_genere = False
        elif doc_type == 'd12':
            etape.documents_data.d12_genere = False
        etape.documents_data.save()

        messages.success(request, 'Document supprime.')

        return JsonResponse({'success': True})
