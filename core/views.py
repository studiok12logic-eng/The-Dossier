from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, View, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse
from django.forms import inlineformset_factory
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from intelligence.models import Target, TimelineItem, CustomAnniversary, TargetGroup, Quest
from intelligence.forms import TargetForm, CustomAnniversaryForm, TargetGroupForm
import json

@login_required
def dashboard(request):
    # Pick the first target owned by the user
    active_target = Target.objects.filter(user=request.user).first()
    timeline = []
    if active_target:
        timeline = TimelineItem.objects.filter(target=active_target).order_by('-date')[:10]
    
    context = {
        'active_target': active_target,
        'timeline': timeline,
    }
    return render(request, 'dashboard.html', context)

@login_required
def target_list(request):
    targets = Target.objects.filter(user=request.user).order_by('-last_contact')
    return render(request, 'target_list.html', {'targets': targets})

# FormSet for Anniversaries
AnniversaryFormSet = inlineformset_factory(
    Target, CustomAnniversary, form=CustomAnniversaryForm,
    extra=1, can_delete=True
)

class TargetCreateView(LoginRequiredMixin, CreateView):
    model = Target
    form_class = TargetForm
    template_name = 'target_form.html'
    success_url = reverse_lazy('target_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

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
            form.instance.user = self.request.user
            self.object = form.save()
            if anniversaries.is_valid():
                anniversaries.instance = self.object
                anniversaries.save()
        return super().form_valid(form)

class TargetUpdateView(LoginRequiredMixin, UpdateView):
    model = Target
    form_class = TargetForm
    template_name = 'target_form.html'
    success_url = reverse_lazy('target_list')

    def get_queryset(self):
        return Target.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

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

class TargetDeleteView(LoginRequiredMixin, DeleteView):
    model = Target
    success_url = reverse_lazy('target_list')
    template_name = 'target_confirm_delete.html' # We might not use this if we do modal or direct post, but standard way needs template. 
    # Actually user asked for button styling, usually implies confirmation.
    
    def get_queryset(self):
        return Target.objects.filter(user=self.request.user)

class TargetGroupCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description', '')
            if not name:
                return JsonResponse({'success': False, 'error': 'Group name is required'})
            
            # Check existing group for THIS user
            group, created = TargetGroup.objects.get_or_create(
                name=name, 
                user=request.user, 
                defaults={
                    'description': description,
                    'is_mon': data.get('is_mon', False),
                    'is_tue': data.get('is_tue', False),
                    'is_wed': data.get('is_wed', False),
                    'is_thu': data.get('is_thu', False),
                    'is_fri': data.get('is_fri', False),
                    'is_sat': data.get('is_sat', False),
                    'is_sun': data.get('is_sun', False),
                }
            )
            
            return JsonResponse({'success': True, 'id': group.id, 'name': group.name})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class IntelligenceLogView(LoginRequiredMixin, View):
    template_name = 'intelligence_log.html'

    def get(self, request, *args, **kwargs):
        import datetime
        today = datetime.datetime.now()
        weekday = today.weekday() # 0=Mon
        weekday_map = ['is_mon', 'is_tue', 'is_wed', 'is_thu', 'is_fri', 'is_sat', 'is_sun']
        current_field = weekday_map[weekday]
        
        # Targets scheduled for today via Groups
        todays_targets = Target.objects.filter(
            user=request.user,
            groups__in=TargetGroup.objects.filter(**{current_field: True, 'user': request.user})
        ).distinct()
        
        all_targets = Target.objects.filter(user=request.user).order_by('nickname')
        
        # Questions (Reuse Quest as Registry for now, or use QuestionRegistry)
        from intelligence.models import QuestionRegistry, Tag
        questions = QuestionRegistry.objects.all().order_by('category')
        tags = Tag.objects.all()

        context = {
            'todays_targets': todays_targets,
            'all_targets': all_targets,
            'questions': questions,
            'tags': tags,
            'today_date': today.strftime('%Y-%m-%d'),
            'weekday_jp': ['月','火','水','木','金','土','日'][weekday]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            target_id = data.get('target_id')
            action_type = data.get('type') # 'EVENT' or 'ANSWER'
            date_str = data.get('date')
            contact_made = data.get('contact_made', False)
            
            target = get_object_or_404(Target, id=target_id, user=request.user)
            
            # Create Timeline Item
            item = TimelineItem(
                target=target,
                type=action_type,
                date=date_str, # Should validate format or use parse
                contact_made=contact_made
            )
            
            if action_type == 'EVENT':
                item.content = data.get('content', '')
                # Tags: handled via set() after save if many-to-many
            elif action_type == 'ANSWER':
                item.question_category = data.get('category', '')
                item.question_text = data.get('question_text', '')
                item.question_answer = data.get('answer', '')
                # Construct content for easy reading
                item.content = f"Q: {item.question_text}\nA: {item.question_answer}"
            
            item.save()
            
            # Handle Tags (assuming list of names provided)
            # if data.get('tags'): ... (Simplified for now)

            if contact_made:
                target.last_contact = datetime.datetime.now() # Or parsed date
                target.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
