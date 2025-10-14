from django.shortcuts import render, redirect
from django.views.generic import UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from .models import CompanyProfile


class CompanyProfileView(LoginRequiredMixin, UpdateView):
    """Vista para ver y editar el perfil de empresa"""
    model = CompanyProfile
    template_name = 'company/profile.html'
    fields = [
        'company_name', 'description', 'sectors', 'certifications', 'size',
        'annual_revenue_eur', 'employees', 'years_in_business', 'geographic_presence',
        'technical_areas', 'programming_languages', 'technologies', 'certifications_technical',
        'relevant_projects', 'public_sector_experience', 'previous_clients',
        'preferred_cpv_codes', 'preferred_contract_types', 'budget_range', 'preferred_regions',
        'max_concurrent_bids', 'avoid_keywords',
        'main_competitors', 'competitive_advantages', 'weaknesses',
        'financial_capacity', 'team_availability', 'overcommitment_risk',
        'is_complete'
    ]
    success_url = reverse_lazy('company:profile')

    def get_object(self, queryset=None):
        # Obtener o crear el perfil de empresa del usuario
        obj, created = CompanyProfile.objects.get_or_create(user=self.request.user)
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Perfil de empresa actualizado correctamente.')
        return super().form_valid(form)


class CompanyProfileDetailView(LoginRequiredMixin, DetailView):
    """Vista de solo lectura del perfil de empresa"""
    model = CompanyProfile
    template_name = 'company/profile_detail.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        # Obtener el perfil del usuario actual
        try:
            return CompanyProfile.objects.get(user=self.request.user)
        except CompanyProfile.DoesNotExist:
            messages.warning(self.request, 'Por favor, crea tu perfil de empresa.')
            return redirect('company:profile')
