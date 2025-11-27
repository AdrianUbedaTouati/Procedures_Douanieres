from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib import messages
from .models import Tender, SavedTender, TenderRecommendation
from apps.company.models import CompanyProfile
from .services import TenderRecommendationService
from .ted_downloader import download_and_save_tenders
import json
import threading


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard principal con estadísticas y licitaciones destacadas"""
    template_name = 'tenders/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Verificar si tiene perfil de empresa completo
        try:
            company_profile = user.company_profile
            context['has_company_profile'] = company_profile.is_complete
        except CompanyProfile.DoesNotExist:
            context['has_company_profile'] = False
            company_profile = None

        # Estadísticas básicas
        context['total_tenders'] = Tender.objects.count()
        context['saved_tenders_count'] = SavedTender.objects.filter(user=user).count()

        # Licitaciones recomendadas (top 5)
        if company_profile and company_profile.is_complete:
            context['recommended_tenders'] = TenderRecommendation.objects.filter(
                user=user,
                recommendation_level__in=['alta', 'media']
            ).select_related('tender').order_by('-score_total')[:5]
        else:
            context['recommended_tenders'] = []

        # Licitaciones recientes
        context['recent_tenders'] = Tender.objects.filter(
            deadline__gte=timezone.now()
        ).order_by('-publication_date')[:10]

        # Licitaciones guardadas por estado
        saved_by_status = SavedTender.objects.filter(user=user).values('status').annotate(
            count=Count('id')
        )
        context['saved_by_status'] = {item['status']: item['count'] for item in saved_by_status}

        return context


class TenderListView(LoginRequiredMixin, ListView):
    """Vista de listado de licitaciones con filtros basados en Agent_IA"""
    model = Tender
    template_name = 'tenders/tender_list.html'
    context_object_name = 'tenders'
    paginate_by = 20

    def get_queryset(self):
        """
        Aplica filtros estructurados basados en Agent_IA:
        - CPV codes
        - NUTS regions
        - Contract type
        - Procedure type
        - Budget range (min/max)
        - Publication date range
        - Deadline date range
        - Buyer name (partial match)
        """
        queryset = Tender.objects.all().order_by('-publication_date')

        # 1. Filtro por CPV codes (lista separada por comas)
        cpv_codes = self.request.GET.get('cpv_codes', '').strip()
        if cpv_codes:
            # Separar por comas y limpiar
            cpv_list = [code.strip() for code in cpv_codes.split(',') if code.strip()]
            if cpv_list:
                # Usar búsqueda de texto en JSON serializado (compatible con SQLite)
                q_objects = Q()
                for cpv in cpv_list:
                    # Buscar en la representación de texto del JSON
                    q_objects |= Q(cpv_codes__icontains=f'"{cpv}"')
                queryset = queryset.filter(q_objects)

        # 2. Filtro por NUTS regions (lista separada por comas)
        nuts_regions = self.request.GET.get('nuts_regions', '').strip()
        if nuts_regions and nuts_regions.lower() != 'all':  # Permitir "all" para todas las regiones
            nuts_list = [region.strip() for region in nuts_regions.split(',') if region.strip()]
            if nuts_list:
                # Usar búsqueda de texto en JSON serializado (compatible con SQLite)
                q_objects = Q()
                for nuts in nuts_list:
                    # Buscar en la representación de texto del JSON
                    q_objects |= Q(nuts_regions__icontains=f'"{nuts}"')
                queryset = queryset.filter(q_objects)

        # 3. Filtro por tipo de contrato
        contract_type = self.request.GET.get('contract_type', '').strip()
        if contract_type:
            queryset = queryset.filter(contract_type=contract_type)

        # 4. Filtro por tipo de procedimiento
        procedure_type = self.request.GET.get('procedure_type', '').strip()
        if procedure_type:
            queryset = queryset.filter(procedure_type=procedure_type)

        # 5. Filtro por presupuesto (rango)
        budget_min = self.request.GET.get('budget_min', '').strip()
        budget_max = self.request.GET.get('budget_max', '').strip()
        if budget_min:
            try:
                queryset = queryset.filter(budget_amount__gte=float(budget_min))
            except ValueError:
                pass
        if budget_max:
            try:
                queryset = queryset.filter(budget_amount__lte=float(budget_max))
            except ValueError:
                pass

        # 6. Filtro por fecha de publicación (rango O días atrás)
        # Prioridad: si hay "days_ago", usarlo; sino usar rango from/to
        days_ago = self.request.GET.get('days_ago', '').strip()
        if days_ago:
            # Modo simple: últimos X días
            try:
                days = int(days_ago)
                from datetime import timedelta
                date_threshold = timezone.now().date() - timedelta(days=days)
                queryset = queryset.filter(publication_date__gte=date_threshold)
            except ValueError:
                pass
        else:
            # Modo experto: rango de fechas específicas
            publication_from = self.request.GET.get('publication_from', '').strip()
            publication_to = self.request.GET.get('publication_to', '').strip()
            if publication_from:
                queryset = queryset.filter(publication_date__gte=publication_from)
            if publication_to:
                queryset = queryset.filter(publication_date__lte=publication_to)

        # 7. Filtro por fecha límite (rango) - Opcional
        deadline_from = self.request.GET.get('deadline_from', '').strip()
        deadline_to = self.request.GET.get('deadline_to', '').strip()
        if deadline_from:
            queryset = queryset.filter(tender_deadline_date__gte=deadline_from)
        if deadline_to:
            queryset = queryset.filter(tender_deadline_date__lte=deadline_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Verificar si la base de datos está vacía
        total_tenders = Tender.objects.count()
        context['db_empty'] = total_tenders == 0
        context['total_tenders_in_db'] = total_tenders

        # Verificar si se ha realizado una búsqueda
        has_filters = any([
            self.request.GET.get('cpv_codes'),
            self.request.GET.get('nuts_regions'),
            self.request.GET.get('contract_type'),
            self.request.GET.get('procedure_type'),
            self.request.GET.get('budget_min'),
            self.request.GET.get('budget_max'),
            self.request.GET.get('days_ago'),
            self.request.GET.get('publication_from'),
            self.request.GET.get('publication_to'),
            self.request.GET.get('deadline_from'),
            self.request.GET.get('deadline_to'),
        ])
        context['has_filters'] = has_filters

        # Precargar datos del perfil de empresa si existe (solo si no hay filtros activos)
        if not has_filters:
            try:
                profile = self.request.user.company_profile
                # Precargar códigos CPV del perfil (sectores de la empresa)
                if profile.preferred_cpv_codes:
                    context['cpv_codes'] = ','.join(profile.preferred_cpv_codes)
                # Precargar regiones NUTS del perfil
                if profile.preferred_nuts_regions:
                    context['nuts_regions'] = ','.join(profile.preferred_nuts_regions)
                # Precargar rango de presupuesto del perfil
                if profile.budget_range:
                    context['budget_min'] = profile.budget_range.get('min', '')
                    context['budget_max'] = profile.budget_range.get('max', '')
            except CompanyProfile.DoesNotExist:
                pass

        # Pasar todos los filtros al template para mantener el estado (sobrescribir solo si vienen del GET)
        context['cpv_codes'] = self.request.GET.get('cpv_codes', context.get('cpv_codes', ''))
        context['nuts_regions'] = self.request.GET.get('nuts_regions', context.get('nuts_regions', ''))
        context['contract_type'] = self.request.GET.get('contract_type', '')
        context['procedure_type'] = self.request.GET.get('procedure_type', '')
        context['budget_min'] = self.request.GET.get('budget_min', context.get('budget_min', ''))
        context['budget_max'] = self.request.GET.get('budget_max', context.get('budget_max', ''))
        context['days_ago'] = self.request.GET.get('days_ago', '')
        context['publication_from'] = self.request.GET.get('publication_from', '')
        context['publication_to'] = self.request.GET.get('publication_to', '')
        context['deadline_from'] = self.request.GET.get('deadline_from', '')
        context['deadline_to'] = self.request.GET.get('deadline_to', '')

        # Construir query string para paginación
        params = self.request.GET.copy()
        if 'page' in params:
            del params['page']
        if params:
            context['query_string'] = '&' + params.urlencode()
        else:
            context['query_string'] = ''

        return context


class RecommendedTendersView(LoginRequiredMixin, ListView):
    """Vista de licitaciones recomendadas para el usuario"""
    model = TenderRecommendation
    template_name = 'tenders/recommended_tenders.html'
    context_object_name = 'recommendations'
    paginate_by = 20

    def get_queryset(self):
        return TenderRecommendation.objects.filter(
            user=self.request.user
        ).select_related('tender').order_by('-score_total')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Verificar si tiene perfil completo
        try:
            company_profile = self.request.user.company_profile
            context['has_company_profile'] = company_profile.is_complete
        except CompanyProfile.DoesNotExist:
            context['has_company_profile'] = False

        return context


class TenderDetailView(LoginRequiredMixin, DetailView):
    """Vista de detalle de una licitación"""
    model = Tender
    template_name = 'tenders/tender_detail.html'
    context_object_name = 'tender'
    slug_field = 'ojs_notice_id'
    slug_url_kwarg = 'ojs_notice_id'

    def get_object(self, queryset=None):
        try:
            tender = super().get_object(queryset)
            # Incrementar contador de vistas
            tender.increment_views()
            return tender
        except Tender.DoesNotExist:
            # Si no existe en BD, redirigir a TED Europa
            ojs_notice_id = self.kwargs.get(self.slug_url_kwarg)
            ted_url = f"https://ted.europa.eu/es/notice/-/detail/{ojs_notice_id}"

            # Añadir mensaje informativo
            messages.info(
                self.request,
                f"La licitación {ojs_notice_id} no está descargada en tu base de datos. "
                f"Te redirigimos a TED Europa para verla."
            )

            # Redirigir a TED
            from django.shortcuts import redirect
            return redirect(ted_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Verificar si está guardada
        context['is_saved'] = SavedTender.objects.filter(
            user=user,
            tender=self.object
        ).exists()

        # Obtener recomendación si existe
        try:
            recommendation = TenderRecommendation.objects.get(
                user=user,
                tender=self.object
            )
            context['recommendation'] = recommendation
        except TenderRecommendation.DoesNotExist:
            context['recommendation'] = None

        return context


class SavedTendersView(LoginRequiredMixin, ListView):
    """Vista de licitaciones guardadas por el usuario"""
    model = SavedTender
    template_name = 'tenders/saved_tenders.html'
    context_object_name = 'saved_tenders'
    paginate_by = 20

    def get_queryset(self):
        queryset = SavedTender.objects.filter(user=self.request.user).select_related('tender')

        # Filtro por estado
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-saved_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class SaveTenderView(LoginRequiredMixin, View):
    """Vista para guardar/desguardar una licitación"""

    def post(self, request, ojs_notice_id):
        tender = get_object_or_404(Tender, ojs_notice_id=ojs_notice_id)

        saved_tender, created = SavedTender.objects.get_or_create(
            user=request.user,
            tender=tender
        )

        if created:
            messages.success(request, 'Licitación guardada correctamente.')
        else:
            saved_tender.delete()
            messages.info(request, 'Licitación eliminada de guardados.')

        # Si es AJAX, devolver JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'saved': created})

        # Si no, redirigir a la página anterior
        return redirect(request.META.get('HTTP_REFERER', 'apps_tenders:dashboard'))


class UpdateSavedTenderStatusView(LoginRequiredMixin, View):
    """Vista para actualizar el estado de una licitación guardada"""

    def post(self, request, ojs_notice_id):
        tender = get_object_or_404(Tender, ojs_notice_id=ojs_notice_id)
        saved_tender = get_object_or_404(SavedTender, user=request.user, tender=tender)

        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        if new_status in dict(SavedTender.STATUS_CHOICES):
            saved_tender.status = new_status
            if notes:
                saved_tender.notes = notes
            saved_tender.save()
            messages.success(request, 'Estado actualizado correctamente.')
        else:
            messages.error(request, 'Estado no válido.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('apps_tenders:detail', ojs_notice_id=ojs_notice_id)


class GenerateRecommendationsView(LoginRequiredMixin, View):
    """Vista para generar recomendaciones de licitaciones"""

    def post(self, request):
        # Verificar que el usuario tiene perfil completo
        try:
            company_profile = request.user.company_profile
            if not company_profile.is_complete:
                messages.warning(request, 'Por favor, completa tu perfil de empresa para generar recomendaciones.')
                return redirect('apps_company:profile')
        except CompanyProfile.DoesNotExist:
            messages.warning(request, 'Por favor, crea tu perfil de empresa para generar recomendaciones.')
            return redirect('apps_company:profile')

        # Verificar API key (Ollama no la necesita)
        user_provider = getattr(request.user, 'llm_provider', 'gemini')
        if not request.user.llm_api_key and user_provider != 'ollama':
            messages.warning(request, 'Por favor, configura tu API key del LLM en tu perfil para usar las recomendaciones IA.')
            return redirect('apps_core:edit_profile')

        # Generar recomendaciones usando Agent_IA
        try:
            # Initialize recommendation service
            rec_service = TenderRecommendationService(request.user)

            # Get active tenders (not yet processed for this user)
            active_tenders = Tender.objects.filter(
                deadline__gte=timezone.now()
            ).exclude(
                tenderrecommendation__user=request.user
            )[:50]  # Limit to 50 tenders per batch

            if not active_tenders:
                messages.info(request, 'No hay nuevas licitaciones para recomendar. Ya has evaluado todas las disponibles.')
                return redirect('apps_tenders:recommended')

            # Generate recommendations
            recommendations_data = rec_service.generate_recommendations(active_tenders)

            # Save recommendations to database
            created_count = 0
            for rec_data in recommendations_data:
                TenderRecommendation.objects.create(
                    user=request.user,
                    tender=rec_data['tender'],
                    score_total=rec_data['score_total'],
                    score_technical=rec_data['score_technical'],
                    score_budget=rec_data['score_budget'],
                    score_geographic=rec_data['score_geographic'],
                    score_experience=rec_data['score_experience'],
                    score_competition=rec_data['score_competition'],
                    probability_success=rec_data['probability_success'],
                    recommendation_level=rec_data['recommendation_level'],
                    match_reasons=rec_data['match_reasons'],
                    warning_factors=rec_data['warning_factors'],
                    contact_info=rec_data['contact_info']
                )
                created_count += 1

            messages.success(request, f'Se generaron {created_count} nuevas recomendaciones basadas en tu perfil.')

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al generar recomendaciones: {str(e)}')

        return redirect('apps_tenders:recommended')


class DownloadTendersFormView(LoginRequiredMixin, TemplateView):
    """Vista que muestra el formulario para configurar la descarga de licitaciones"""
    template_name = 'tenders/tender_download.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasar el total de licitaciones en la BD
        context['total_tenders'] = Tender.objects.count()

        # Precargar datos del perfil de empresa si existe (recargar siempre del DB)
        try:
            # Force refresh from database to get latest data
            profile = CompanyProfile.objects.get(user=self.request.user)
            # Precargar códigos CPV del perfil (sectores de la empresa)
            if profile.preferred_cpv_codes:
                context['default_cpv_codes'] = ','.join(profile.preferred_cpv_codes)
            else:
                context['default_cpv_codes'] = '7226'  # Default: Software
        except CompanyProfile.DoesNotExist:
            context['default_cpv_codes'] = '7226'  # Default: Software

        return context

    def dispatch(self, request, *args, **kwargs):
        """Evitar cache del navegador para siempre obtener datos frescos"""
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class DownloadTendersExecuteView(LoginRequiredMixin, View):
    """Vista con SSE para descargar licitaciones y enviar progreso en tiempo real"""

    def get(self, request):
        import sys
        from datetime import date, datetime

        # Obtener parámetros de la URL
        days_back = int(request.GET.get('days_back', 30))
        max_download = int(request.GET.get('max_download', 50))

        # Obtener parámetros de filtros de búsqueda
        cpv_codes_str = request.GET.get('cpv_codes', '').strip()
        cpv_codes = [code.strip() for code in cpv_codes_str.split(',') if code.strip()] if cpv_codes_str else None

        place = request.GET.get('place', '').strip() or None
        notice_type = request.GET.get('notice_type', '').strip() or None

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[DOWNLOAD START] Iniciando descarga de licitaciones", file=sys.stderr)
        print(f"  - Días atrás: {days_back}", file=sys.stderr)
        print(f"  - Máximo descargas: {max_download}", file=sys.stderr)
        print(f"  - CPV Codes: {cpv_codes}", file=sys.stderr)
        print(f"  - Place: {place}", file=sys.stderr)
        print(f"  - Notice Type: {notice_type}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

        def json_serial(obj):
            """JSON serializer para objetos date/datetime"""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        def event_stream():
            """Generador que envía eventos SSE"""
            try:
                # Enviar evento de inicio
                yield f"data: {json.dumps({'type': 'start', 'message': 'Iniciando búsqueda en TED API...'})}\n\n"
                print("[SSE] Evento START enviado", file=sys.stderr)

                # Queue para comunicación entre el download y SSE
                import queue
                event_queue = queue.Queue()

                # Función callback que pone eventos en la queue
                def progress_callback(data):
                    print(f"[CALLBACK] Recibido: {data}", file=sys.stderr)
                    event_queue.put(data)

                # Ejecutar descarga en thread separado
                def run_download():
                    try:
                        print("[THREAD] Iniciando download_and_save_tenders", file=sys.stderr)
                        result = download_and_save_tenders(
                            days_back=days_back,
                            max_download=max_download,
                            cpv_codes=cpv_codes,
                            place=place,
                            notice_type=notice_type,
                            progress_callback=progress_callback,
                            user_id=request.user.id
                        )
                        print(f"[THREAD] Descarga completada: {result}", file=sys.stderr)
                        event_queue.put({'type': 'complete', 'result': result})
                    except Exception as e:
                        print(f"[THREAD ERROR] {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        event_queue.put({'type': 'error', 'message': str(e)})
                    finally:
                        event_queue.put(None)  # Señal de fin

                import threading
                download_thread = threading.Thread(target=run_download)
                download_thread.daemon = True
                download_thread.start()
                print("[THREAD] Thread de descarga iniciado", file=sys.stderr)

                # Procesar eventos de la queue y enviarlos como SSE
                while True:
                    try:
                        # Esperar evento con timeout
                        event_data = event_queue.get(timeout=1.0)

                        if event_data is None:
                            # Fin de descarga
                            print("[SSE] Fin de eventos", file=sys.stderr)
                            break

                        # Serializar y enviar
                        print(f"[SSE] Enviando evento: {event_data.get('type', 'unknown')}", file=sys.stderr)
                        json_data = json.dumps(event_data, default=json_serial)
                        yield f"data: {json_data}\n\n"

                    except queue.Empty:
                        # Timeout - enviar heartbeat para mantener conexión viva
                        yield f": heartbeat\n\n"
                        continue

                print("[SSE] Stream completado", file=sys.stderr)

            except Exception as e:
                print(f"[SSE ERROR] {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        return response


class CancelDownloadView(LoginRequiredMixin, View):
    """Vista para cancelar la descarga en proceso"""

    def post(self, request):
        from .ted_downloader import set_cancel_flag
        try:
            # Establecer el flag de cancelación para este usuario
            set_cancel_flag(request.user.id)

            return JsonResponse({
                'success': True,
                'message': 'Cancelación solicitada. La descarga se detendrá después del archivo actual.'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class DeleteAllXMLsView(LoginRequiredMixin, View):
    """Vista para borrar todos los XMLs (licitaciones) de la cuenta del usuario"""

    def post(self, request):
        try:
            from pathlib import Path
            from agent_ia_core.config import XML_DIR

            # Contar licitaciones antes de borrar
            count = Tender.objects.count()

            # Obtener lista de archivos XML a borrar
            tenders = Tender.objects.all()
            xml_files_deleted = 0

            for tender in tenders:
                # Intentar borrar archivo XML si existe
                if tender.source_path:
                    xml_file = Path(tender.source_path)
                    if xml_file.exists():
                        try:
                            xml_file.unlink()
                            xml_files_deleted += 1
                        except Exception as e:
                            print(f"Error borrando archivo {xml_file}: {e}")
                else:
                    # Intentar con el nombre por defecto
                    xml_file = XML_DIR / f"{tender.ojs_notice_id}.xml"
                    if xml_file.exists():
                        try:
                            xml_file.unlink()
                            xml_files_deleted += 1
                        except Exception as e:
                            print(f"Error borrando archivo {xml_file}: {e}")

            # Borrar todas las licitaciones (esto también borrará SavedTender y TenderRecommendation por CASCADE)
            Tender.objects.all().delete()

            return JsonResponse({
                'success': True,
                'deleted_count': count,
                'xml_files_deleted': xml_files_deleted,
                'message': f'{count} licitaciones borradas exitosamente ({xml_files_deleted} archivos XML eliminados)'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class DeleteXMLView(LoginRequiredMixin, View):
    """Vista para borrar una licitación individual"""

    def post(self, request, ojs_notice_id):
        try:
            from pathlib import Path
            from agent_ia_core.config import XML_DIR

            tender = get_object_or_404(Tender, ojs_notice_id=ojs_notice_id)
            title = tender.title

            # Intentar borrar archivo XML si existe
            xml_deleted = False
            if tender.source_path:
                xml_file = Path(tender.source_path)
                if xml_file.exists():
                    try:
                        xml_file.unlink()
                        xml_deleted = True
                    except Exception as e:
                        print(f"Error borrando archivo {xml_file}: {e}")
            else:
                # Intentar con el nombre por defecto
                xml_file = XML_DIR / f"{tender.ojs_notice_id}.xml"
                if xml_file.exists():
                    try:
                        xml_file.unlink()
                        xml_deleted = True
                    except Exception as e:
                        print(f"Error borrando archivo {xml_file}: {e}")

            # Borrar la licitación de la BD
            tender.delete()

            message = f'Licitación "{title}" borrada exitosamente'
            if xml_deleted:
                message += ' (archivo XML eliminado)'

            return JsonResponse({
                'success': True,
                'xml_deleted': xml_deleted,
                'message': message
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


# ============================================================================
# VECTORIZACIÓN Y GESTIÓN DE CHROMADB
# ============================================================================

class VectorizationDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard para gestionar la vectorización e indexación de licitaciones"""
    template_name = 'tenders/vectorization_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Verificar API key (Ollama no la necesita)
        user_provider = getattr(self.request.user, 'llm_provider', 'gemini')
        if not self.request.user.llm_api_key and user_provider != 'ollama':
            context['has_api_key'] = False
            context['status'] = {
                'is_initialized': False,
                'status': 'no_api_key',
                'message': 'Por favor, configura tu API key de LLM en tu perfil.'
            }
            return context

        context['has_api_key'] = True

        # Obtener estado del vectorstore
        from .vectorization_service import VectorizationService
        service = VectorizationService(user=self.request.user)
        context['status'] = service.get_vectorstore_status()

        # Contar licitaciones con XML disponibles
        context['tenders_with_xml'] = Tender.objects.exclude(
            xml_content=''
        ).exclude(
            xml_content__isnull=True
        ).count()

        context['total_tenders'] = Tender.objects.count()

        return context


class IndexAllTendersView(LoginRequiredMixin, View):
    """Vista con SSE para indexar todas las licitaciones con progreso en tiempo real"""

    def get(self, request):
        import sys
        from datetime import date, datetime
        from .cancel_flags import check_cancel_flag, clear_cancel_flag

        # Verificar API key (Ollama no la necesita)
        user_provider = getattr(request.user, 'llm_provider', 'gemini')
        if not request.user.llm_api_key and user_provider != 'ollama':
            return JsonResponse({
                'error': 'Por favor, configura tu API key de LLM en tu perfil.'
            }, status=400)

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[INDEXING START] Iniciando indexación de licitaciones", file=sys.stderr)
        print(f"  - Usuario: {request.user.username}", file=sys.stderr)
        print(f"  - Proveedor: {request.user.llm_provider}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

        # Clear any previous cancel flags for this user
        clear_cancel_flag(request.user.id, 'indexing')

        def json_serial(obj):
            """JSON serializer para objetos date/datetime"""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        def event_stream():
            """Generador que envía eventos SSE"""
            try:
                # Enviar evento de inicio
                yield f"data: {json.dumps({'type': 'start', 'message': 'Iniciando indexación...'})}\n\n"
                print("[SSE] Evento START enviado", file=sys.stderr)

                # Queue para comunicación entre el indexing y SSE
                import queue
                event_queue = queue.Queue()

                # Función callback que pone eventos en la queue
                def progress_callback(data):
                    print(f"[CALLBACK] Recibido: {data}", file=sys.stderr)
                    event_queue.put(data)

                # Función para checkear cancelación
                def cancel_flag_checker():
                    is_cancelled = check_cancel_flag(request.user.id, 'indexing')
                    if is_cancelled:
                        print(f"[CANCEL CHECK] Cancelación detectada para user {request.user.id}", file=sys.stderr)
                    return is_cancelled

                # Ejecutar indexación en thread separado
                def run_indexing():
                    try:
                        from .vectorization_service import VectorizationService

                        print("[THREAD] Iniciando indexación", file=sys.stderr)
                        service = VectorizationService(user=request.user)
                        result = service.index_all_tenders(
                            progress_callback=progress_callback,
                            cancel_flag_checker=cancel_flag_checker
                        )

                        print(f"[THREAD] Indexación completada: {result}", file=sys.stderr)
                        event_queue.put({'type': 'complete', 'result': result})
                    except Exception as e:
                        print(f"[THREAD ERROR] {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        event_queue.put({'type': 'error', 'message': str(e)})
                    finally:
                        # Clear cancel flag when done
                        clear_cancel_flag(request.user.id, 'indexing')
                        event_queue.put(None)  # Señal de fin

                download_thread = threading.Thread(target=run_indexing)
                download_thread.daemon = True
                download_thread.start()
                print("[THREAD] Thread de indexación iniciado", file=sys.stderr)

                # Procesar eventos de la queue y enviarlos como SSE
                while True:
                    try:
                        # Esperar evento con timeout
                        event_data = event_queue.get(timeout=1.0)

                        if event_data is None:
                            # Fin de indexación
                            print("[SSE] Fin de eventos", file=sys.stderr)
                            break

                        # Serializar y enviar
                        print(f"[SSE] Enviando evento: {event_data.get('type', 'unknown')}", file=sys.stderr)
                        json_data = json.dumps(event_data, default=json_serial)
                        yield f"data: {json_data}\n\n"

                    except queue.Empty:
                        # Timeout - enviar heartbeat para mantener conexión viva
                        yield f": heartbeat\n\n"
                        continue

                print("[SSE] Stream completado", file=sys.stderr)

            except Exception as e:
                print(f"[SSE ERROR] {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        return response


class ClearVectorstoreView(LoginRequiredMixin, View):
    """Vista para limpiar (borrar) el vectorstore completo"""

    def post(self, request):
        try:
            from .vectorization_service import VectorizationService

            service = VectorizationService(user=request.user)
            result = service.clear_vectorstore()

            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': result['message']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Error desconocido')
                }, status=500)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class CancelIndexingView(LoginRequiredMixin, View):
    """Vista para cancelar la indexación en proceso"""

    def post(self, request):
        from .cancel_flags import set_cancel_flag
        try:
            # Establecer el flag de cancelación para este usuario
            set_cancel_flag(request.user.id, 'indexing')

            return JsonResponse({
                'success': True,
                'message': 'Cancelación solicitada. La indexación se detendrá después del chunk actual.'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class VectorstoreStatusAPIView(LoginRequiredMixin, View):
    """API JSON para obtener el estado actual del vectorstore"""

    def get(self, request):
        try:
            from .vectorization_service import VectorizationService

            service = VectorizationService(user=request.user)
            status = service.get_vectorstore_status()

            return JsonResponse(status)

        except Exception as e:
            return JsonResponse({
                'is_initialized': False,
                'status': 'error',
                'error': str(e)
            }, status=500)
