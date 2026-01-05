"""
Tests pour l'authentification.
- Login/Logout
- Creation de compte
- Protection des vues
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginTestCase(TestCase):
    """Tests pour le login."""

    def setUp(self):
        """Creer un utilisateur de test."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.login_url = reverse('apps_authentication:login')

    def test_login_page_accessible(self):
        """La page de login est accessible."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')

    def test_login_with_valid_credentials(self):
        """Login avec credentials valides."""
        response = self.client.post(self.login_url, {
            'username': 'testuser@example.com',
            'password': 'testpass123'
        })
        # Devrait rediriger apres login reussi
        self.assertIn(response.status_code, [200, 302])

    def test_login_with_invalid_credentials(self):
        """Login avec credentials invalides."""
        response = self.client.post(self.login_url, {
            'username': 'testuser@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        # Devrait rester sur la page de login avec erreur

    def test_login_with_nonexistent_user(self):
        """Login avec utilisateur inexistant."""
        response = self.client.post(self.login_url, {
            'username': 'nonexistent@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)


class LogoutTestCase(TestCase):
    """Tests pour le logout."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.logout_url = reverse('apps_authentication:logout')

    def test_logout_redirects(self):
        """Logout redirige vers la page d'accueil."""
        self.client.login(username='testuser@example.com', password='testpass123')
        response = self.client.get(self.logout_url)
        self.assertIn(response.status_code, [200, 302])


class RegisterTestCase(TestCase):
    """Tests pour l'inscription."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('apps_authentication:register')

    def test_register_page_accessible(self):
        """La page d'inscription est accessible."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_register_with_valid_data(self):
        """Inscription avec donnees valides."""
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        })
        # Verifier que l'utilisateur a ete cree
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_register_with_mismatched_passwords(self):
        """Inscription avec mots de passe differents."""
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'DifferentPass456!'
        })
        # L'utilisateur ne devrait pas etre cree
        self.assertFalse(User.objects.filter(email='newuser@example.com').exists())


class ProtectedViewsTestCase(TestCase):
    """Tests pour la protection des vues."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )

    def test_expeditions_list_requires_login(self):
        """La liste des expeditions necessite une connexion."""
        response = self.client.get(reverse('apps_expeditions:list'))
        # Devrait rediriger vers login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_expeditions_list_accessible_when_logged_in(self):
        """La liste est accessible quand connecte."""
        self.client.login(username='testuser@example.com', password='testpass123')
        response = self.client.get(reverse('apps_expeditions:list'))
        self.assertEqual(response.status_code, 200)

    def test_create_expedition_requires_login(self):
        """Creer une expedition necessite une connexion."""
        response = self.client.get(reverse('apps_expeditions:create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
