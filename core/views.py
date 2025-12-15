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
    sort_by = request.GET.get('sort', 'last_contact')
    targets = Target.objects.filter(user=request.user)

    if sort_by == 'group':
        targets = targets.order_by('groups__name', 'nickname')
    elif sort_by == 'anniversary':
        # Sort by birth month and day (Upcoming birthdays/anniversaries rough approx)
        # Note: This simply sorts Jan -> Dec. For strict "Upcoming", python sorting is often easier for small lists.
        targets = targets.order_by('birth_month', 'birth_day', 'nickname')
    else: # last_contact
        from django.db.models import F
        targets = targets.order_by(F('last_contact').desc(nulls_last=True), 'nickname')

    return render(request, 'target_list.html', {'targets': targets, 'current_sort': sort_by})

# FormSet for Anniversaries
AnniversaryFormSet = inlineformset_factory(
    Target, CustomAnniversary, form=CustomAnniversaryForm,
    extra=0, can_delete=True
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

        # 1.5 Auto-Add Logic (From Target List LOG button)
        target_id_param = request.GET.get('target_id')
        if target_id_param:
            try:
                auto_target = Target.objects.get(pk=target_id_param, user=request.user)
                # Ensure it's in today's list
                state, _ = DailyTargetState.objects.get_or_create(
                    target=auto_target, date=current_date,
                    defaults={'is_manual_add': True, 'is_hidden': False}
                )
                if not state.is_manual_add and state.is_hidden: # If it was hidden, unhide it
                     state.is_hidden = False
                     state.save()
                elif not state.is_manual_add: # Ensure it is marked as manual add if not already
                     state.is_manual_add = True
                     state.save()
            except Target.DoesNotExist:
                pass
        
        # 2. Base Targets (Group Schedule)
        base_targets = Target.objects.filter(
            user=request.user,
            groups__pk__in=TargetGroup.objects.filter(**{current_weekday_field: True}).values('pk')
        ).distinct()

        # 3. Anniversary/Birthday Targets
        birthday_targets = Target.objects.filter(
            user=request.user,
            birth_month=current_date.month,
            birth_day=current_date.day
        )
        
        anniv_ids = set()
        for t in birthday_targets: anniv_ids.add(t.id)
        
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
        final_ids = set(base_targets.values_list('id', flat=True))
        final_ids.update(anniv_ids)
        final_ids.update(manual_add_ids)
        final_ids = final_ids - hidden_ids
        
        # Fetch Objects & Annotate for UI
        targets = Target.objects.filter(id__in=final_ids).order_by('nickname')
        
        target_list = []
        for t in targets:
            has_entry = TimelineItem.objects.filter(target=t, date=current_date).exists()
            is_anniv = (t.id in anniv_ids)
            age = t.age
            
            target_list.append({
                'obj': t,
                'has_entry': has_entry,
                'is_anniversary': is_anniv,
                'age': age
            })

        # Questions & Tags
        from intelligence.models import Question, Tag
        questions = Question.objects.filter(
            Q(is_shared=True) | Q(user=request.user)
        ).order_by('order', 'title')
        tags = Tag.objects.all()
        
        all_targets = Target.objects.filter(user=request.user)

        from django.db.models import Count
        top_tags = Tag.objects.annotate(count=Count('timelineitem')).order_by('-count')[:10]

        context = {
            'todays_targets': target_list,
            'all_targets': all_targets,
            'questions': questions,
            'tags': top_tags, # Updated to use top_tags
            'today_date': current_date.strftime('%Y-%m-%d'),
            'weekday_jp': ['月','火','水','木','金','土','日'][weekday]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        import datetime
        try:
            data = json.loads(request.body)
            target_id = data.get('target_id')
            date_str = data.get('date')
            entry_type = data.get('type') # EVENT or ANSWER
            content = data.get('content')
            contact_made = data.get('contact_made', False)
            
            if not target_id: 
                return JsonResponse({'success': False, 'error': 'No target specified'})
            
            target = get_object_or_404(Target, pk=target_id, user=request.user)
            
            # Date validation
            if date_str:
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    date_obj = datetime.date.today()
            else:
                date_obj = datetime.date.today()
            
            # Create Timeline Item
            item = TimelineItem(
                target=target,
                date=date_obj,
                contact_made=contact_made
            )
            
            if entry_type == 'EVENT':
                item.content = content
                item.save() # Save first to add m2m
                
                # Tags Handling
                tag_ids = data.get('tags', [])
                if tag_ids:
                    item.tags.set(tag_ids)

                if not content and not contact_made:
                     return JsonResponse({'success': False, 'error': 'Content or Contact is required'})
            elif entry_type == 'ANSWER':
                item.question_category = data.get('category', '')
                item.question_text = data.get('question_text', '')
                item.question_answer = data.get('answer', '')
                item.content = f"Q: {item.question_text}\nA: {item.question_answer}"
                
            item.save()
            
            # Update Last Contact if contact made
            if contact_made:
                target.last_contact = datetime.datetime.now()
                target.save()
                
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class TargetStateToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        import datetime
        from django.db import IntegrityError
        
        try:
            data = json.loads(request.body)
            target_id = data.get('target_id')
            date_str = data.get('date')
            action = data.get('action') # 'add' or 'hide'
            
            if not target_id or not action:
                return JsonResponse({'success': False, 'error': 'Missing parameters'})
                
            target = get_object_or_404(Target, pk=target_id, user=request.user)
            
            if date_str:
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    date_obj = datetime.date.today()
            else:
                date_obj = datetime.date.today()
                
            # Get or Create State
            state, created = DailyTargetState.objects.get_or_create(
                target=target,
                date=date_obj,
                defaults={'is_manual_add': False, 'is_hidden': False}
            )
            
            if action == 'add':
                state.is_manual_add = True
                state.is_hidden = False
            elif action == 'hide':
                state.is_hidden = True
            
            state.save()
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

# --- QUESTION MANAGEMENT ---
from intelligence.models import Question, QuestionCategory, QuestionRank
from intelligence.forms import QuestionForm, QuestionCategoryForm, QuestionRankForm
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

class QuestionListView(LoginRequiredMixin, ListView):
    model = Question
    template_name = 'question_list.html'
    context_object_name = 'questions'

    def get_queryset(self):
        return Question.objects.filter(user=self.request.user).order_by('order', 'created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = QuestionCategory.objects.filter(user=self.request.user)
        context['ranks'] = QuestionRank.objects.filter(user=self.request.user)
        return context

class QuestionCreateView(LoginRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'question_form.html'
    success_url = reverse_lazy('question_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class QuestionUpdateView(LoginRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'question_form.html'
    success_url = reverse_lazy('question_list')

    def get_queryset(self):
        return Question.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class QuestionDeleteView(LoginRequiredMixin, DeleteView):
    model = Question
    success_url = reverse_lazy('question_list')
    template_name = 'question_confirm_delete.html' # Logic will typically be modal or simple confirm
    
    def get_queryset(self):
        return Question.objects.filter(user=self.request.user)

# API Views for Dynamic Add
class CategoryCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get('name')
            desc = data.get('description', '')
            if not name: return JsonResponse({'success': False, 'error': 'Name required'})
            
            cat = QuestionCategory.objects.create(user=request.user, name=name, description=desc)
            return JsonResponse({'success': True, 'id': cat.id, 'name': cat.name})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# --- TIMELINE API ---
class TimelineListAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        target_id = request.GET.get('target_id')
        if not target_id:
            return JsonResponse({'success': False, 'error': 'Target ID required'}, status=400)
            
        try:
            target = Target.objects.get(pk=target_id, user=request.user)
        except Target.DoesNotExist:
             return JsonResponse({'success': False, 'error': 'Target not found'}, status=404)

        # Base Query
        queryset = TimelineItem.objects.filter(target=target).select_related('question')
        
        # Filtering
        import datetime
        from django.db.models import Q
        
        # Type
        event_type = request.GET.get('type') # 'EVENT' or 'QUESTION'
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        # Search Query
        query = request.GET.get('search')
        if query:
            queryset = queryset.filter(
                Q(description__icontains=query) | 
                Q(question__title__icontains=query)
            )

        # Tags (list of IDs)
        tags = request.GET.getlist('tags[]')
        if tags:
            queryset = queryset.filter(tags__id__in=tags).distinct()

        # Pagination (Cursor) - simple date based for now
        before_date = request.GET.get('before_date')
        if before_date:
            queryset = queryset.filter(date__lt=before_date)
            
        # Ordering: Newest first (for chat style bottom-up, usually we load newest first)
        queryset = queryset.order_by('-date', '-created_at')

        # Limit
        limit = int(request.GET.get('limit', 20))
        queryset = queryset[:limit]
        
        # Serialize
        data = []
        for item in queryset:
            data.append({
                'id': item.id,
                'date': item.date.strftime('%Y-%m-%d'),
                'type': item.event_type,
                'description': item.description,
                'question_title': item.question.title if item.question else None,
                'question_category': item.question.category.name if item.question and item.question.category else None,
                'contact_made': item.contact_made,
                'tags': [{'id': t.id, 'name': t.name} for t in item.tags.all()],
            })
            
        return JsonResponse({'success': True, 'data': data})

