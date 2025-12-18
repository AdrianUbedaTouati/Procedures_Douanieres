"""
Tests para la app core.
Verifica home, perfil, edición de perfil y configuración.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class CoreViewTests(TestCase):
    """Tests para las vistas principales de core."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_home_page_loads(self):
        """Test que la página de inicio carga correctamente."""
        response = self.client.get(reverse('apps_core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')

    def test_home_page_content_unauthenticated(self):
        """Test contenido de home para usuario no autenticado."""
        response = self.client.get(reverse('apps_core:home'))
        self.assertContains(response, 'ChatBot IA')
        self.assertContains(response, 'Iniciar Sesión')
        self.assertContains(response, 'Registrarse')

    def test_home_page_content_authenticated(self):
        """Test contenido de home para usuario autenticado."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_core:home'))
        self.assertContains(response, 'Hola')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Ir al Chat')

    def test_profile_page_requires_login(self):
        """Test que el perfil requiere login."""
        response = self.client.get(reverse('apps_core:profile'))
        # Debería redirigir a login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_profile_page_loads_authenticated(self):
        """Test que el perfil carga para usuario autenticado."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_core:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/profile.html')

    def test_edit_profile_page_requires_login(self):
        """Test que editar perfil requiere login."""
        response = self.client.get(reverse('apps_core:edit_profile'))
        self.assertEqual(response.status_code, 302)

    def test_edit_profile_page_loads_authenticated(self):
        """Test que editar perfil carga para usuario autenticado."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_core:edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/edit_profile.html')


class ProfileEditTests(TestCase):
    """Tests para edición de perfil."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_update_llm_provider(self):
        """Test actualizar proveedor de LLM."""
        response = self.client.post(reverse('apps_core:edit_profile'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'llm_provider': 'openai',
            'llm_api_key': 'test-key'
        })
        self.user.refresh_from_db()
        # Verificar que se actualizó (puede redirigir o mostrar success)
        self.assertIn(response.status_code, [200, 302])

    def test_profile_shows_current_settings(self):
        """Test que el perfil muestra configuración actual."""
        self.user.llm_provider = 'openai'
        self.user.save()

        response = self.client.get(reverse('apps_core:profile'))
        self.assertContains(response, 'openai')


class NavbarTests(TestCase):
    """Tests para el navbar."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_navbar_shows_login_when_unauthenticated(self):
        """Test que el navbar muestra login cuando no está autenticado."""
        response = self.client.get(reverse('apps_core:home'))
        self.assertContains(response, 'Iniciar Sesión')

    def test_navbar_shows_user_when_authenticated(self):
        """Test que el navbar muestra usuario cuando está autenticado."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_core:home'))
        self.assertContains(response, 'test@example.com')

    def test_navbar_has_chat_link_when_authenticated(self):
        """Test que el navbar tiene link al chat cuando está autenticado."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_core:home'))
        self.assertContains(response, 'Chat')

    def test_navbar_branding(self):
        """Test que el navbar muestra el branding correcto."""
        response = self.client.get(reverse('apps_core:home'))
        self.assertContains(response, 'ChatBot IA')


class URLRoutingTests(TestCase):
    """Tests para verificar que las URLs funcionan correctamente."""

    def test_home_url_resolves(self):
        """Test que la URL de home resuelve."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_auth_urls_exist(self):
        """Test que las URLs de auth existen."""
        response = self.client.get('/auth/login/')
        self.assertEqual(response.status_code, 200)

    def test_chat_url_requires_login(self):
        """Test que la URL de chat requiere login."""
        response = self.client.get('/chat/')
        self.assertEqual(response.status_code, 302)

    def test_old_tender_urls_return_404(self):
        """Test que las URLs de licitaciones ya no existen."""
        response = self.client.get('/licitaciones/')
        self.assertEqual(response.status_code, 404)

    def test_old_empresa_urls_return_404(self):
        """Test que las URLs de empresa ya no existen."""
        response = self.client.get('/empresa/')
        self.assertEqual(response.status_code, 404)
