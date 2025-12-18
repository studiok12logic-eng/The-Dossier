from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, View, DeleteView, DetailView
from core.mixins import MobileTemplateMixin
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse
from django.forms import inlineformset_factory
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from intelligence.models import Target, TimelineItem, CustomAnniversary, TargetGroup, DailyTargetState
from intelligence.forms import TargetForm, CustomAnniversaryForm, TargetGroupForm
import json

@login_required
def dashboard(request):
    import datetime
    from django.db.models import Count, Sum, Q, F
    from django.utils import timezone
    from intelligence.models import QuestionRank, Tag

    today = datetime.date.today()
    user = request.user
    
    # 1. Stats Calculation (Python-side for safety/compatibility)
    # Fetch all relevant fields for Question items
    q_items = TimelineItem.objects.filter(
        target__user=user, type='Question', question__isnull=False
    ).values('target_id', 'question_id', 'question__rank__points')
    
    # Process Unique Answers
    # Set of unique (target_id, question_id) tuples
    unique_pairs = set()
    total_points = 0
    
    for item in q_items:
        pair = (item['target_id'], item['question_id'])
        if pair not in unique_pairs:
            unique_pairs.add(pair)
            # Add points for this unique answer
            points = item['question__rank__points']
            if points:
                total_points += points

    qa_count = len(unique_pairs)
    total_logs = TimelineItem.objects.filter(target__user=user).count()

    # 2. Anniversaries (Range: Today to Today+7 for notification bar)
    start_date = today
    end_date = today + datetime.timedelta(days=7)
    
    upcoming_anniv_list = []
    
    # Helper to check range
    date_curs = start_date
    while date_curs <= end_date:
        # Birthdays
        b_targets = Target.objects.filter(
            user=user, birth_month=date_curs.month, birth_day=date_curs.day
        )
        for t in b_targets:
            upcoming_anniv_list.append({
                'date': date_curs,
                'name': '誕生日',
                'target': t,
                'is_past': date_curs < today
            })
            
        # Custom
        c_annivs = CustomAnniversary.objects.filter(
            target__user=user, date__month=date_curs.month, date__day=date_curs.day
        ).select_related('target')
        for ca in c_annivs:
            upcoming_anniv_list.append({
                'date': date_curs,
                'name': ca.label,
                'target': ca.target,
                'is_past': date_curs < today
            })
            
        date_curs += datetime.timedelta(days=1)
        
    upcoming_anniv_list.sort(key=lambda x: x['date']) # Sort by date

    # 3. Filters Support (Groups, Tags)
    groups = TargetGroup.objects.filter(user=user)
    top_tags = Tag.objects.filter(timelineitem__target__user=user).annotate(c=Count('timelineitem')).order_by('-c')[:20]

    context = {
        'stats': {
            'qa_count': qa_count,
            'total_points': total_points,
            'total_logs': total_logs
        },
        'upcoming_anniversaries': upcoming_anniv_list,
        'groups': groups,
        'tags': top_tags,
    }
    
    if getattr(request, 'is_mobile', False):
        return render(request, 'mobile/home_mobile.html', context)
        
    return render(request, 'dashboard.html', context)

@login_required
def target_list(request):
    sort_by = request.GET.get('sort', 'last_contact')
    targets = Target.objects.filter(user=request.user).prefetch_related('groups')

    if sort_by == 'group':
        targets = targets.order_by('groups__name', 'nickname')
    elif sort_by == 'anniversary':
        # Sort by birth month and day (Upcoming birthdays/anniversaries rough approx)
        # Note: This simply sorts Jan -> Dec. For strict "Upcoming", python sorting is often easier for small lists.
        targets = targets.order_by('birth_month', 'birth_day', 'nickname')
    else: # last_contact
        from django.db.models import F
        targets = targets.order_by(F('last_contact').desc(nulls_last=True), 'nickname')

    # Template Selection
    if request.htmx:
        template_name = '_target_list_partial.html'
    elif getattr(request, 'is_mobile', False):
        template_name = 'mobile/target_list_mobile.html'
    else:
        template_name = 'target_list.html'

    return render(request, template_name, {'targets': targets, 'current_sort': sort_by})

# FormSet for Anniversaries
AnniversaryFormSet = inlineformset_factory(
    Target, CustomAnniversary, form=CustomAnniversaryForm,
    extra=0, can_delete=True
)

class TargetDetailView(LoginRequiredMixin, MobileTemplateMixin, DetailView):
    model = Target
    template_name = 'target_detail.html'
    mobile_template_name = 'mobile/target_detail_mobile.html'
    context_object_name = 'target'

    def get_object(self):
        # Allow fetching by ?target_id= or standard PK if provided (though URL will likely be clean)
        pk = self.request.GET.get('target_id')
        if not pk:
            # Fallback to URL kwarg if present
            return super().get_object()
        return get_object_or_404(Target, pk=pk, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target = self.object
        
        # 1. Stats
        # Total Log Count
        context['log_count'] = TimelineItem.objects.filter(target=target).count()
        # Contact Count
        context['contact_count'] = TimelineItem.objects.filter(target=target, contact_made=True).count()
        
        # 2. Q&A
        from intelligence.models import Question, QuestionCategory
        # Get all categories
        categories = QuestionCategory.objects.filter(user=self.request.user)
        qa_data = []
        
        for cat in categories:
            questions = Question.objects.filter(category=cat).order_by('order', 'title')
            cat_data = {
                'category': cat,
                'questions': [],
                'answered_count': 0,
                'total_count': questions.count()
            }
            
            for q in questions:
                # Find latest answer
                # Optimized: could use Subquery/Prefetch, but loop is okay for low volume
                answer_item = TimelineItem.objects.filter(
                    target=target, 
                    type='Question', 
                    question=q
                ).order_by('-date', '-created_at').first()
                
                q_info = {
                    'question': q,
                    'answer': answer_item.content if answer_item else None, # key is 'content' in model
                    'answer_date': answer_item.date if answer_item else None,
                    'is_answered': bool(answer_item)
                }
                if answer_item: cat_data['answered_count'] += 1
                cat_data['questions'].append(q_info)
                
            qa_data.append(cat_data)
            
        context['qa_data'] = qa_data
        
        # 3. Events / Timeline (Recent 20)
        context['events'] = TimelineItem.objects.filter(
            target=target
        ).exclude(type='Question').order_by('-date', '-created_at')[:20]
        
        # 4. Tags
        from django.db.models import Count
        from intelligence.models import Tag
        context['tags'] = Tag.objects.filter(
            timelineitem__target=target
        ).annotate(count=Count('timelineitem')).order_by('-count')
        
        return context

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
    template_name = 'target_confirm_delete.html' 
    
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

    def get_daily_target_ids(self, user, date):
        from intelligence.models import Target, DailyTargetState, CustomAnniversary, TargetGroup
        import datetime
        from django.db.models import Q

        weekday = date.weekday()
        weekday_map = ['is_mon', 'is_tue', 'is_wed', 'is_thu', 'is_fri', 'is_sat', 'is_sun']
        current_weekday_field = weekday_map[weekday]
        
        # 1. Base Logic (Groups)
        # Filter groups that have the current weekday set to True
        base_targets = Target.objects.filter(
            user=user,
            groups__in=TargetGroup.objects.filter(**{current_weekday_field: True})
        ).distinct()
        
        # 2. Anniversary Logic
        anniv_ids = set()
        
        # Birthday (Today)
        birthday_targets = Target.objects.filter(
            user=user,
            birth_month=date.month,
            birth_day=date.day
        )
        anniv_ids.update(birthday_targets.values_list('id', flat=True))
        
        # Custom Anniv (Today)
        custom_annivs = CustomAnniversary.objects.filter(
            target__user=user,
            date__month=date.month,
            date__day=date.day
        )
        anniv_ids.update(custom_annivs.values_list('target_id', flat=True))
        
        # 3. Manual State
        daily_states = DailyTargetState.objects.filter(target__user=user, date=date)
        manual_add_ids = set(daily_states.filter(is_manual_add=True).values_list('target_id', flat=True))
        hidden_ids = set(daily_states.filter(is_hidden=True).values_list('target_id', flat=True))
        
        # Combine
        final_ids = set(base_targets.values_list('id', flat=True))
        final_ids.update(anniv_ids)
        final_ids.update(manual_add_ids)
        final_ids = final_ids - hidden_ids
        
        return final_ids

    def get(self, request, *args, **kwargs):
        import datetime
        from django.db.models import Q
        
        is_mobile = getattr(request, 'is_mobile', False)
        target_id_param = request.GET.get('target_id')
        
        # 1. Date Handling
        date_str = request.GET.get('date')
        if date_str:
            try:
                current_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                current_date = datetime.date.today()
        else:
            current_date = datetime.date.today()

        # [MOBILE OPTIMIZATION] Timeline View - Short Circuit
        if is_mobile and target_id_param:
            target = get_object_or_404(Target, pk=target_id_param, user=request.user)
            
            # Auto-Add Logic (Ensure it's marked as active for today)
            state, _ = DailyTargetState.objects.get_or_create(
                target=target, date=current_date,
                defaults={'is_manual_add': True, 'is_hidden': False}
            )
            if not state.is_manual_add and state.is_hidden:
                    state.is_hidden = False
                    state.save()
            elif not state.is_manual_add:
                    state.is_manual_add = True
                    state.save()
            
            # [SSR] Fetch Timeline Items for rendering
            # Pass ALL items for the target, or filtered?
            # User wants "Timeline items content". Usually full history or recent.
            # Let's pass all for now, ordered by date desc (or match render logic).
            # renderJS does sort. Let's pass objects.
            # [SSR] Fetch and Group Timeline Items
            raw_items = TimelineItem.objects.filter(target=target).prefetch_related('images').order_by('date', 'created_at')
            
            grouped_timeline = []
            current_group = None
            for item in raw_items:
                date_str = item.date.strftime('%Y-%m-%d')
                if current_group and current_group['date_str'] == date_str:
                    current_group['items'].append(item)
                    if item.contact_made: current_group['has_contact'] = True
                else:
                    if current_group: grouped_timeline.append(current_group)
                    current_group = {
                        'date': item.date,
                        'date_str': date_str,
                        'items': [item],
                        'has_contact': item.contact_made
                    }
            if current_group: grouped_timeline.append(current_group)

            timeline_items = grouped_timeline # Pass as 'timeline_items' but structure changed
 
            
            return render(request, 'mobile/intelligence_timeline_mobile.html', {
                'target': target,
                'today_date': current_date, # This is actually specific date from param if set
                'timeline_items': timeline_items,
            })

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
        
        # Get IDs
        final_ids = self.get_daily_target_ids(request.user, current_date)
        
        # Fetch Objects & Annotate for UI
        from django.db.models import Max
        targets = Target.objects.filter(id__in=final_ids).prefetch_related('groups').annotate(
            real_last_contact=Max('timelineitem__date', filter=Q(timelineitem__contact_made=True))
        ).order_by('nickname')
        
        target_list = []
        
        # Helper for Anniversary
        def get_next_date(month, day, reference_date):
            try:
                this_year = datetime.date(reference_date.year, month, day)
            except ValueError: # Leap year case
                this_year = datetime.date(reference_date.year, 3, 1)
            
            if this_year >= reference_date:
                return this_year
            
            try:
                next_year = datetime.date(reference_date.year + 1, month, day)
            except ValueError:
                next_year = datetime.date(reference_date.year + 1, 3, 1)
            return next_year

        for t in targets:
            has_entry = TimelineItem.objects.filter(target=t, date=current_date).exists()
            log_count = TimelineItem.objects.filter(target=t, date=current_date).count()
            age = t.age

            # 1. Birthday
            next_bday = None
            if t.birth_month and t.birth_day:
                next_bday = get_next_date(t.birth_month, t.birth_day, current_date)
            
            # 2. Custom Anniversaries
            # We need to fetch ALL custom anniversaries for this target to find the next one
            # Optimization: Fetch all custom annivs for displayed targets in bulk outside loop would be better, 
            # but for now inside loop is safer logic-wise, though slower. 
            # Given list size is usually small (~5-20), it's acceptable.
            # actually better to fetch related outside.
            # Use pre-fetched custom annivs?
            
            # Simplified: Just fetch here for correctness first.
            t_custom_annivs = CustomAnniversary.objects.filter(target=t)
            next_custom = None
            next_custom_label = ""
            
            for ca in t_custom_annivs:
                nd = get_next_date(ca.date.month, ca.date.day, current_date)
                if next_custom is None or nd < next_custom:
                    next_custom = nd
                    next_custom_label = ca.label
            
            # Compare Birthday vs Custom
            final_anniv_date = None
            final_anniv_label = ""
            final_anniv_type = "" # 'birthday' or 'custom'
            
            if next_bday and next_custom:
                if next_bday <= next_custom:
                    final_anniv_date = next_bday
                    final_anniv_label = "誕生日"
                else:
                    final_anniv_date = next_custom
                    final_anniv_label = next_custom_label
                    final_anniv_type = 'custom'
            elif next_bday:
                final_anniv_date = next_bday
                final_anniv_label = "誕生日"
                final_anniv_type = 'birthday'
            elif next_custom:
                final_anniv_date = next_custom
                final_anniv_label = next_custom_label
                final_anniv_type = 'custom'
            
            anniv_display = None
            if final_anniv_date:
                days_until = (final_anniv_date - current_date).days
                color_class = "text-text-sub" # Default gray
                if days_until == 0:
                    color_class = "text-accent-red font-bold"
                elif days_until <= 10:
                    color_class = "text-yellow-500"
                
                icon = "fa-birthday-cake" if final_anniv_type == 'birthday' else "fa-medal" # generic icon
                
                anniv_display = {
                    'label': final_anniv_label,
                    'date_str': final_anniv_date.strftime('%Y/%m/%d'),
                    'color_class': color_class,
                    'icon': icon,
                    'is_today': days_until == 0
                }

            target_list.append({
                'obj': t,
                'has_entry': has_entry,
                'log_count': log_count,
                'age': age,
                'last_contact_date': t.real_last_contact,
                'nearest_anniversary': anniv_display
            })

        # Questions & Tags
        from intelligence.models import Question, Tag, QuestionCategory
        questions = Question.objects.filter(
            Q(is_shared=True) | Q(user=request.user)
        ).order_by('category', 'order', 'title')
        
        # Get IDs of categories used by these questions
        category_ids = questions.values_list('category_id', flat=True).distinct()

        # Fetch Categories (User's OR Used by Questions)
        categories = QuestionCategory.objects.filter(
            Q(user=request.user) | Q(id__in=category_ids)
        ).order_by('id').distinct()

        from django.db.models import Count
        # Filter tags used by THIS user's targets
        top_tags = Tag.objects.filter(
            timelineitem__target__user=request.user
        ).annotate(count=Count('timelineitem')).order_by('-count')[:10]

        context = {
            'todays_targets': target_list,
            'questions': questions,
            'categories': categories, # Add categories to context
            'tags': top_tags,
            'today_date': current_date,
            'weekday_jp': ['月','火','水','木','金','土','日'][weekday]
        }
        if is_mobile:
            return render(request, 'mobile/intelligence_select_mobile.html', context)
        
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        import datetime
        import re
        from django.utils import timezone
        from intelligence.models import TimelineImage
        
        try:
            # 1. Parse Data (Support JSON & Multipart)
            images = []
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
                images = request.FILES.getlist('images')

            # Action: 'create' (default), 'update' or 'delete'
            action = data.get('action', 'create')
            
            if action == 'delete':
                item_id = data.get('item_id')
                if not item_id: return JsonResponse({'success': False, 'error': 'Item ID required'})
                item = get_object_or_404(TimelineItem, pk=item_id, target__user=request.user)
                target = item.target
                date = item.date
                item.delete()
                
                # Check if any entry remains for this date
                has_entry_today = TimelineItem.objects.filter(target=target, date=date).exists()
                return JsonResponse({'success': True, 'has_entry_today': has_entry_today, 'target_id': target.id})

            elif action == 'refresh_list':
                # Remove (Hide) displayed targets with 0 logs from the selection list for this date
                date_str = data.get('date')
                try:
                    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'error': 'Invalid date'})

                displayed_ids = self.get_daily_target_ids(request.user, date)
                
                # Check logs
                hidden_count = 0
                for tid in displayed_ids:
                    has_log = TimelineItem.objects.filter(target_id=tid, date=date).exists()
                    if not has_log:
                        DailyTargetState.objects.update_or_create(
                            target_id=tid,
                            date=date,
                            defaults={'is_hidden': True}
                        )
                        hidden_count += 1
                
                return JsonResponse({'success': True, 'hidden_count': hidden_count})

            elif action == 'manual_add':
                target_id = data.get('target_id')
                date_str = data.get('date')
                try:
                    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'error': 'Invalid date'})

                if not target_id: return JsonResponse({'success': False, 'error': 'Target ID required'})
                
                DailyTargetState.objects.update_or_create(
                    target_id=target_id,
                    date=date,
                    defaults={'is_manual_add': True, 'is_hidden': False}
                )
                return JsonResponse({'success': True})

            elif action == 'get_candidates':
                # Return JSON list of targets NOT in current selection, sorted by last contact asc
                date_str = data.get('date')
                try:
                    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'error': 'Invalid date'})
                
                current_ids = self.get_daily_target_ids(request.user, date)
                
                from django.db.models import Max, Q
                candidates = Target.objects.filter(user=request.user).exclude(id__in=current_ids).annotate(
                    real_last_contact=Max('timelineitem__date', filter=Q(timelineitem__contact_made=True))
                ).order_by('real_last_contact', 'nickname') # Nulls first (never contacted)? or last? Django defaults. ASC means old dates first.
                
                # Manual serialization for simple list
                candidate_list = []
                for c in candidates:
                    candidate_list.append({
                        'id': c.id,
                        'nickname': c.nickname,
                        'name_kanji': f"{c.last_name} {c.first_name}".strip(),
                        'name_kana': f"{c.last_name_kana} {c.first_name_kana}".strip(),
                        'avatar_url': c.avatar.url if c.avatar else None,
                        'last_contact': c.real_last_contact.strftime('%Y/%m/%d') if c.real_last_contact else 'No Contact'
                    })
                
                return JsonResponse({'success': True, 'candidates': candidate_list})

            elif action == 'update':
                item_id = data.get('item_id')
                item = get_object_or_404(TimelineItem, pk=item_id, target__user=request.user)
                
                # Update fields
                if 'description' in data: item.content = data.get('description')
                content = item.content # for tag processing
                
                if 'date' in data and data['date']:
                    try:
                        item.date = datetime.datetime.strptime(data['date'], '%Y-%m-%d').date()
                    except ValueError: pass
                    
                if 'contact_made' in data: item.contact_made = data.get('contact_made') == 'true' if isinstance(data.get('contact_made'), str) else data.get('contact_made', False)
                
                # Bump created_at to now? Or just save.
                # item.created_at = timezone.now() # User might not want timestamp bump on edit.
                
                item.save()
                item.tags.clear()
                # Tag logic continues below if shared?
                # Actually tag logic is usually separate.
                # Returning success for update here to keep it simple as tags are separate?
                # The original code likely fell through to tag processing.
                # Let's check if there is tag processing after this block.
                # Assuming tag processing is below line 750 (end of create).
                # But 'item' needs to be defined.
                pass 

            else: # Create
                target_id = data.get('target_id')
                date_str = data.get('date')
                frontend_type = data.get('event_type', 'NOTE') 
                content = data.get('description', '')
                if not content: content = data.get('content', '')
                if content in ['null', 'undefined', 'None']: content = ''
                # Handle boolean string from FormData
                contact_made_raw = data.get('contact_made')
                contact_made = contact_made_raw == 'true' if isinstance(contact_made_raw, str) else bool(contact_made_raw)
                
                if not target_id: return JsonResponse({'success': False, 'error': 'No target specified'})
                target = get_object_or_404(Target, pk=target_id, user=request.user)
                
                if date_str:
                    try:
                        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError: date_obj = datetime.date.today()
                else: date_obj = datetime.date.today()
                
                if frontend_type == 'QUESTION': item_type = 'Question'
                else: item_type = 'Event' if not images else 'Note' # Default note if images only
                    
                item = TimelineItem(
                    target=target,
                    date=date_obj,
                    contact_made=contact_made,
                    type=item_type,
                    content=content
                )
                
                if frontend_type == 'QUESTION':
                    q_id = data.get('question_id')
                    if q_id:
                        from intelligence.models import Question
                        try:
                            q = Question.objects.get(pk=q_id)
                            item.question = q
                            item.question_text = q.title
                            item.question_category = q.category.name if q.category else ''
                        except Question.DoesNotExist: pass
                    item.question_answer = content
                    item.content = content 
                
                item.save()

                # Handle Images (Max 4)
                if images:
                    for img in images[:4]:
                        TimelineImage.objects.create(item=item, image=img)
            
            # --- Common Logic for Create & Update: Tags ---
            tag_ids = data.get('tags', []) # List? FormData uses tags list?
            # FormData sending array: usually same key multiple times data.getlist('tags')?
            # Existing code: `tag_ids = data.get('tags', [])` implies JSON list.
            # If FormData, we might need request.POST.getlist('tags')?
            # Let's support both.
            if hasattr(request.POST, 'getlist') and 'tags' in request.POST:
                 tag_ids = request.POST.getlist('tags')
            from intelligence.models import Tag
            # 2. Extract Hashtags from Content (Legacy/Text-based)
            hashtags = re.findall(r'#(\w+)', content)
            for tag_name in hashtags:
                tag, _ = Tag.objects.get_or_create(user=request.user, name=tag_name)
                item.tags.add(tag)

            # 3. Handle Explicit Tag IDs (New UI)
            explicit_tags = data.get('tags', []) # Expecting list of IDs
            if explicit_tags:
                 # If explicit_tags is string (from FormData), split/parse
                 if isinstance(explicit_tags, str):
                     try:
                         explicit_tags = json.loads(explicit_tags)
                     except:
                         explicit_tags = [] # Or split by comma if comma-separated
                 
                 if isinstance(explicit_tags, list):
                     for tag_id in explicit_tags:
                         try:
                             tag = Tag.objects.get(id=tag_id, user=request.user)
                             item.tags.add(tag)
                         except Tag.DoesNotExist:
                             pass
            
            if item.contact_made:
                item.target.last_contact = timezone.now()
                item.target.save()

            # Check has_entry_today
            has_entry_today = TimelineItem.objects.filter(target=item.target, date=item.date).exists()

            return JsonResponse({'success': True, 'has_entry_today': has_entry_today, 'target_id': item.target.id})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
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

class QuestionListView(LoginRequiredMixin, MobileTemplateMixin, ListView):
    model = Question
    template_name = 'question_list.html'
    mobile_template_name = 'mobile/question_list_mobile.html'
    context_object_name = 'questions'

    def get_template_names(self):
        # HTMX: Return partial template for smooth updates
        if self.request.htmx:
            return ['_question_list_partial.html']
        return [self.template_name]

    def get_queryset(self):
        from django.db.models import Q, Count
        
        # Base Query: User's Own OR Shared Questions
        qs = Question.objects.filter(
            Q(user=self.request.user) | Q(is_shared=True)
        ).annotate(
            answer_count=Count('timelineitem')
        ).order_by('order', 'created_at')
        
        # Filters
        cat_id = self.request.GET.get('category')
        if cat_id:
            qs = qs.filter(category_id=cat_id)
            
        rank_id = self.request.GET.get('rank')
        if rank_id:
            qs = qs.filter(rank_id=rank_id)
            
        # shared param: '1' -> Only Shared, '0' -> Only Individual
        is_shared = self.request.GET.get('shared')
        if is_shared == '1':
            qs = qs.filter(is_shared=True)
        elif is_shared == '0':
            qs = qs.filter(is_shared=False)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = QuestionCategory.objects.filter(user=self.request.user)
        context['ranks'] = QuestionRank.objects.filter(user=self.request.user)
        # Add all targets for the LOG modal
        from intelligence.models import Target
        context['all_targets'] = Target.objects.filter(user=self.request.user).order_by('nickname')
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
    template_name = 'question_confirm_delete.html' 
    
    def get_queryset(self):
        return Question.objects.filter(user=self.request.user)

class QuestionDetailView(LoginRequiredMixin, MobileTemplateMixin, View):
    template_name = 'question_detail.html'
    mobile_template_name = 'mobile/question_detail_mobile.html'
    
    def get(self, request, pk=None):
        from django.db.models import Q, Count, Max, Prefetch
        import json
        
        # Get question if pk provided or from query param
        question_id = pk or request.GET.get('question_id')
        question = None
        answer_data = []
        
        if question_id:
            try:
                question = Question.objects.filter(
                    Q(user=request.user) | Q(is_shared=True)
                ).prefetch_related('category', 'rank').get(pk=question_id)
                
                # Get all answers for this question
                answers_qs = TimelineItem.objects.filter(
                    question=question,
                    target__user=request.user
                ).select_related('target').prefetch_related('tags').order_by('target', '-date')
                
                # Apply filters
                group_id = request.GET.get('group')
                if group_id:
                    answers_qs = answers_qs.filter(target__groups__id=group_id)
                
                # Get latest answer per target with count
                from collections import defaultdict
                target_answers = defaultdict(list)
                for answer in answers_qs:
                    target_answers[answer.target].append(answer)
                
                # Build answer data
                for target, answers in target_answers.items():
                    answer_data.append({
                        'target': target,
                        'latest_answer': answers[0],
                        'all_answers': answers,
                        'answer_count': len(answers)
                    })
                
                # Apply sorting
                sort_by = request.GET.get('sort', 'date')
                if sort_by == 'date':
                    answer_data.sort(key=lambda x: x['latest_answer'].date, reverse=True)
                elif sort_by == 'choice':
                    answer_data.sort(key=lambda x: x['latest_answer'].question_answer or '')
                elif sort_by == 'count':
                    answer_data.sort(key=lambda x: x['answer_count'], reverse=True)
            except Question.DoesNotExist:
                pass
        
        # Get all questions for dropdown with category info
        questions = Question.objects.filter(
            Q(user=request.user) | Q(is_shared=True)
        ).select_related('category').order_by('category', 'order', 'title')
        
        # Prepare questions data for JavaScript
        questions_json = json.dumps([{
            'id': q.id,
            'title': q.title,
            'category_id': q.category.id if q.category else None
        } for q in questions])
        
        # Get categories for filter
        categories = QuestionCategory.objects.filter(user=request.user)
        
        # Get groups for filter
        from intelligence.models import TargetGroup
        groups = TargetGroup.objects.filter(user=request.user)
        
        context = {
            'question': question,
            'answer_data': answer_data,
            'questions': questions_json,
            'categories': categories,
            'groups': groups,
            'total_answers': sum(x['answer_count'] for x in answer_data) if answer_data else 0,
            'total_targets': len(answer_data)
        }
        
        return render(request, self.template_name, context)


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


class RankCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get('name')
            points = data.get('points', 0)
            if not name: return JsonResponse({'success': False, 'error': 'Name required'})
            
            rank = QuestionRank.objects.create(user=request.user, name=name, points=points)
            return JsonResponse({'success': True, 'id': rank.id, 'name': rank.name})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# --- TIMELINE API ---
class TimelineListAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            target_id = request.GET.get('target_id')
            
            # Base Query
            if target_id:
                try:
                    target = Target.objects.get(pk=target_id, user=request.user)
                    queryset = TimelineItem.objects.filter(target=target).select_related('question')
                except Target.DoesNotExist:
                     return JsonResponse({'success': False, 'error': 'Target not found'}, status=404)
            else:
                # Global Feed
                queryset = TimelineItem.objects.filter(target__user=request.user).select_related('target', 'question')

            # Filtering
            import datetime
            from django.db.models import Q
            
            # Group Filter
            group_id = request.GET.get('group_id')
            if group_id:
                queryset = queryset.filter(target__groups__id=group_id)

            # Type
            event_type = request.GET.get('type') # 'EVENT' or 'QUESTION'
            if event_type:
                if event_type == 'EVENT':
                    queryset = queryset.filter(Q(type='Event') | Q(type='Note'))
                elif event_type == 'QUESTION':
                    queryset = queryset.filter(type='Question')

            # Search Query
            query = request.GET.get('search')
            if query:
                queryset = queryset.filter(
                    Q(content__icontains=query) | 
                    Q(question__title__icontains=query)
                )
            
            # Encanto Filter
            contact_only = request.GET.get('contact_only') == 'true'
            if contact_only:
                queryset = queryset.filter(contact_made=True)

            # Tags (list of IDs)
            tags = request.GET.getlist('tags[]')
            if tags:
                queryset = queryset.filter(tags__id__in=tags).distinct()

            # Pagination (Cursor) - simple date based for now
            # Note: For Global Feed, simple date based cursor on 'date' field might be ambiguous if many logs same date.
            # But 'created_at' is safer. 
            # Current frontend uses 'date' for sorting? 
            # User wants "Sort by Occurrence Date (Newest) AND Input Date (Newest) default".
            # Order By: `-date`, `-created_at`.
            
            before_timestamp = request.GET.get('before_timestamp') # Changed from before_date for precision
            if before_timestamp:
                queryset = queryset.filter(created_at__lt=before_timestamp)
                
            # Ordering: Date Desc, Created At Desc
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
                    'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
                    'type': item.type, 
                    'question_id': item.question.id if item.question else None,
                    'description': item.content, # Model has 'content', mapped to 'description' for frontend
                    # Safety checks for question relation
                    'question_title': (item.question.title if item.question else item.question_text) or '',
                    'question_category': (item.question.category.name if item.question and item.question.category else item.question_category) or '',
                    'contact_made': item.contact_made,
                    'tags': [{'id': t.id, 'name': t.name} for t in item.tags.all()],
                    'target': {
                        'id': item.target.id,
                        'nickname': item.target.nickname,
                        'avatar': item.target.avatar.url if item.target.avatar else None,
                        'first_name': item.target.first_name,
                        'last_name': item.target.last_name
                    }
                })
                
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class TagListAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            from django.db.models import Count, Q
            from intelligence.models import Tag
            
            target_id = request.GET.get('target_id')
            
            # 1. All Tags (Global frequency)
            all_tags_qs = Tag.objects.filter(user=request.user).annotate(
                count=Count('timelineitem')
            ).order_by('-count')
            
            all_tags_data = [{'id': t.id, 'name': t.name, 'count': t.count} for t in all_tags_qs]
            
            # 2. Target Specific Tags (Top 5)
            target_tags_data = []
            if target_id:
                target_tags = Tag.objects.filter(
                    user=request.user,
                    timelineitem__target_id=target_id
                ).annotate(
                    target_count=Count('timelineitem', filter=Q(timelineitem__target_id=target_id))
                ).order_by('-target_count')[:5]
                
                target_tags_data = [{'id': t.id, 'name': t.name, 'count': t.target_count} for t in target_tags]

            return JsonResponse({
                'success': True, 
                'tags': all_tags_data, # Legacy support if needed, or main list
                'all_tags': all_tags_data,
                'target_tags': target_tags_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def post(self, request, *args, **kwargs):
        try:
             import json
             from intelligence.models import Tag
             
             if request.content_type == 'application/json':
                 data = json.loads(request.body)
             else:
                 data = request.POST
             
             name = data.get('name', '').strip()
             if not name:
                 return JsonResponse({'success': False, 'error': 'Tag name required'})
             
             if name.startswith('#'): name = name[1:]
             
             tag, created = Tag.objects.get_or_create(user=request.user, name=name)
             
             return JsonResponse({
                 'success': True,
                 'tag': {'id': tag.id, 'name': tag.name, 'count': 0}
             })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class QuestionListAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            from intelligence.models import Question, QuestionCategory, TimelineItem
            from django.db.models import Count, Q
            
            target_id = request.GET.get('target_id')
            if not target_id:
                return JsonResponse({'success': False, 'error': 'Target ID required'})
            
            # Fetch all categories
            # Including 'Uncategorized'? Maybe handling null category questions separately or generic
            # Fetch Questions first to know which categories are needed
            questions_qs = Question.objects.filter(
                Q(is_shared=True) | Q(user=request.user)
            ).select_related('category', 'rank').order_by('category__id', 'order', 'title')
            
            # Get IDs of categories used by these questions
            category_ids = questions_qs.values_list('category_id', flat=True).distinct()

            # Fetch Categories (User's OR Used by Questions)
            categories = QuestionCategory.objects.filter(
                Q(user=request.user) | Q(id__in=category_ids)
            ).order_by('id').distinct()
            
            # We can't easily annotate a filtered count inside a related manager query for serialization 
            # without complex Prefetch or annotation.
            # Simpler approach: Fetch log counts separately or use subquery.
            
            # Use annotation with Q filter on TimelineItem
            # But Question -> TimelineItem (reverse relation name defaults to 'timelineitem_set' or similar?)
            # TimelineItem has 'question' FK. So 'timelineitem'.
            
            questions_qs = questions_qs.annotate(
                answer_count=Count('timelineitem_set', filter=Q(timelineitem_set__target_id=target_id))
            )

            # Structure by Category
            categorized_data = {}
            # Initialize with categories
            for cat in categories:
                categorized_data[cat.id] = {
                    'id': cat.id,
                    'name': cat.name,
                    'questions': []
                }
            # Special bucket for 'No Category'
            categorized_data['none'] = {'id': 'none', 'name': 'Uncategorized', 'questions': []}

            for q in questions_qs:
                q_data = {
                    'id': q.id,
                    'title': q.title,
                    'rank': q.rank.name if q.rank else '',
                    'answer_type': q.answer_type,
                    'choices': q.choices,
                    'description': q.description,
                    'example': q.example,
                    'count': q.answer_count
                }
                
                if q.category:
                    if q.category.id in categorized_data:
                         categorized_data[q.category.id]['questions'].append(q_data)
                    else:
                         categorized_data['none']['questions'].append(q_data) # Fallback
                else:
                    categorized_data['none']['questions'].append(q_data)
            
            # Convert to list, removing empty if desired? Or keep all.
            result_list = []
            # Order: Categories then None
            for cat in categories:
                if categorized_data[cat.id]['questions']:
                    result_list.append(categorized_data[cat.id])
            if categorized_data['none']['questions']:
                result_list.append(categorized_data['none'])
                
            return JsonResponse({'success': True, 'categories': result_list})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
