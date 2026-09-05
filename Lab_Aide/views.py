from django.views.generic import TemplateView
from django.shortcuts import render 

class LandingPageView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #dynamic data for the landing page
        context['year'] = 2026
        return context
        
def terms(request):
    return render(request, "terms.html")
    
def privacy(request):
    return render(request, "privacy.html")

