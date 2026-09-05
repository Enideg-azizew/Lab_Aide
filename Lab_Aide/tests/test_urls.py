from django.test import TestCase
from django.urls import reverse, resolve
from Lab_Aide.views import LandingPageView, terms, privacy

class MainAppURLsTest(TestCase):
    """Test main application URL configuration."""
    
    def test_home_url(self):
        """Test home page URL."""
        url = reverse('home')
        self.assertEqual(url, '/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, LandingPageView)
    
    def test_terms_url(self):
        """Test terms page URL."""
        url = reverse('terms')
        self.assertEqual(url, '/terms/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, terms)
    
    def test_privacy_url(self):
        """Test privacy page URL."""
        url = reverse('privacy')
        self.assertEqual(url, '/privacy/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, privacy)
    
    def test_admin_url(self):
        """Test admin URL."""
        url = reverse('admin:index')
        self.assertEqual(url, '/admin/')
