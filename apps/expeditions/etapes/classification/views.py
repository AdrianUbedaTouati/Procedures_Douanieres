"""
Vues pour l'étape de Classification Douanière.
Étape 1 du processus douanier.
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Max

from apps.expeditions.models import (
    Expedition, ExpeditionDocument,
    ClassificationChat, ClassificationMessage, TARICProposal
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

        # Récupérer les documents de classification séparés par type
        photos = expedition.documents.filter(type='photo').order_by('ordre', '-created_at')
        fiches_techniques = expedition.documents.filter(type='fiche_technique').order_by('ordre', '-created_at')

        # Vérifier si l'étape est terminée (lecture seule)
        etape_terminee = etape.statut == 'termine'

        context = {
            'expedition': expedition,
            'etape': etape,
            'photos': photos,
            'fiches_techniques': fiches_techniques,
            'has_documents': photos.exists() or fiches_techniques.exists(),
            'upload_form': ClassificationUploadForm(),
            'manuel_form': ClassificationManuelleForm(),
            'page_title': f'Classification - {expedition.reference}',
            'etape_terminee': etape_terminee,
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
        max_ordre = expedition.documents.filter(type=type_doc).aggregate(Max('ordre'))['ordre__max'] or 0

        documents_crees = []
        for i, fichier in enumerate(fichiers):
            # Vérifier la taille et l'extension
            if fichier.size > 10 * 1024 * 1024:
                continue  # Skip fichiers trop gros

            ext = fichier.name.split('.')[-1].lower()
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']
            if ext not in allowed_extensions:
                continue  # Skip fichiers non autorisés

            document = ExpeditionDocument.objects.create(
                expedition=expedition,
                type=type_doc,
                fichier=fichier,
                nom_original=fichier.name,
                etape=expedition.get_etape(1),
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
            ExpeditionDocument.objects.filter(expedition=expedition),
            pk=doc_id
        )

        # Supprimer le fichier physique
        if document.fichier:
            document.fichier.delete(save=False)

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
            ExpeditionDocument.objects.filter(expedition=expedition),
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
                    expedition=expedition
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

        # Récupérer ou créer le chat
        chat, created = ClassificationChat.objects.get_or_create(
            expedition=expedition
        )

        # Récupérer les messages
        messages_qs = chat.messages.all().order_by('created_at')

        messages_data = []
        for msg in messages_qs:
            msg_data = {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'metadata': msg.metadata,
            }

            # Ajouter les proposals si présentes
            if msg.metadata.get('has_proposals'):
                proposals = msg.proposals.all().order_by('-probability')
                msg_data['proposals'] = [{
                    'id': p.id,
                    'code_sh': p.code_sh,
                    'code_nc': p.code_nc,
                    'code_taric': p.code_taric,
                    'probability': p.probability,
                    'description': p.description,
                    'justification': p.justification,
                    'is_selected': p.is_selected,
                    'formatted_code': p.formatted_code,
                    'confidence_level': p.confidence_level,
                    'confidence_color': p.confidence_color,
                } for p in proposals]

            messages_data.append(msg_data)

        # Vérifier l'état de l'étape
        etape = expedition.get_etape(1)

        # Si chat vient d'être créé, ajouter message de bienvenue
        if created:
            from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
            service = TARICClassificationService(request.user, expedition)
            welcome = service.get_welcome_message()

            welcome_msg = ClassificationMessage.objects.create(
                chat=chat,
                role='assistant',
                content=welcome['content'],
                metadata=welcome['metadata']
            )

            messages_data.append({
                'id': welcome_msg.id,
                'role': welcome_msg.role,
                'content': welcome_msg.content,
                'created_at': welcome_msg.created_at.isoformat(),
                'metadata': welcome_msg.metadata,
            })

        return JsonResponse({
            'success': True,
            'chat_id': chat.id,
            'messages': messages_data,
            'etape_terminee': etape.statut == 'termine',
            'has_selected_proposal': chat.messages.filter(
                proposals__is_selected=True
            ).exists()
        })


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

        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()

            if not user_message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message vide.'
                }, status=400)

            # Récupérer le chat
            chat, _ = ClassificationChat.objects.get_or_create(
                expedition=expedition
            )

            # Sauvegarder le message utilisateur
            user_msg = ClassificationMessage.objects.create(
                chat=chat,
                role='user',
                content=user_message,
                metadata={'type': 'user_input'}
            )

            # Préparer l'historique pour le service
            history = []
            for msg in chat.messages.exclude(pk=user_msg.pk).order_by('created_at'):
                history.append({
                    'role': msg.role,
                    'content': msg.content
                })

            # Traiter le message avec le service TARIC
            from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
            service = TARICClassificationService(request.user, expedition)
            result = service.process_message(user_message, history)

            # Sauvegarder la réponse de l'assistant
            assistant_msg = ClassificationMessage.objects.create(
                chat=chat,
                role='assistant',
                content=result['content'],
                metadata=result.get('metadata', {})
            )

            # Sauvegarder les proposals si présentes
            proposals_data = []
            if result.get('metadata', {}).get('proposals'):
                for i, prop in enumerate(result['metadata']['proposals']):
                    proposal = TARICProposal.objects.create(
                        message=assistant_msg,
                        code_sh=prop.get('code_sh', '')[:6],
                        code_nc=prop.get('code_nc', '')[:8],
                        code_taric=prop.get('code_taric', '')[:10],
                        probability=prop.get('probability', 0),
                        description=prop.get('description', '')[:255],
                        justification=prop.get('justification', ''),
                        ordre=i
                    )
                    proposals_data.append({
                        'id': proposal.id,
                        'code_sh': proposal.code_sh,
                        'code_nc': proposal.code_nc,
                        'code_taric': proposal.code_taric,
                        'probability': proposal.probability,
                        'description': proposal.description,
                        'justification': proposal.justification,
                        'formatted_code': proposal.formatted_code,
                        'confidence_level': proposal.confidence_level,
                        'confidence_color': proposal.confidence_color,
                    })

            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': user_msg.id,
                    'role': 'user',
                    'content': user_msg.content,
                    'created_at': user_msg.created_at.isoformat(),
                },
                'assistant_message': {
                    'id': assistant_msg.id,
                    'role': 'assistant',
                    'content': assistant_msg.content,
                    'created_at': assistant_msg.created_at.isoformat(),
                    'metadata': assistant_msg.metadata,
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

        # Récupérer la proposition
        proposal = get_object_or_404(
            TARICProposal.objects.filter(
                message__chat__expedition=expedition
            ),
            pk=proposal_id
        )

        # Désélectionner toutes les autres
        TARICProposal.objects.filter(
            message__chat__expedition=expedition
        ).update(is_selected=False)

        # Sélectionner celle-ci
        proposal.is_selected = True
        proposal.save()

        return JsonResponse({
            'success': True,
            'message': 'Proposition sélectionnée',
            'proposal': {
                'id': proposal.id,
                'code_taric': proposal.code_taric,
                'code_nc': proposal.code_nc,
                'code_sh': proposal.code_sh,
                'probability': proposal.probability,
                'description': proposal.description,
                'justification': proposal.justification,
                'formatted_code': proposal.formatted_code,
            }
        })


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

        # Récupérer le chat
        try:
            chat = expedition.classification_chat
        except ClassificationChat.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Aucun chat trouvé pour cette expédition.'
            }, status=404)

        # Récupérer la proposition sélectionnée
        selected_proposal = TARICProposal.objects.filter(
            message__chat=chat,
            is_selected=True
        ).first()

        if not selected_proposal:
            return JsonResponse({
                'success': False,
                'error': 'Veuillez d\'abord sélectionner un code TARIC.'
            }, status=400)

        # Générer le résumé
        from agent_ia_core.chatbots.etapes_classification_taric import TARICClassificationService
        service = TARICClassificationService(request.user, expedition)

        # Récupérer tous les messages pour le résumé
        messages_list = list(chat.messages.values('role', 'content'))
        proposal_dict = {
            'code_taric': selected_proposal.code_taric,
            'code_nc': selected_proposal.code_nc,
            'code_sh': selected_proposal.code_sh,
            'probability': selected_proposal.probability,
            'description': selected_proposal.description,
            'justification': selected_proposal.justification,
        }

        summary = service.generate_conversation_summary(messages_list, proposal_dict)

        # Préparer les données de l'étape
        donnees = {
            'code_sh': selected_proposal.code_sh,
            'code_nc': selected_proposal.code_nc,
            'code_taric': selected_proposal.code_taric,
            'description': selected_proposal.description,
            'confiance': selected_proposal.probability,
            'justification': selected_proposal.justification,
            'mode': 'chatbot',
            'valide': True,
            'summary': summary,
        }

        # Marquer l'étape comme terminée
        etape.marquer_termine(donnees)

        # Ajouter un message système au chat
        ClassificationMessage.objects.create(
            chat=chat,
            role='system',
            content=f"Classification validée: {selected_proposal.formatted_code}",
            metadata={
                'type': 'validation',
                'code_taric': selected_proposal.code_taric,
                'summary': summary
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Classification validée avec succès',
            'result': {
                'code_taric': selected_proposal.code_taric,
                'code_nc': selected_proposal.code_nc,
                'code_sh': selected_proposal.code_sh,
                'description': selected_proposal.description,
                'probability': selected_proposal.probability,
                'justification': selected_proposal.justification,
            },
            'summary': summary
        })
