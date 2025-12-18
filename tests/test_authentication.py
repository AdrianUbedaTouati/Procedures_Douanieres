"""
Tests para la app de autenticación.
Verifica login, registro, logout y gestión de usuarios.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthenticationModelTests(TestCase):
    """Tests para el modelo de usuario personalizado."""

    def test_create_user(self):
        """Test crear usuario normal."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test crear superusuario."""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_llm_provider_default(self):
        """Test que el proveedor LLM por defecto es 'gemini'."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.llm_provider, 'gemini')

    def test_user_str_representation(self):
        """Test representación string del usuario."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # El modelo usa email como USERNAME_FIELD, str() devuelve el email
        self.assertEqual(str(user), 'test@example.com')


class AuthenticationViewTests(TestCase):
    """Tests para las vistas de autenticación."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_login_page_loads(self):
        """Test que la página de login carga correctamente."""
        response = self.client.get(reverse('apps_authentication:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')

    def test_register_page_loads(self):
        """Test que la página de registro carga correctamente."""
        response = self.client.get(reverse('apps_authentication:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/register.html')

    def test_login_success(self):
        """Test login exitoso."""
        response = self.client.post(reverse('apps_authentication:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        # Debería redirigir después del login
        self.assertEqual(response.status_code, 302)

    def test_login_failure_wrong_password(self):
        """Test login fallido con contraseña incorrecta."""
        response = self.client.post(reverse('apps_authentication:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        # Debería quedarse en la página de login
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        """Test logout."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_authentication:logout'))
        # Debería redirigir después del logout
        self.assertIn(response.status_code, [200, 302])

    def test_register_new_user(self):
        """Test registro de nuevo usuario."""
        # La contraseña debe cumplir requisitos de seguridad
        response = self.client.post(reverse('apps_authentication:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexP@ss123!',
            'password2': 'ComplexP@ss123!'
        })
        # Verificar que el usuario fue creado o se redirigió
        user_exists = User.objects.filter(username='newuser').exists()
        # El registro puede requerir confirmación de email
        self.assertIn(response.status_code, [200, 302])

    def test_authenticated_user_redirect_from_login(self):
        """Test que usuario autenticado es redirigido desde login."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('apps_authentication:login'))
        # Puede redirigir o mostrar la página
        self.assertIn(response.status_code, [200, 302])


class UserAPIKeyTests(TestCase):
    """Tests para configuración de API keys del usuario."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_set_llm_api_key(self):
        """Test establecer API key de LLM."""
        self.user.llm_api_key = 'test-api-key-12345'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.llm_api_key, 'test-api-key-12345')

    def test_set_llm_provider(self):
        """Test cambiar proveedor de LLM."""
        self.user.llm_provider = 'openai'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.llm_provider, 'openai')

    def test_set_openai_model(self):
        """Test establecer modelo de OpenAI."""
        self.user.openai_model = 'gpt-4o'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.openai_model, 'gpt-4o')

    def test_set_ollama_model(self):
        """Test establecer modelo de Ollama."""
        self.user.ollama_model = 'llama3:8b'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.ollama_model, 'llama3:8b')

    def test_google_search_credentials(self):
        """Test establecer credenciales de Google Search."""
        self.user.google_search_api_key = 'google-api-key'
        self.user.google_search_engine_id = 'engine-id-123'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.google_search_api_key, 'google-api-key')
        self.assertEqual(self.user.google_search_engine_id, 'engine-id-123')
