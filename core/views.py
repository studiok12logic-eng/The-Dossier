from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from intelligence.models import Target, TimelineItem
from intelligence.forms import TargetForm

def dashboard(request):
    # For now, just pick the first target or None if empty
    active_target = Target.objects.first()
    timeline = []
    if active_target:
        timeline = TimelineItem.objects.filter(target=active_target).order_by('-date')[:10]
    
    context = {
        'active_target': active_target,
        'timeline': timeline,
    }
    return render(request, 'dashboard.html', context)

def target_list(request):
    targets = Target.objects.all().order_by('-last_contact')
    return render(request, 'target_list.html', {'targets': targets})

class TargetCreateView(CreateView):
    model = Target
    form_class = TargetForm
    template_name = 'target_form.html'
    success_url = reverse_lazy('target_list')
