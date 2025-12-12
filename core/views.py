from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse
from django.forms import inlineformset_factory
from intelligence.models import Target, TimelineItem, CustomAnniversary, TargetGroup
from intelligence.forms import TargetForm, CustomAnniversaryForm, TargetGroupForm
import json

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

# FormSet for Anniversaries
AnniversaryFormSet = inlineformset_factory(
    Target, CustomAnniversary, form=CustomAnniversaryForm,
    extra=1, can_delete=True
)

class TargetCreateView(CreateView):
    model = Target
    form_class = TargetForm
    template_name = 'target_form.html'
    success_url = reverse_lazy('target_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['anniversaries'] = AnniversaryFormSet(self.request.POST)
        else:
            context['anniversaries'] = AnniversaryFormSet()
        context['group_form'] = TargetGroupForm() # For the modal
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        anniversaries = context['anniversaries']
        with transaction.atomic():
            self.object = form.save()
            if anniversaries.is_valid():
                anniversaries.instance = self.object
                anniversaries.save()
        return super().form_valid(form)

class TargetUpdateView(UpdateView):
    model = Target
    form_class = TargetForm
    template_name = 'target_form.html' # Reuse template
    success_url = reverse_lazy('target_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['anniversaries'] = AnniversaryFormSet(self.request.POST, instance=self.object)
        else:
            context['anniversaries'] = AnniversaryFormSet(instance=self.object)
        context['group_form'] = TargetGroupForm()
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        anniversaries = context['anniversaries']
        with transaction.atomic():
            self.object = form.save()
            if anniversaries.is_valid():
                anniversaries.instance = self.object
                anniversaries.save()
        return super().form_valid(form)

class TargetGroupCreateView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description', '')
            if not name:
                return JsonResponse({'success': False, 'error': 'Group name is required'})
            
            group, created = TargetGroup.objects.get_or_create(name=name, defaults={'description': description})
            
            if not created:
                # Update description if exists? Or just return existing.
                # User said "Same name insert impossible", so likely just return error or select existing?
                # "同名のグループはinsert不可" -> Error if not created? Or just simple unique check.
                # get_or_create will get it if exists. 
                # If the user explicitly wants to "Create", finding an existing one might be confusing.
                # But for UX, selecting the existing one is usually fine.
                # Let's return success with the ID.
                return JsonResponse({'success': True, 'id': group.id, 'name': group.name})
            
            return JsonResponse({'success': True, 'id': group.id, 'name': group.name})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
