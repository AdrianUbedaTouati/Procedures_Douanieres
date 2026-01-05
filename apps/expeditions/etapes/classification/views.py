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
    Expedition, ExpeditionEtape, ExpeditionDocument, ClassificationData
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

        # Vérifier si l'étape est terminée (lecture seule)
        etape_terminee = etape.statut == 'termine'

        context = {
            'expedition': expedition,
            'etape': etape,
            'classification_data': classification_data,
            'photos': photos,
            'fiches_techniques': fiches_techniques,
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
        if classification_data.propositions:
            proposals_data = []
            for i, prop in enumerate(classification_data.propositions):
                proposals_data.append({
                    'id': i,
                    'code_sh': prop.get('code_sh', ''),
                    'code_nc': prop.get('code_nc', ''),
                    'code_taric': prop.get('code_taric', ''),
                    'probability': prop.get('probability', 0),
                    'description': prop.get('description', ''),
                    'justification': prop.get('justification', ''),
                    'is_selected': i == classification_data.proposition_selectionnee,
                    'formatted_code': self._format_taric_code(prop.get('code_taric', '')),
                    'confidence_level': self._get_confidence_level(prop.get('probability', 0)),
                    'confidence_color': self._get_confidence_color(prop.get('probability', 0)),
                })

        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'proposals': classification_data.propositions or [],
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

            # Sauvegarder la réponse de l'assistant
            assistant_msg = classification_data.add_message(
                role='assistant',
                content=result['content']
            )

            # Sauvegarder les proposals si présentes
            proposals_data = []
            if result.get('metadata', {}).get('proposals'):
                proposals = result['metadata']['proposals']
                classification_data.set_propositions(proposals)

                for i, prop in enumerate(proposals):
                    proposals_data.append({
                        'id': i,
                        'code_sh': prop.get('code_sh', ''),
                        'code_nc': prop.get('code_nc', ''),
                        'code_taric': prop.get('code_taric', ''),
                        'probability': prop.get('probability', 0),
                        'description': prop.get('description', ''),
                        'justification': prop.get('justification', ''),
                        'formatted_code': self._format_taric_code(prop.get('code_taric', '')),
                        'confidence_level': self._get_confidence_level(prop.get('probability', 0)),
                        'confidence_color': self._get_confidence_color(prop.get('probability', 0)),
                    })

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

        # Vérifier qu'une proposition est sélectionnée
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

        # Générer le résumé
        from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
        service = TARICClassificationService(request.user, expedition)

        # Récupérer tous les messages pour le résumé
        messages_list = [
            {'role': m.get('role'), 'content': m.get('content')}
            for m in classification_data.chat_historique
        ]

        summary = service.generate_conversation_summary(messages_list, selected_proposal)

        # Valider la classification (copie les codes dans ClassificationData)
        classification_data.validate_classification()

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
            },
            'summary': summary
        })
