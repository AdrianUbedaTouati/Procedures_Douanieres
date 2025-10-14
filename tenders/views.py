from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib import messages
from .models import Tender, SavedTender, TenderRecommendation
from company.models import CompanyProfile
from .services import TenderRecommendationService


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
    """Vista de listado de licitaciones con búsqueda y filtros"""
    model = Tender
    template_name = 'tenders/tender_list.html'
    context_object_name = 'tenders'
    paginate_by = 20

    def get_queryset(self):
        queryset = Tender.objects.filter(deadline__gte=timezone.now()).order_by('-publication_date')

        # Búsqueda por texto
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(buyer_name__icontains=search_query)
            )

        # Filtro por tipo de contrato
        contract_type = self.request.GET.get('contract_type')
        if contract_type:
            queryset = queryset.filter(contract_type=contract_type)

        # Filtro por presupuesto
        min_budget = self.request.GET.get('min_budget')
        max_budget = self.request.GET.get('max_budget')
        if min_budget:
            queryset = queryset.filter(budget_amount__gte=min_budget)
        if max_budget:
            queryset = queryset.filter(budget_amount__lte=max_budget)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['contract_type'] = self.request.GET.get('contract_type', '')
        context['min_budget'] = self.request.GET.get('min_budget', '')
        context['max_budget'] = self.request.GET.get('max_budget', '')
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
        tender = super().get_object(queryset)
        # Incrementar contador de vistas
        tender.increment_views()
        return tender

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
        return redirect(request.META.get('HTTP_REFERER', 'tenders:dashboard'))


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

        return redirect('tenders:detail', ojs_notice_id=ojs_notice_id)


class GenerateRecommendationsView(LoginRequiredMixin, View):
    """Vista para generar recomendaciones de licitaciones"""

    def post(self, request):
        # Verificar que el usuario tiene perfil completo
        try:
            company_profile = request.user.company_profile
            if not company_profile.is_complete:
                messages.warning(request, 'Por favor, completa tu perfil de empresa para generar recomendaciones.')
                return redirect('company:profile')
        except CompanyProfile.DoesNotExist:
            messages.warning(request, 'Por favor, crea tu perfil de empresa para generar recomendaciones.')
            return redirect('company:profile')

        # Verificar API key
        if not request.user.llm_api_key:
            messages.warning(request, 'Por favor, configura tu API key del LLM en tu perfil para usar las recomendaciones IA.')
            return redirect('core:edit_profile')

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
                return redirect('tenders:recommended')

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

        return redirect('tenders:recommended')
