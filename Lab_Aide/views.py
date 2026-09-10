from django.views.generic import TemplateView
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import render, redirect

class LandingPageView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #dynamic data for the landing page
        context['year'] = 2026
        return context

def logout_view(request):
    """Log the user out and redirect home with a success message."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/')
        
def terms(request):
    return render(request, "terms.html")
    
def privacy(request):
    return render(request, "privacy.html")

