"""
Vues pour l'étape de Classification Douanière.
Étape 1 du processus douanier.

Utilise la nouvelle structure:
- ExpeditionEtape (table intermédiaire)
- ClassificationData (données spécifiques 1:1)
- ExpeditionDocument (fichiers liés à l'étape)
"""

import json
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Max

from apps.expeditions.models import (
    Expedition, ExpeditionEtape, ExpeditionDocument, ClassificationData, WebDocument
)
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
        classification_data = etape.get_data()

        # Récupérer les documents de classification séparés par type
        photos = etape.documents.filter(type='photo').order_by('ordre', '-created_at')
        fiches_techniques = etape.documents.filter(type='fiche_technique').order_by('ordre', '-created_at')

        # Récupérer les documents web téléchargés par l'IA
        web_documents = etape.web_documents.all().order_by('-created_at')

        # Vérifier si l'étape est terminée (lecture seule)
        etape_terminee = etape.statut == 'termine'

        context = {
            'expedition': expedition,
            'etape': etape,
            'classification_data': classification_data,
            'photos': photos,
            'fiches_techniques': fiches_techniques,
            'web_documents': web_documents,
            'has_documents': photos.exists() or fiches_techniques.exists(),
            'upload_form': ClassificationUploadForm(),
            'manuel_form': ClassificationManuelleForm(),
            'page_title': f'Classification - {expedition.reference}',
            'etape_terminee': etape_terminee,
        }

        # Si la classification a déjà été faite, pré-remplir le formulaire manuel
        if classification_data and classification_data.code_sh:
            context['classification_result'] = {
                'code_sh': classification_data.code_sh,
                'code_nc': classification_data.code_nc,
                'code_taric': classification_data.code_taric,
            }
            context['manuel_form'] = ClassificationManuelleForm(initial={
                'code_sh': classification_data.code_sh or '',
                'code_nc': classification_data.code_nc or '',
                'code_taric': classification_data.code_taric or '',
            })

        return render(request, self.template_name, context)


class ClassificationUploadView(LoginRequiredMixin, View):
    """Upload de document pour la classification (supporte fichiers multiples)."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Cette étape est terminée. Les documents ne peuvent plus être modifiés.'
                }, status=403)
            messages.error(request, 'Cette étape est terminée. Les documents ne peuvent plus être modifiés.')
            return redirect('apps_expeditions:classification', pk=pk)

        type_doc = request.POST.get('type_document', 'photo')
        fichiers = request.FILES.getlist('fichier')

        if not fichiers:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Aucun fichier sélectionné.'
                }, status=400)
            messages.error(request, 'Aucun fichier sélectionné.')
            return redirect('apps_expeditions:classification', pk=pk)

        # Obtenir le prochain ordre pour ce type de document
        max_ordre = etape.documents.filter(type=type_doc).aggregate(Max('ordre'))['ordre__max'] or 0

        # Récupérer le nom personnalisé si envoyé via AJAX
        nom_personnalise = request.POST.get('nom_personnalise', '').strip()

        documents_crees = []
        for i, fichier in enumerate(fichiers):
            # Vérifier la taille et l'extension
            if fichier.size > 10 * 1024 * 1024:
                continue  # Skip fichiers trop gros

            ext = fichier.name.split('.')[-1].lower()
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']
            if ext not in allowed_extensions:
                continue  # Skip fichiers non autorisés

            # Utiliser le nom personnalisé si fourni, sinon le nom original
            nom_final = nom_personnalise if nom_personnalise else fichier.name

            # S'assurer que l'extension est correcte
            if nom_final and not nom_final.lower().endswith(f'.{ext}'):
                nom_final = f"{nom_final}.{ext}"

            document = ExpeditionDocument.objects.create(
                etape=etape,
                type=type_doc,
                fichier=fichier,
                nom_original=nom_final,
                ordre=max_ordre + i + 1
            )
            documents_crees.append({
                'id': document.id,
                'nom': document.nom_original,
                'url': document.fichier.url,
                'is_image': document.is_image,
                'ordre': document.ordre
            })

        if documents_crees:
            messages.success(request, f'{len(documents_crees)} fichier(s) téléchargé(s) avec succès.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'documents': documents_crees,
                    'message': f'{len(documents_crees)} fichier(s) téléchargé(s)'
                })
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Aucun fichier valide.'
                }, status=400)
            messages.error(request, 'Aucun fichier valide.')

        return redirect('apps_expeditions:classification', pk=pk)


class ClassificationAnalyseView(LoginRequiredMixin, View):
    """Lancer l'analyse IA pour la classification."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )
        etape = expedition.get_etape(1)
        classification_data = etape.get_data()

        # Récupérer le document à analyser
        document = etape.documents.filter(
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

            # Sauvegarder les résultats dans ClassificationData
            if result.get('code_sh'):
                classification_data.code_sh = result.get('code_sh', '')[:6]
            if result.get('code_nc'):
                classification_data.code_nc = result.get('code_nc', '')[:8]
            if result.get('code_taric'):
                classification_data.code_taric = result.get('code_taric', '')[:10]
            classification_data.save()

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
        classification_data = etape.get_data()

        # Vérifier si c'est une validation manuelle
        form = ClassificationManuelleForm(request.POST)

        if form.is_valid():
            # Sauvegarder les codes dans ClassificationData
            classification_data.code_sh = form.cleaned_data['code_sh']
            classification_data.code_nc = form.cleaned_data.get('code_nc', '')
            classification_data.code_taric = form.cleaned_data.get('code_taric', '')
            classification_data.save()

            # Marquer l'étape comme terminée
            etape.marquer_termine()

            messages.success(
                request,
                f'Classification validée: SH {classification_data.code_sh}'
            )

            # Rediriger vers l'étape suivante ou le détail
            return redirect('apps_expeditions:detail', pk=pk)

        messages.error(request, 'Veuillez corriger les erreurs du formulaire.')
        return redirect('apps_expeditions:classification', pk=pk)


class DocumentDeleteView(LoginRequiredMixin, View):
    """Supprimer un document."""

    def post(self, request, pk, doc_id):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Cette étape est terminée. Les documents ne peuvent plus être supprimés.'
                }, status=403)
            messages.error(request, 'Cette étape est terminée. Les documents ne peuvent plus être supprimés.')
            return redirect('apps_expeditions:classification', pk=pk)

        document = get_object_or_404(
            ExpeditionDocument.objects.filter(etape=etape),
            pk=doc_id
        )

        # Supprimer le fichier physique du disque
        if document.fichier:
            file_path = document.fichier.path
            if os.path.isfile(file_path):
                os.remove(file_path)

        document.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Document supprimé'})

        messages.success(request, 'Document supprimé.')
        return redirect('apps_expeditions:classification', pk=pk)


class DocumentRenameView(LoginRequiredMixin, View):
    """Renommer un document."""

    def post(self, request, pk, doc_id):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': 'Cette étape est terminée. Les documents ne peuvent plus être renommés.'
                }, status=403)
            messages.error(request, 'Cette étape est terminée. Les documents ne peuvent plus être renommés.')
            return redirect('apps_expeditions:classification', pk=pk)

        document = get_object_or_404(
            ExpeditionDocument.objects.filter(etape=etape),
            pk=doc_id
        )

        # Lire les données JSON du body ou du POST
        nouveau_nom = ''
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                nouveau_nom = data.get('nouveau_nom', '').strip()
            except json.JSONDecodeError:
                pass
        else:
            nouveau_nom = request.POST.get('nouveau_nom', '').strip()

        if not nouveau_nom:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Nom invalide'}, status=400)
            messages.error(request, 'Nom invalide.')
            return redirect('apps_expeditions:classification', pk=pk)

        # Conserver l'extension originale
        ext = document.nom_original.split('.')[-1] if '.' in document.nom_original else ''
        if ext and not nouveau_nom.endswith(f'.{ext}'):
            nouveau_nom = f'{nouveau_nom}.{ext}'

        document.nom_original = nouveau_nom
        document.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'message': 'Document renommé',
                'nouveau_nom': nouveau_nom
            })

        messages.success(request, 'Document renommé.')
        return redirect('apps_expeditions:classification', pk=pk)


class DocumentReorderView(LoginRequiredMixin, View):
    """Réorganiser l'ordre des documents."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            return JsonResponse({
                'success': False,
                'error': 'Cette étape est terminée. Les documents ne peuvent plus être réorganisés.'
            }, status=403)

        try:
            data = json.loads(request.body)
            ordre_ids = data.get('ordre', [])

            # Mettre à jour l'ordre de chaque document
            for index, doc_id in enumerate(ordre_ids):
                ExpeditionDocument.objects.filter(
                    pk=doc_id,
                    etape=etape
                ).update(ordre=index)

            return JsonResponse({'success': True, 'message': 'Ordre mis à jour'})

        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


# ============================================================================
# VUES API CHAT CLASSIFICATION
# ============================================================================

class ClassificationChatView(LoginRequiredMixin, View):
    """API pour récupérer l'historique du chat de classification."""

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        etape = expedition.get_etape(1)
        classification_data = etape.get_data()

        # Récupérer l'historique depuis le JSONField
        chat_historique = classification_data.chat_historique or []

        # Si le chat est vide, ajouter le message de bienvenue
        if not chat_historique:
            from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
            service = TARICClassificationService(request.user, expedition)
            welcome = service.get_welcome_message()

            # Ajouter le message de bienvenue
            classification_data.add_message(
                role='assistant',
                content=welcome['content']
            )
            chat_historique = classification_data.chat_historique

        # Construire les données des messages avec les proposals
        messages_data = []
        for i, msg in enumerate(chat_historique):
            msg_data = {
                'id': i,
                'role': msg.get('role'),
                'content': msg.get('content'),
                'created_at': msg.get('timestamp'),
                'metadata': msg.get('metadata', {}),
            }
            messages_data.append(msg_data)

        # Ajouter les proposals si elles existent
        proposals_data = []
        if classification_data.propositions:
            for i, prop in enumerate(classification_data.propositions):
                code_taric = prop.get('code_taric', '')
                proposals_data.append({
                    'id': i,
                    'code_sh': prop.get('code_sh', ''),
                    'code_nc': prop.get('code_nc', ''),
                    'code_taric': code_taric,
                    'probability': prop.get('probability', 0),
                    'description': prop.get('description', ''),
                    'justification': prop.get('justification', ''),
                    'droits_douane': prop.get('droits_douane', '-'),
                    'tva': prop.get('tva', '20%'),
                    'lien_taric': prop.get('lien_taric') or f"https://www.tarifdouanier.eu/2026/{code_taric[:8]}" if code_taric else '',
                    'is_selected': i == classification_data.proposition_selectionnee,
                    'formatted_code': self._format_taric_code(code_taric),
                    'confidence_level': self._get_confidence_level(prop.get('probability', 0)),
                    'confidence_color': self._get_confidence_color(prop.get('probability', 0)),
                })

        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'proposals': proposals_data,  # Utiliser proposals_data formate, pas les donnees brutes
            'selected_proposal': classification_data.proposition_selectionnee,
            'etape_terminee': etape.statut == 'termine',
            'has_selected_proposal': classification_data.proposition_selectionnee is not None
        })

    def _format_taric_code(self, code):
        """Formate le code TARIC avec des points."""
        if code and len(code) == 10:
            return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"
        return code

    def _get_confidence_level(self, probability):
        """Retourne le niveau de confiance."""
        if probability >= 80:
            return 'Élevé'
        elif probability >= 60:
            return 'Moyen'
        return 'Faible'

    def _get_confidence_color(self, probability):
        """Retourne la couleur de confiance."""
        if probability >= 80:
            return 'success'
        elif probability >= 60:
            return 'warning'
        return 'danger'


class ClassificationChatMessageView(LoginRequiredMixin, View):
    """API pour envoyer un message au chat de classification."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            return JsonResponse({
                'success': False,
                'error': 'Cette étape est terminée. Le chat est en lecture seule.'
            }, status=403)

        classification_data = etape.get_data()

        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()

            if not user_message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message vide.'
                }, status=400)

            # Sauvegarder le message utilisateur
            classification_data.add_message(role='user', content=user_message)

            # Préparer l'historique pour le service
            history = []
            for msg in classification_data.chat_historique:
                history.append({
                    'role': msg.get('role'),
                    'content': msg.get('content')
                })

            # Traiter le message avec le service TARIC
            from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
            service = TARICClassificationService(request.user, expedition)
            result = service.process_message(user_message, history)

            # Extraer tools_used del metadata
            tools_used = result.get('metadata', {}).get('tools_used', [])

            # Sauvegarder la réponse de l'assistant con metadata
            assistant_msg = classification_data.add_message(
                role='assistant',
                content=result['content'],
                metadata={
                    'tools_used': tools_used,
                    'iterations': result.get('metadata', {}).get('iterations', 0),
                    'review_score': result.get('metadata', {}).get('review', {}).get('final_score', 0)
                }
            )

            # Sauvegarder les proposals si présentes
            proposals_data = []
            raw_proposals = result.get('metadata', {}).get('proposals')
            print(f"[VIEW-CHAT] Raw proposals from service: {raw_proposals}", flush=True)

            if raw_proposals:
                classification_data.set_propositions(raw_proposals)

                for i, prop in enumerate(raw_proposals):
                    code_taric = prop.get('code_taric', '')
                    proposals_data.append({
                        'id': i,
                        'code_sh': prop.get('code_sh', ''),
                        'code_nc': prop.get('code_nc', ''),
                        'code_taric': code_taric,
                        'probability': prop.get('probability', 0),
                        'description': prop.get('description', ''),
                        'justification': prop.get('justification', ''),
                        'droits_douane': prop.get('droits_douane', '-'),
                        'tva': prop.get('tva', '20%'),
                        'lien_taric': prop.get('lien_taric') or f"https://www.tarifdouanier.eu/2026/{code_taric[:8]}" if code_taric else '',
                        'formatted_code': self._format_taric_code(code_taric),
                        'confidence_level': self._get_confidence_level(prop.get('probability', 0)),
                        'confidence_color': self._get_confidence_color(prop.get('probability', 0)),
                    })

            print(f"[VIEW-CHAT] Proposals data to send: {len(proposals_data)} items", flush=True)

            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': len(classification_data.chat_historique) - 2,
                    'role': 'user',
                    'content': user_message,
                    'created_at': classification_data.chat_historique[-2].get('timestamp'),
                },
                'assistant_message': {
                    'id': len(classification_data.chat_historique) - 1,
                    'role': 'assistant',
                    'content': result['content'],
                    'created_at': classification_data.chat_historique[-1].get('timestamp'),
                    'metadata': result.get('metadata', {}),
                    'tools_used': tools_used,
                    'proposals': proposals_data if proposals_data else None,
                }
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON invalide.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def _format_taric_code(self, code):
        """Formate le code TARIC avec des points."""
        if code and len(code) == 10:
            return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"
        return code

    def _get_confidence_level(self, probability):
        """Retourne le niveau de confiance."""
        if probability >= 80:
            return 'Élevé'
        elif probability >= 60:
            return 'Moyen'
        return 'Faible'

    def _get_confidence_color(self, probability):
        """Retourne la couleur de confiance."""
        if probability >= 80:
            return 'success'
        elif probability >= 60:
            return 'warning'
        return 'danger'


class ClassificationAnalyzeDocumentsView(LoginRequiredMixin, View):
    """API pour lancer l'analyse automatique des documents."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            return JsonResponse({
                'success': False,
                'error': 'Cette étape est terminée.'
            }, status=403)

        classification_data = etape.get_data()

        try:
            data = json.loads(request.body)
            additional_context = data.get('context', '').strip()

            # ================================================================
            # ETAPE 1: Appeler get_expedition_documents directement
            # ================================================================
            from agent_ia_core.chatbots.etapes_classification_taric.tools.get_expedition_documents import get_expedition_documents
            from agent_ia_core.chatbots.etapes_classification_taric.tools.analyze_documents import analyze_documents

            docs_result = get_expedition_documents(
                expedition_id=expedition.pk,
                type_filter="all",
                user=request.user
            )

            if not docs_result.get('success') or docs_result.get('total', 0) == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Aucun document à analyser. Veuillez d\'abord télécharger des photos ou fiches techniques.'
                }, status=400)

            # ================================================================
            # ETAPE 2: Appeler analyze_documents directement
            # ================================================================
            analysis_result = analyze_documents(
                expedition_id=expedition.pk,
                document_ids=None,  # Analyser tous les documents
                user=request.user
            )

            # ================================================================
            # ETAPE 3: Construire le contexte avec les résultats des tools
            # ================================================================
            tools_context = "## RÉSULTATS DES OUTILS D'ANALYSE\n\n"

            # Résultat de get_expedition_documents
            tools_context += "### 📁 get_expedition_documents\n"
            tools_context += f"- Référence expédition: {docs_result.get('expedition_reference', 'N/A')}\n"
            tools_context += f"- Produit: {docs_result.get('product_name', 'Non spécifié')}\n"
            tools_context += f"- Documents trouvés: {docs_result.get('summary', '0 documents')}\n"

            if docs_result.get('photos'):
                tools_context += f"- Photos: {', '.join([p['nom'] for p in docs_result['photos']])}\n"
            if docs_result.get('fiches_techniques'):
                tools_context += f"- Fiches techniques: {', '.join([f['nom'] for f in docs_result['fiches_techniques']])}\n"

            tools_context += "\n### 🔍 analyze_documents\n"
            if analysis_result.get('success'):
                tools_context += f"- Documents analysés: {len(analysis_result.get('documents_analyzed', []))}\n"
                tools_context += f"- Méthode: {'Vision IA' if analysis_result.get('images_analyzed', 0) > 0 else 'Extraction texte'}\n"
                if analysis_result.get('analysis'):
                    tools_context += f"\n**Analyse détaillée:**\n{analysis_result['analysis']}\n"
            else:
                tools_context += f"- Erreur: {analysis_result.get('error', 'Erreur inconnue')}\n"

            # Ajouter le contexte utilisateur si présent
            if additional_context:
                tools_context += f"\n### 💬 Informations de l'utilisateur\n{additional_context}\n"

            # ================================================================
            # ETAPE 4: Construire le message pour le LLM
            # ================================================================
            analyze_message = f"""{tools_context}

## INSTRUCTIONS

Basé sur l'analyse automatique des documents ci-dessus, génère une réponse complète pour l'utilisateur avec:

1. **Résumé du produit** identifié à partir des photos/documents
2. **5 propositions de codes TARIC** avec:
   - Code complet (10 chiffres)
   - Probabilité estimée (%)
   - Description officielle
   - Justification

Présente les résultats de manière claire et professionnelle en français.
Si l'analyse n'a pas pu identifier clairement le produit, pose des questions à l'utilisateur."""

            # Sauvegarder le message utilisateur (simplifié pour l'affichage)
            user_display_message = "Analyser les documents"
            if additional_context:
                user_display_message += f": {additional_context}"

            classification_data.add_message(role='user', content=user_display_message)

            # Préparer l'historique pour le service
            history = []
            for msg in classification_data.chat_historique:
                history.append({
                    'role': msg.get('role'),
                    'content': msg.get('content')
                })

            # Traiter avec le service TARIC
            from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
            service = TARICClassificationService(request.user, expedition)
            result = service.process_message(analyze_message, history[:-1])

            # Marquer les tools utilisées (car on les a appelées directement)
            tools_used = ['get_expedition_documents', 'analyze_documents']
            if result.get('metadata', {}).get('tools_used'):
                tools_used.extend(result['metadata']['tools_used'])

            # Sauvegarder la réponse de l'assistant
            classification_data.add_message(
                role='assistant',
                content=result['content'],
                metadata={
                    'tools_used': tools_used,
                    'iterations': result.get('metadata', {}).get('iterations', 0),
                    'review_score': result.get('metadata', {}).get('review', {}).get('final_score', 0)
                }
            )

            # Sauvegarder les proposals si présentes
            proposals_data = []
            raw_proposals = result.get('metadata', {}).get('proposals')
            print(f"[VIEW] Raw proposals from service: {raw_proposals}", flush=True)

            if raw_proposals:
                classification_data.set_propositions(raw_proposals)

                for i, prop in enumerate(raw_proposals):
                    code_taric = prop.get('code_taric', '')
                    proposals_data.append({
                        'id': i,
                        'code_sh': prop.get('code_sh', ''),
                        'code_nc': prop.get('code_nc', ''),
                        'code_taric': code_taric,
                        'probability': prop.get('probability', 0),
                        'description': prop.get('description', ''),
                        'justification': prop.get('justification', ''),
                        'droits_douane': prop.get('droits_douane', '-'),
                        'tva': prop.get('tva', '20%'),
                        'lien_taric': prop.get('lien_taric') or f"https://www.tarifdouanier.eu/2026/{code_taric[:8]}" if code_taric else '',
                        'formatted_code': self._format_taric_code(code_taric),
                    })

            print(f"[VIEW] Proposals data to send: {len(proposals_data)} items", flush=True)

            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': len(classification_data.chat_historique) - 2,
                    'role': 'user',
                    'content': user_display_message,
                    'created_at': classification_data.chat_historique[-2].get('timestamp'),
                },
                'assistant_message': {
                    'id': len(classification_data.chat_historique) - 1,
                    'role': 'assistant',
                    'content': result['content'],
                    'created_at': classification_data.chat_historique[-1].get('timestamp'),
                    'metadata': result.get('metadata', {}),
                    'tools_used': tools_used,
                    'proposals': proposals_data if proposals_data else None,
                }
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON invalide.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def _format_taric_code(self, code):
        """Formate le code TARIC avec des points."""
        if code and len(code) == 10:
            return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"
        return code


class SelectTARICProposalView(LoginRequiredMixin, View):
    """Sélectionner une proposition de code TARIC."""

    def post(self, request, pk, proposal_id):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            return JsonResponse({
                'success': False,
                'error': 'Cette étape est terminée.'
            }, status=403)

        classification_data = etape.get_data()

        # Vérifier que l'index est valide
        if not classification_data.propositions or proposal_id >= len(classification_data.propositions):
            return JsonResponse({
                'success': False,
                'error': 'Proposition invalide.'
            }, status=400)

        # Sélectionner la proposition
        classification_data.select_proposition(proposal_id)
        proposal = classification_data.propositions[proposal_id]

        return JsonResponse({
            'success': True,
            'message': 'Proposition sélectionnée',
            'proposal': {
                'id': proposal_id,
                'code_taric': proposal.get('code_taric', ''),
                'code_nc': proposal.get('code_nc', ''),
                'code_sh': proposal.get('code_sh', ''),
                'probability': proposal.get('probability', 0),
                'description': proposal.get('description', ''),
                'justification': proposal.get('justification', ''),
                'droits_douane': proposal.get('droits_douane', '-'),
                'tva': proposal.get('tva', '20%'),
                'formatted_code': self._format_taric_code(proposal.get('code_taric', '')),
            }
        })

    def _format_taric_code(self, code):
        """Formate le code TARIC avec des points."""
        if code and len(code) == 10:
            return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"
        return code


class ValidateTARICCodeView(LoginRequiredMixin, View):
    """Valider le code TARIC sélectionné et terminer l'étape."""

    def post(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        # Vérifier si l'étape est terminée
        etape = expedition.get_etape(1)
        if etape.statut == 'termine':
            return JsonResponse({
                'success': False,
                'error': 'Cette étape est déjà terminée.'
            }, status=403)

        classification_data = etape.get_data()

        # Récupérer les données de la requête
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        proposal_index = data.get('proposal_index')
        proposal_data = data.get('proposal_data')

        # Si on reçoit les données directement du frontend
        if proposal_data and proposal_data.get('code_taric'):
            selected_proposal = proposal_data
            # Mettre à jour la proposition sélectionnée dans la BD
            if proposal_index is not None and classification_data.propositions:
                classification_data.select_proposition(int(proposal_index))
        else:
            # Fallback: utiliser la proposition déjà sélectionnée
            if classification_data.proposition_selectionnee is None:
                return JsonResponse({
                    'success': False,
                    'error': 'Veuillez d\'abord sélectionner un code TARIC.'
                }, status=400)

            selected_proposal = classification_data.selected_proposal
            if not selected_proposal:
                return JsonResponse({
                    'success': False,
                    'error': 'Proposition invalide.'
                }, status=400)

        # Sauvegarder les codes et taxes dans ClassificationData
        classification_data.code_sh = selected_proposal.get('code_sh', '')[:6] if selected_proposal.get('code_sh') else ''
        classification_data.code_nc = selected_proposal.get('code_nc', '')[:8] if selected_proposal.get('code_nc') else ''
        classification_data.code_taric = selected_proposal.get('code_taric', '')[:10] if selected_proposal.get('code_taric') else ''
        classification_data.droits_douane = selected_proposal.get('droits_douane', '-')[:50] if selected_proposal.get('droits_douane') else '-'
        classification_data.tva = selected_proposal.get('tva', '20%')[:20] if selected_proposal.get('tva') else '20%'
        classification_data.save()

        # Générer le résumé
        from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
        service = TARICClassificationService(request.user, expedition)

        # Récupérer tous les messages pour le résumé
        messages_list = [
            {'role': m.get('role'), 'content': m.get('content')}
            for m in classification_data.chat_historique
        ]

        summary = service.generate_conversation_summary(messages_list, selected_proposal)

        # Ajouter un message système au chat
        classification_data.add_message(
            role='system',
            content=f"Classification validée: {classification_data.formatted_code}"
        )

        # Marquer l'étape comme terminée
        etape.marquer_termine()

        return JsonResponse({
            'success': True,
            'message': 'Classification validée avec succès',
            'result': {
                'code_taric': classification_data.code_taric,
                'code_nc': classification_data.code_nc,
                'code_sh': classification_data.code_sh,
                'description': selected_proposal.get('description', ''),
                'probability': selected_proposal.get('probability', 0),
                'justification': selected_proposal.get('justification', ''),
                'droits_douane': selected_proposal.get('droits_douane', '-'),
                'tva': selected_proposal.get('tva', '20%'),
            },
            'summary': summary
        })


# ============================================================================
# API WEB DOCUMENTS (documentos descargados por el agente IA)
# ============================================================================

class WebDocumentsListView(LoginRequiredMixin, View):
    """API para listar los documentos web descargados por el agente IA."""

    def get(self, request, pk):
        expedition = get_object_or_404(
            Expedition.objects.filter(user=request.user),
            pk=pk
        )

        etape = expedition.get_etape(1)
        web_documents = etape.web_documents.all().order_by('-created_at')

        documents_list = []
        for doc in web_documents:
            documents_list.append({
                'id': doc.id,
                'titulo': doc.titulo,
                'url_origen': doc.url_origen,
                'dominio': doc.dominio_origen,
                'nom_fichier': doc.nom_fichier,
                'tamano': doc.tamano_legible,
                'paginas': doc.paginas,
                'razon': doc.razon_guardado,
                'fichier_url': doc.fichier.url if doc.fichier else None,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
            })

        return JsonResponse({
            'success': True,
            'count': len(documents_list),
            'documents': documents_list
        })
