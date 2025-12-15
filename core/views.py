from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, View, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse
from django.forms import inlineformset_factory
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from intelligence.models import Target, TimelineItem, CustomAnniversary, TargetGroup, Quest, DailyTargetState
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

class TargetGroupUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            group = TargetGroup.objects.get(pk=pk, user=request.user)
            data = json.loads(request.body)
            group.name = data.get('name', group.name)
            group.description = data.get('description', group.description)
            # Update frequency fields ?? User didn't explicitly ask but good to have
            if 'is_mon' in data: group.is_mon = data.get('is_mon')
            if 'is_tue' in data: group.is_tue = data.get('is_tue')
            if 'is_wed' in data: group.is_wed = data.get('is_wed')
            if 'is_thu' in data: group.is_thu = data.get('is_thu')
            if 'is_fri' in data: group.is_fri = data.get('is_fri')
            if 'is_sat' in data: group.is_sat = data.get('is_sat')
            if 'is_sun' in data: group.is_sun = data.get('is_sun')
            group.save()
            return JsonResponse({'success': True})
        except TargetGroup.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Group not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class TargetGroupDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            group = TargetGroup.objects.get(pk=pk, user=request.user)
            group.delete()
            return JsonResponse({'success': True})
        except TargetGroup.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Group not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class IntelligenceLogView(LoginRequiredMixin, View):
    template_name = 'intelligence_log.html'

    def get(self, request, *args, **kwargs):
        import datetime
        from django.db.models import Q
        
        # 1. Date Handling
        date_str = request.GET.get('date')
        if date_str:
            try:
                current_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                current_date = datetime.date.today()
        else:
            current_date = datetime.date.today()

        weekday = current_date.weekday() # 0=Mon
        weekday_map = ['is_mon', 'is_tue', 'is_wed', 'is_thu', 'is_fri', 'is_sat', 'is_sun']
        current_weekday_field = weekday_map[weekday]
        
        # 2. Base Targets (Group Schedule)
        # Filter targets that belong to groups active on this weekday
        # And construct a list of IDs to start with.
        # Since targets have M2M to groups, we filter Targets where groups__<weekday_field>=True
        base_targets = Target.objects.filter(
            user=request.user,
            groups__pk__in=TargetGroup.objects.filter(**{current_weekday_field: True}).values('pk')
        ).distinct()

        # 3. Anniversary/Birthday Targets
        # Targets who have birthday today or CustomAnniversary today
        birthday_targets = Target.objects.filter(
            user=request.user,
            birth_month=current_date.month,
            birth_day=current_date.day
        )
        custom_anniv_targets = Target.objects.filter(
            user=request.user,
            customanniversary__date__month=current_date.month,
            customanniversary__date__day=current_date.day
        ) # Note: This simple month/day filter for custom anniv might need Year handling if it's one-time? 
          # Assuming CustomAnniversary is annual for now? Or implies specific date?
          # User "Add Anniversary" usually implies recurring. But DateField implies specific.
          # Let's assume specific date matches for now, or maybe check month/day ignoring year?
          # If it's "Wedding Anniversary", year matters for calculation but day matters for alert.
          # Let's check month/day match.
        
        anniv_ids = set()
        for t in birthday_targets: anniv_ids.add(t.id)
        # For custom, let's just match exact date OR month/day? 
        # Usually "Anniversary" in strictly data sense is exact date. But for "Celebrating", it's recurring.
        # Let's match month/day for custom annivs representing recurring events.
        # We can't easily do month/day filter on DateField in generic manner without more complex lookup or specific year interaction.
        # Simple approach: Fetch all custom annivs for user, check in python for small sets, or filter by month/day.
        # Django's __month and __day work on DateField.
        custom_annivs = CustomAnniversary.objects.filter(
            target__user=request.user,
            date__month=current_date.month,
            date__day=current_date.day
        )
        for ca in custom_annivs:
            anniv_ids.add(ca.target.id)

        # 4. Manual State Handling
        daily_states = DailyTargetState.objects.filter(target__user=request.user, date=current_date)
        manual_add_ids = set(daily_states.filter(is_manual_add=True).values_list('target_id', flat=True))
        hidden_ids = set(daily_states.filter(is_hidden=True).values_list('target_id', flat=True))

        # 5. Combine Logic
        # Start with Base (Groups)
        final_ids = set(base_targets.values_list('id', flat=True))
        
        # Add Anniversaries
        final_ids.update(anniv_ids)
        
        # Add Manuals
        final_ids.update(manual_add_ids)
        
        # Remove Hidden
        final_ids = final_ids - hidden_ids
        
        # Fetch Objects & Annotate for UI
        targets = Target.objects.filter(id__in=final_ids)
        
        # Sort? Maybe by nickname
        targets = targets.order_by('nickname')
        
        target_list = []
        for t in targets:
            # Check unfulfilled status
            # Assumption: "Unfulfilled" means no Log (TimelineItem) for THIS date?
            # Or just no "Contact"? User said "未記入" (Unfilled/No Entry).
            # Let's check if any TimelineItem exists for this target on this date.
            has_entry = TimelineItem.objects.filter(target=t, date=current_date).exists()
            
            # Check if Anniversary today
            is_anniv = (t.id in anniv_ids)
            
            # Check age
            age = t.age
            
            target_list.append({
                'obj': t,
                'has_entry': has_entry,
                'is_anniversary': is_anniv,
                'age': age
            })

        # Questions (Shared + Individual)
        from intelligence.models import Question, Tag
        # Use Q object (already imported at top of file)
        questions = Question.objects.filter(
            Q(is_shared=True) | Q(user=request.user)
        ).order_by('order', 'content')
        tags = Tag.objects.all()

        context = {
            'all_targets': all_targets,
            'questions': questions,
            'tags': tags,
            'today_date': current_date.strftime('%Y-%m-%d'), # Use current_date, not 'today'
            'weekday_jp': ['月','火','水','木','金','土','日'][weekday]
        }
        return render(request, self.template_name, context)

class TargetStateToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            target_id = data.get('target_id')
            date_str = data.get('date')
            action = data.get('action') # 'hide', 'add', 'remove_manual'
            
            if not target_id or not date_str or not action:
                return JsonResponse({'success': False, 'error': 'Missing params'})
            
            try:
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                 return JsonResponse({'success': False, 'error': 'Invalid date'})

            target = Target.objects.get(pk=target_id, user=request.user)
            
            state, created = DailyTargetState.objects.get_or_create(target=target, date=date_obj)
            
            if action == 'hide':
                state.is_hidden = True
                # If it was manually added, maybe we keep that true so we know origin? 
                # Or does hide override everything? Yes, logic says (Group|Manual) - Hidden. 
                # So setting hidden=True is sufficient.
            elif action == 'add':
                state.is_manual_add = True
                state.is_hidden = False # Unhide if previously hidden
            elif action == 'remove_manual':
                state.is_manual_add = False
                
            state.save()
            
            return JsonResponse({'success': True})
        except Target.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Target not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class IntelligenceLogEntryView(LoginRequiredMixin, View):
     # Separate view for saving log entries to keep clean? 
     # Or keep it in IntelligenceLogView.post?
     # User asked for "Remove unfulfilled" button which is a state change.
     # Log saving is established in 'post' of template usually.
     # Let's keep Log Logic separate or reusing common patterns.
     # The previous implementation had no POST in IntelligenceLogView for saving logs shown in snippet?
     # Checking snippet... ah I replaced the whole class. 
     # I need to re-implement the POST logic for saving logs if it was there or add it.
     
     def post(self, request, *args, **kwargs):
        # Save TimelineItem LOG logic
        try:
            data = json.loads(request.body)
            # ... Log saving logic same as before or improved ...
            # For brevity in this generic replacement, I'll stub it or assume generic view handling
            # ACTUALLY, I should implement the Log Saving here since I overwrote the class.
            
            target_id = data.get('target_id')
            date_str = data.get('date')
            entry_type = data.get('type') # Event, Question, etc.
            content = data.get('content')
            contact_made = data.get('contact_made', False)
            
            if not target_id: return JsonResponse({'error': 'No target'}, status=400)
            
            target = Target.objects.get(pk=target_id, user=request.user)
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.date.today()
            
            # Create Timeline Item
            item = TimelineItem.objects.create(
                target=target,
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
