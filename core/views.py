from django.shortcuts import render, redirect, get_object_or_404



from django.views.generic import CreateView, UpdateView, View, DeleteView, DetailView, TemplateView



from core.mixins import MobileTemplateMixin



from django.urls import reverse_lazy



from django.db import transaction



from django.http import JsonResponse, HttpResponse



from django.forms import inlineformset_factory



from django.contrib.auth.decorators import login_required



from django.contrib.auth.mixins import LoginRequiredMixin



from django.db import models



from django.db.models import Q







from intelligence.models import Target, TimelineItem, CustomAnniversary, TargetGroup, DailyTargetState, Question, QuestionCategory, QuestionRank



from intelligence.forms import TargetForm, CustomAnniversaryForm, TargetGroupForm, QuestionImportForm



import io



import json



import csv



import urllib.parse







@login_required



def dashboard(request):



    import datetime



    from django.db.models import Count, Sum, Q, F



    from django.utils import timezone



    from intelligence.models import QuestionRank, Tag







    today = datetime.date.today()



    user = request.user



    



    # [MODIFIED] 1. Random Question for "Today's Topic"



    random_question = Question.objects.filter(



        Q(user=user) | Q(is_shared=True) | Q(user__role='MASTER')



    ).distinct().order_by('?').first()







    # [MODIFIED] 2. Latest Logs (Events) - Limit 10



    latest_logs = TimelineItem.objects.filter(



        target__user=user



    ).exclude(type='Question').select_related('target').prefetch_related('images').order_by('-date', '-created_at')[:10]







    # [MODIFIED] 3. Latest Answers - Limit 10



    latest_answers = TimelineItem.objects.filter(



        target__user=user, type='Question'



    ).select_related('target', 'question').order_by('-date', '-created_at')[:10]







    # 4. Anniversaries (Range: Today to Today+14)



    start_date = today



    end_date = today + datetime.timedelta(days=14)



    



    upcoming_anniv_list = []



    



    date_curs = start_date



    while date_curs <= end_date:



        # Birthdays



        b_targets = Target.objects.filter(



            user=user, birth_month=date_curs.month, birth_day=date_curs.day



        )



        for t in b_targets:



            days_left = (date_curs - today).days



            upcoming_anniv_list.append({



                'date': date_curs,



                'name': 'Birthday',



                'target': t,



                'days_left': days_left,



                'is_today': days_left == 0



            })



            



        # Custom



        c_annivs = CustomAnniversary.objects.filter(



            target__user=user, date__month=date_curs.month, date__day=date_curs.day



        ).select_related('target')



        for ca in c_annivs:



            days_left = (date_curs - today).days



            upcoming_anniv_list.append({



                'date': date_curs,



                'name': ca.label,



                'target': ca.target,



                'days_left': days_left,



                'is_today': days_left == 0



            })



            



        date_curs += datetime.timedelta(days=1)



        



    upcoming_anniv_list.sort(key=lambda x: x['date'])







    # Filters Support (Groups, Tags)



    groups = TargetGroup.objects.filter(user=user)



    top_tags = Tag.objects.filter(



        timelineitem__target__user=user



    ).annotate(c=Count('timelineitem')).order_by('-c')[:20]







    context = {



        'random_question': random_question,



        'latest_logs': latest_logs,



        'latest_answers': latest_answers,



        'upcoming_anniversaries': upcoming_anniv_list,



        'groups': groups,



        'tags': top_tags,



    }



    



    if getattr(request, 'is_mobile', False):



        return render(request, 'mobile/home_mobile.html', context)



        



    return render(request, 'dashboard.html', context)







@login_required



@login_required



def target_list(request):



    from django.db.models import Count, Sum, Q, Subquery, OuterRef



    



    sort_by = request.GET.get('sort', 'last_contact')



    search_query = request.GET.get('q')



    group_filter = request.GET.get('group')



    



    # Base Query



    targets = Target.objects.filter(user=request.user).prefetch_related('groups')







    # Search Filter



    if search_query:



        targets = targets.filter(



            Q(nickname__icontains=search_query) |



            Q(first_name__icontains=search_query) |



            Q(last_name__icontains=search_query) |



            Q(first_name_kana__icontains=search_query) |



            Q(last_name_kana__icontains=search_query)



        )







    # Group Filter



    if group_filter:



        targets = targets.filter(groups__id=group_filter)







    # Annotations



    # Latest Message Subquery



    latest_msg = TimelineItem.objects.filter(



        target=OuterRef('pk')



    ).order_by('-date', '-created_at').values('content')[:1]







    targets = targets.annotate(



        total_points=Sum('timelineitem__question__rank__points', filter=Q(timelineitem__type='Question')),



        log_count=Count('timelineitem'),



        latest_msg_content=Subquery(latest_msg)



    )







    # Sorting



    if sort_by == 'group':



        targets = targets.order_by('groups__name', 'nickname')



    elif sort_by == 'anniversary':



        targets = targets.order_by('birth_month', 'birth_day', 'nickname')



    else: # last_contact



        from django.db.models import F



        targets = targets.order_by(F('last_contact').desc(nulls_last=True), 'nickname')







    # Get Groups for Filter UI



    groups = TargetGroup.objects.filter(user=request.user)







    # Template Selection



    if request.htmx:



        template_name = '_target_list_partial.html'



    elif getattr(request, 'is_mobile', False):



        template_name = 'mobile/target_list_mobile.html'



    else:



        template_name = 'target_list.html'







    return render(request, template_name, {



        'targets': targets, 



        'current_sort': sort_by,



        'groups': groups



    })







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



        



        # Calculate Age



        from datetime import date



        context['age'] = None



        if target.birth_year and target.birth_month and target.birth_day:



            today = date.today()



            context['age'] = today.year - target.birth_year - (



                (today.month, today.day) < (target.birth_month, target.birth_day)



            )



        



        # 1. Stats



        # Total Log Count



        context['log_count'] = TimelineItem.objects.filter(target=target).count()



        # Contact Count



        context['contact_count'] = TimelineItem.objects.filter(target=target, contact_made=True).count()



        



        # Calculate Total Points & Answers



        from django.db.models import Sum, Count, Q



        points_data = TimelineItem.objects.filter(



            target=target, type='Question'



        ).aggregate(



            total_points=Sum('question__rank__points'),



            total_answers=Count('question', distinct=True)



        )



        



        context['total_points'] = points_data['total_points'] or 0



        context['total_answers'] = points_data['total_answers'] or 0



        



        # 2. Q&A and Progress Calculation (Robust Question-First Approach)



        from intelligence.models import Question, QuestionCategory



        from accounts.models import CustomUser



        



        # 2.1 Fetch all visible questions once



        visible_qs = Question.objects.filter(



            Q(user=self.request.user) | Q(is_shared=True) | Q(user__role='MASTER')



        ).distinct().select_related('category', 'user').order_by('category__order', 'category__created_at', 'order', 'title')







        # 2.2 Prepare grouping



        from collections import defaultdict



        cat_to_qs = defaultdict(list)



        all_visible_cats = set()



        



        for q in visible_qs:



            cat_to_qs[q.category].append(q)



            if q.category:



                all_visible_cats.add(q.category)







        # 2.3 Mapping Title to Key for Base Profile



        base_title_map = {



            '職業': 'occupation', 'ご職業': 'occupation',



            '現在住所': 'address', '住所': 'address', 'お住まい': 'address',



            '家族構成': 'family_structure', '家族': 'family_structure',



            '趣味': 'hobbies', 'ご趣味': 'hobbies',



            '弱点': 'weakness', '苦手': 'weakness', '苦手なもの': 'weakness',



            '得意分野': 'skills', '得意': 'skills', '特技': 'skills'



        }



        base_answers = {



            'occupation': None, 'address': None, 'family_structure': None, 



            'hobbies': None, 'weakness': None, 'skills': None



        }



        answered_base_qs_count = 0







        # 2.4 Process Categories



        # Sort categories based on the same logic as QuestionListView: Order/CreatedAt



        sorted_cats = sorted(list(all_visible_cats), key=lambda x: (x.order, x.created_at))



        



        qa_data = [] # List of {category, questions: [{question, answer, is_answered}], answered_count, total_count, progress}



        total_q_count = 0



        total_answered_count = 0







        def process_q_list(category_obj, q_list):



            nonlocal total_q_count, total_answered_count, answered_base_qs_count



            q_count = len(q_list)



            data = {



                'category': category_obj,



                'questions': [],



                'answered_count': 0,



                'total_count': q_count,



                'progress': 0



            }



            total_q_count += q_count



            



            for q in q_list:



                answer_item = TimelineItem.objects.filter(



                    target=target, type='Question', question=q



                ).order_by('-date', '-created_at').first()



                



                is_answered = bool(answer_item)



                if is_answered:



                    data['answered_count'] += 1



                    total_answered_count += 1



                    



                    # [REQUIREMENT 2] BASE PROFILE REFLECTION



                    # Link by Title, strictly. If title matches, show it.



                    clean_title = q.title.strip()



                    if clean_title in base_title_map:



                        key = base_title_map[clean_title]



                        base_answers[key] = answer_item.content



                        answered_base_qs_count += 1



                



                data['questions'].append({



                    'question': q,



                    'answer': answer_item.content if is_answered else None,



                    'answer_date': answer_item.date if is_answered else None,



                    'is_answered': is_answered



                })



            



            if q_count > 0:



                data['progress'] = round((data['answered_count'] / q_count) * 100)



            return data







        # Add categorized groups



        for cat in sorted_cats:



            qa_data.append(process_q_list(cat, cat_to_qs[cat]))



        



        # Add uncategorized group (if exists)



        if None in cat_to_qs:



            qa_data.append(process_q_list(None, cat_to_qs[None]))



            



        # Sort category progress: Exclude "基本情報" for the category bar display



        context['qa_data_progress'] = [c for c in qa_data if c['category'] is None or c['category'].name != "基本情報"]



        context['qa_data'] = qa_data # Keep full list for the Q&A tab



        



        # Calculate Base Profile Progress (14 items: 3 Bio + 1 Anniversary + 10 Questions)



        answered_base_items = 0



        if target.birth_year:



            answered_base_items += 3 # Birthday, Age, Eto



        if target.customanniversary_set.exists():



            answered_base_items += 1



        answered_base_items += answered_base_qs_count



        



        context['base_answers'] = base_answers



        context['base_progress'] = min(round((answered_base_items / 14) * 100), 100)



        



        # Calculate HSL color for Base Progress (Red-to-Green: 0 to 120 deg)



        h = int(context['base_progress'] * 1.2)



        context['base_color'] = f"hsl({h}, 70%, 45%)"



        context['base_shadow'] = f"0 0 10px hsl({h}, 70%, 45%, 0.3)"



        



        # Global Progress (ensure counts for display)



        context['total_q_count'] = total_q_count



        context['total_answered_count'] = total_answered_count



        if total_q_count > 0:



            context['global_progress'] = round((total_answered_count / total_q_count) * 100)



        else:



            context['global_progress'] = 0







        # 3. Events / Event Log (Include Questions, Sort by Date DESC)



        # Fetch more than 20 to support basic log browsing



        context['events'] = TimelineItem.objects.filter(



            target=target



        ).exclude(type='Question').prefetch_related('images', 'tags').order_by('-date', '-created_at')[:100]



        



        # 4. Tags (Top tags for this specific target)



        from django.db.models import Count



        from intelligence.models import Tag



        # Get all tags used by THIS target's items, sorted by count



        context['all_tags'] = Tag.objects.filter(



            timelineitem__target=target



        ).annotate(use_count=Count('timelineitem')).order_by('-use_count')



        



        # 5. Anniversaries



        context['custom_anniversaries'] = target.customanniversary_set.all()



        



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



        from django.db.models import Count



        context['user_groups'] = TargetGroup.objects.filter(user=self.request.user).annotate(target_count=Count('target'))



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



        from django.db.models import Count



        context['user_groups'] = TargetGroup.objects.filter(user=self.request.user).annotate(target_count=Count('target'))



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



            



            # [SSR] Fetch and Group Timeline Items



            # Note: TimelineItem is shared if target is shared.



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







        # Questions & Tags (Owned OR Shared)



        questions = Question.objects.filter(



            Q(user=request.user) | Q(is_shared=True) | Q(user__role='MASTER')



        ).distinct().select_related('category', 'rank').order_by('category__order', 'category__created_at', 'order', 'title')



        



        # Get IDs of categories used by these questions



        category_ids = questions.values_list('category_id', flat=True).distinct()







        # Fetch Categories (User's OR Shared OR MASTER OR Used by Questions)



        categories = QuestionCategory.objects.filter(



            Q(user=request.user) | Q(is_shared=True) | Q(user__role='MASTER') | Q(id__in=category_ids)



        ).distinct().order_by('order', 'created_at')







        from django.db.models import Count



        from intelligence.models import Tag



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



                # Candidates: Owned OR MASTER-owned



                candidates = Target.objects.filter(



                    Q(user=request.user)



                ).exclude(id__in=current_ids).annotate(



                    real_last_contact=Max('timelineitem__date', filter=Q(timelineitem__contact_made=True))



                ).order_by('real_last_contact', 'nickname').distinct()



                



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



        # Delegate to Mixin for Mobile check



        return super().get_template_names()







    def get_queryset(self):



        from django.db.models import Q, Count



        



        # Base Query: My Own OR Shared OR MASTER Questions



        qs = Question.objects.filter(



            Q(user=self.request.user) | Q(is_shared=True) | Q(user__role='MASTER')



        ).distinct().annotate(



            answer_count=Count('timelineitem', filter=Q(timelineitem__target__user=self.request.user))



        ).order_by('category', 'order', 'created_at')



        



        # Search



        q = self.request.GET.get('q')



        if q:



            qs = qs.filter(



                Q(title__icontains=q) | 



                Q(description__icontains=q) | 



                Q(example__icontains=q)



            )







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



        user = self.request.user







        # 1. Fetch Categories properly sorted



        # User's Private Categories: Created At ASC



        private_cats = list(QuestionCategory.objects.filter(user=user, is_shared=False).exclude(user__role='MASTER').order_by('created_at'))



        # Shared Categories (Shared flag OR MASTER creation)



        shared_cats = list(QuestionCategory.objects.filter(Q(is_shared=True) | Q(user__role='MASTER')).distinct().order_by('order', 'created_at'))



        



        # Combined List: Private (Top) -> Shared (Bottom)



        all_cats = private_cats + shared_cats



        



        # 2. Bucket questions



        # self.object_list contains the filtered questions



        qs = self.object_list



        from collections import defaultdict



        q_dict = defaultdict(list)



        uncategorized = []



        



        for q in qs:



            if q.category_id:



                q_dict[q.category_id].append(q)



            else:



                uncategorized.append(q)



                



        # 3. Build structure



        structured_list = []



        for cat in all_cats:



            # We add a .questions_list attribute to the category object for the template



            cat.questions_list = q_dict[cat.id] 



            structured_list.append(cat)



            



        # 4. Uncategorized (Append to end if exists)



        if uncategorized:



            # Create a dummy object to mimic category interface



            class DummyCat:



                name = "Unclassified"



                id = None



                questions_list = uncategorized



                is_shared = False



                description = "" # Add description to avoid template errors



            structured_list.append(DummyCat())



            



        context['structured_categories'] = structured_list



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







    def dispatch(self, request, *args, **kwargs):



        if getattr(request.user, 'role', '') != 'MASTER':



             from django.core.exceptions import PermissionDenied



             raise PermissionDenied("Only MASTER can create questions.")



        return super().dispatch(request, *args, **kwargs)







    def form_valid(self, form):



        form.instance.user = self.request.user



        return super().form_valid(form)







class QuestionUpdateView(LoginRequiredMixin, UpdateView):



    model = Question



    form_class = QuestionForm



    template_name = 'question_form.html'



    success_url = reverse_lazy('question_list')







    def get_queryset(self):



        # Only MASTER can edit questions (Shared or MASTER-owned)



        if hasattr(self.request.user, 'role') and self.request.user.role == 'MASTER':



            return Question.objects.filter(Q(user=self.request.user) | Q(is_shared=True))



        return Question.objects.none() # Non-MASTER cannot edit any question







    def dispatch(self, request, *args, **kwargs):



        # Double check for shared edit permission



        if request.user.is_authenticated:



            try:



                obj = self.get_object() 



                if obj.is_shared and getattr(request.user, 'role', '') != 'MASTER':



                     from django.core.exceptions import PermissionDenied



                     raise PermissionDenied("You do not have permission to edit shared questions.")



            except:



                pass # get_object will fail safely later if 404



        return super().dispatch(request, *args, **kwargs)







    def get_form_kwargs(self):



        kwargs = super().get_form_kwargs()



        kwargs['user'] = self.request.user



        return kwargs







class QuestionDeleteView(LoginRequiredMixin, DeleteView):



    model = Question



    success_url = reverse_lazy('question_list')



    template_name = 'question_confirm_delete.html' 



    



    def dispatch(self, request, *args, **kwargs):



        if getattr(request.user, 'role', '') != 'MASTER':



             from django.core.exceptions import PermissionDenied



             raise PermissionDenied("Only MASTER can delete questions.")



        return super().dispatch(request, *args, **kwargs)







    def get_queryset(self):



        return Question.objects.filter(user=self.request.user)







from django.views.generic import TemplateView







class QuestionDetailView(LoginRequiredMixin, MobileTemplateMixin, TemplateView):



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



                    Q(user=request.user) | Q(is_shared=True) | Q(user__role='MASTER')



                ).distinct().prefetch_related('category', 'rank').get(pk=question_id)



                



                # Get latest answer per target with count



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



            Q(user=request.user) | Q(is_shared=True) | Q(user__role='MASTER')



        ).distinct().select_related('category').order_by('category', 'order', 'title')



        



        # Prepare questions data for JavaScript



        questions_json = json.dumps([{



            'id': q.id,



            'title': q.title,



            'category_id': q.category.id if q.category else None



        } for q in questions])



        



        # Get categories for filter (Owned OR Shared OR MASTER)



        categories = QuestionCategory.objects.filter(



            Q(user=request.user) | Q(is_shared=True) | Q(user__role='MASTER')



        ).distinct().order_by('order', 'created_at')



        



        # Get groups for filter



        from intelligence.models import TargetGroup



        groups = TargetGroup.objects.filter(user=request.user)







        # Get all targets for Add Modal



        from intelligence.models import Target



        all_targets = Target.objects.filter(user=request.user).order_by('nickname')



        



        context = {



            'question': question,



            'answer_data': answer_data,



            'questions': questions_json,



            'categories': categories,



            'groups': groups,



            'all_targets': all_targets,



            'total_answers': sum(x['answer_count'] for x in answer_data) if answer_data else 0,



            'total_targets': len(answer_data)



        }



        



        return render(request, self.get_template_names(), context)











# API Views for Dynamic Add



class CategoryCreateView(LoginRequiredMixin, View):



    def post(self, request, *args, **kwargs):



        if getattr(request.user, 'role', '') != 'MASTER':



             return JsonResponse({'success': False, 'error': 'Only MASTER can create categories.'})



        try:



            data = json.loads(request.body)



            name = data.get('name')



            desc = data.get('description', '')



            if not name: return JsonResponse({'success': False, 'error': 'Name required'})



            



            # Categories are shared by default if created by MASTER? 



            # Looking at init_data.py, they have is_shared=True.



            cat = QuestionCategory.objects.create(user=request.user, name=name, description=desc, is_shared=True)



            return JsonResponse({'success': True, 'id': cat.id, 'name': cat.name})



        except Exception as e:



            return JsonResponse({'success': False, 'error': str(e)})











class RankCreateView(LoginRequiredMixin, View):



    def post(self, request, *args, **kwargs):



        if getattr(request.user, 'role', '') != 'MASTER':



             return JsonResponse({'success': False, 'error': 'Only MASTER can create ranks.'})



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



            from django.db.models import Count, Q, Max



            



            target_id = request.GET.get('target_id')



            if not target_id:



                return JsonResponse({'success': False, 'error': 'Target ID required'})



            



            # Access Check



            get_object_or_404(Target, pk=target_id, user=request.user)



            



            # Fetch all categories



            # Including 'Uncategorized'? Maybe handling null category questions separately or generic



            # Fetch Questions first to know which categories are needed



            questions_qs = Question.objects.filter(



                Q(is_shared=True) | Q(user=request.user) | Q(user__role='MASTER')



            ).distinct().select_related('category', 'rank').order_by('category__id', 'order', 'title')



            



            # Get IDs of categories used by these questions



            category_ids = questions_qs.values_list('category_id', flat=True).distinct()







            # Fetch Categories (User's OR Shared OR MASTER OR Used by Questions)



            categories = QuestionCategory.objects.filter(



                Q(user=request.user) | Q(is_shared=True) | Q(user__role='MASTER') | Q(id__in=category_ids)



            ).distinct().order_by('order', 'created_at')



            



            # We can't easily annotate a filtered count inside a related manager query for serialization 



            # without complex Prefetch or annotation.



            # Simpler approach: Fetch log counts separately or use subquery.



            



            # Use annotation with Q filter on TimelineItem



            # But Question -> TimelineItem (reverse relation name defaults to 'timelineitem_set' or similar?)



            # TimelineItem has 'question' FK. So 'timelineitem'.



            



            questions_qs = questions_qs.annotate(



                answer_count=Count('timelineitem', filter=Q(timelineitem__target_id=target_id)),



                latest_answer=Max('timelineitem__date', filter=Q(timelineitem__target_id=target_id))



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



                    'count': q.answer_count,



                    'latest_date': q.latest_answer.strftime('%Y-%m-%d') if q.latest_answer else ''



                }



                



                if q.category:



                    if q.category.id in categorized_data:



                         categorized_data[q.category.id]['questions'].append(q_data)



                    else:



                         categorized_data['none']['questions'].append(q_data) # Fallback



                else:



                    categorized_data['none']['questions'].append(q_data)



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







class HelpView(LoginRequiredMixin, MobileTemplateMixin, TemplateView):



    template_name = 'help.html'



    mobile_template_name = 'mobile/help_mobile.html'







import csv

import urllib.parse

from django.http import HttpResponse



class TargetExportView(LoginRequiredMixin, View):

    def get(self, request, pk, *args, **kwargs):

        from accounts.models import CustomUser

        # 1. Check Permissions (MASTER or ELITE_AGENT only)

        if request.user.role not in [CustomUser.MASTER, CustomUser.ELITE_AGENT]:

             return render(request, '403.html', status=403) # Or simple HttpResponseForbidden



        target = get_object_or_404(Target, pk=pk, user=request.user)

        

        # 2. Prepare Response (Shift-JIS)

        # Handle filename encoding for various browsers (URL encode usually safe)

        filename = f"{target.nickname}_dossier_export.csv"

        quoted_filename = urllib.parse.quote(filename)

        

        response = HttpResponse(content_type='text/csv; charset=Shift-JIS')

        response['Content-Disposition'] = f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}'

        

        # Wrapper to handle encoding errors (replace chars not in Shift-JIS)

        # Since csv.writer writes strings and HttpResponse encodes them, we need to ensure

        # the strings we pass contain only characters representable in Shift-JIS

        # OR we rely on Python's error handling. 

        # But HttpResponse using charset='Shift-JIS' might raise UnicodeEncodeError if content has unmappable chars.

        # Strategy: Clean data before passing to writer.

        

        def clean(text):

            if text is None: return ""

            text = str(text)

            # Replace unmappable characters with '?'

            return text.encode('cp932', 'replace').decode('cp932')



        writer = csv.writer(response)



        # 3. Row 1: Profile Headers

        header_row1 = [

            'ニックネーム', '姓名', 'せいめい', '生年月日', '年齢', '干支', 

            '星座', '性別', '血液型', '出身地', '所属グループ', '記念日'

        ]

        writer.writerow([clean(h) for h in header_row1])



        # 4. Row 2: Profile Data

        # Groups

        groups_str = " ".join([g.name for g in target.groups.all()])

        

        # Anniversaries

        annivs = []

        if target.birth_month and target.birth_day:

             annivs.append(f"誕生日({target.birth_month}/{target.birth_day})")

        for ca in target.customanniversary_set.all():

             annivs.append(f"{ca.label}({ca.date.month}/{ca.date.day})")

        annivs_str = " ".join(annivs)

        

        # Full Name & Kana

        full_name = f"{target.last_name} {target.first_name}".strip()

        full_name_kana = f"{target.last_name_kana} {target.first_name_kana}".strip()

        

        # Birthdate

        birth_date = ""

        if target.birth_year and target.birth_month and target.birth_day:

            birth_date = f"{target.birth_year}/{target.birth_month}/{target.birth_day}"

        elif target.birth_month and target.birth_day:

             birth_date = f"--/{target.birth_month}/{target.birth_day}"



        data_row1 = [

            target.nickname,

            full_name,

            full_name_kana,

            birth_date,

            target.age if target.age else "",

            target.eto if target.eto else "",

            target.zodiac_hiragana, # Use property

            target.get_gender_display(),

            target.get_blood_type_display(),

            target.birthplace,

            groups_str,

            annivs_str

        ]

        writer.writerow([clean(d) for d in data_row1])

        

        # 5. Row 3: Log Headers

        header_row2 = [

            '発生日', 'ニックネーム', '接触有無', 'イベント・質問', '内容', 

            'タグ', '質問名', '回答', '入力日', '更新日'

        ]

        writer.writerow([clean(h) for h in header_row2])

        

        # 6. Row 4+: Log Data

        # Fetch generic timeline items (Logs) AND Question answers.

        # Requirement: "インテリジェンス・ログ" which usually means TimelineItems.

        # Sorted by date desc

        

        items = TimelineItem.objects.filter(target=target).prefetch_related('tags', 'question').order_by('-date', '-created_at')

        

        for item in items:

            # Type mapping

            # USER REQUEST: "イベント・質問"

            # TYPE_CHOICES: Contact, Note, Event, Question

            item_type = item.type

            if item.type == 'Question':

                item_type = '質問'

            elif item.type == 'Contact':

                item_type = '接触'

            elif item.type == 'Event':

                 item_type = 'イベント'

            elif item.type == 'Note':

                 item_type = 'メモ'

            

            # Tags

            tags_str = " ".join([t.name for t in item.tags.all()])

            

            # Contact Made

            contact_str = "有" if item.contact_made else "無"

            

            # Question specific

            q_title = ""

            q_answer = ""

            content = item.content

            

            if item.type == 'Question':

                if item.question:

                    q_title = item.question.title

                # For questions, 'content' stores the answer usually?

                # Check model: question_answer field exists but content is also used?

                # Views.py logic uses `item.content` for answer.

                q_answer = item.content

                content = "" # "内容" requested separate from "回答"? 

                # Request says: 質問名｜回答. "内容" is col 5. "回答" is col 8.

                # If it's a question, maybe "内容" is empty and "回答" has the answer?

                # Or "内容" has the full text?

                # Let's put answer in "回答" and keep "内容" as is (which is answer in current DB design basically).

                # Actually, let's duplicate or leave content empty if it's purely Q&A.

                # User req: "内容" ... "回答".

                # I will put item.content into "回答" for Questions, and item.content into "内容" for others.

                if item.type == 'Question':

                     content = "" 

                

            else:

                # Normal log

                content = item.content

            

            # Dates

            date_str = item.date.strftime('%Y/%m/%d')

            created_str = item.created_at.astimezone().strftime('%Y/%m/%d %H:%M')

            # Update date fallback

            updated_str = created_str # TimelineItem has no updated_at

            

            row = [

                date_str,

                target.nickname,

                contact_str,

                item_type,

                content,

                tags_str,

                q_title,

                q_answer,

                created_str,

                updated_str

            ]

            writer.writerow([clean(col) for col in row])



        return response

import csv

import io

import codecs

from django.db import transaction

from django.shortcuts import render, redirect

from django.views import View

from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponse, JsonResponse

from django.utils import timezone

from django.db.models import Q

from intelligence.models import Question, QuestionCategory, QuestionRank

from intelligence.forms import QuestionImportForm

import urllib.parse



class QuestionExportView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        # 1. Fetch visible questions

        user = request.user

        questions = Question.objects.filter(

            Q(user=user) | Q(is_shared=True)

        ).select_related('category', 'rank').order_by('category__order', 'order')



        # 2. Prepare Response (Shift-JIS)

        filename = "questions_export.csv"

        quoted_filename = urllib.parse.quote(filename)

        

        response = HttpResponse(content_type='text/csv; charset=Shift-JIS')

        response['Content-Disposition'] = f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}'

        

        # 3. CSV Writer

        # Helper to clean text for Shift-JIS

        def clean(text):

            if text is None: return ""

            text = str(text)

            return text.encode('cp932', 'replace').decode('cp932')

            

        writer = csv.writer(response)

        

        # Header

        # 





class QuestionExportView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        # 1. Fetch visible questions

        user = request.user

        questions = Question.objects.filter(

            Q(user=user) | Q(is_shared=True)

        ).select_related('category', 'rank').order_by('category__order', 'order')



        # 2. Prepare Response (Shift-JIS)

        filename = "questions_export.csv"

        quoted_filename = urllib.parse.quote(filename)

        

        response = HttpResponse(content_type='text/csv; charset=Shift-JIS')

        response['Content-Disposition'] = f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}'

        

        # 3. CSV Writer

        # Helper to clean text for Shift-JIS

        def clean(text):

            if text is None: return ""

            text = str(text)

            return text.encode('cp932', 'replace').decode('cp932')

            

        writer = csv.writer(response)

        

        # Header

        header = ['入力列', 'カテゴリー名', '共通質問', '表示順', 'ランク', '質問名', '説明・意図', '質問例', '回答形式', '選択肢']

        writer.writerow([clean(h) for h in header])

        

        for q in questions:

            row = [

                '', # Input column

                q.category.name if q.category else '未分類',

                'TRUE' if q.is_shared else 'FALSE',

                q.order,

                q.rank.name if q.rank else '',

                q.title,

                q.description,

                q.example,

                q.get_answer_type_display(),

                q.choices

            ]

            writer.writerow([clean(col) for col in row])

            

        return response



class QuestionImportView(LoginRequiredMixin, View):

    template_name = 'question_import.html'

    

    def get(self, request):

        form = QuestionImportForm()

        return render(request, self.template_name, {'form': form})

        

    def post(self, request):

        form = QuestionImportForm(request.POST, request.FILES)

        if not form.is_valid():

            return render(request, self.template_name, {'form': form})

            

        csv_file = request.FILES['file']

        

        # 1. Detect Encoding

        sample = csv_file.read(2048)

        csv_file.seek(0)

        encoding = 'utf-8'

        try:

            sample.decode('utf-8')

        except UnicodeDecodeError:

            encoding = 'cp932'

            

        # 2. Read lines

        try:

            io_text = io.TextIOWrapper(csv_file, encoding=encoding, newline='')

            reader = csv.reader(io_text)

            rows = list(reader)

        except Exception as e:

            return render(request, self.template_name, {'form': form, 'error_msg': f'ファイルの読み込みに失敗しました: {str(e)}'})



        if not rows:

             return render(request, self.template_name, {'form': form, 'error_msg': 'CSVファイルが空です。'})



        logs = []

        errors = []

        success_count = 0

        

        try:

            with transaction.atomic():

                for idx, row in enumerate(rows):

                    if idx == 0: continue

                    if len(row) < 6: continue

                         

                    line_no = idx + 1

                    input_act = row[0].strip().lower()

                    cat_name = row[1].strip()

                    is_shared_str = row[2].strip().upper()

                    order_str = row[3].strip()

                    rank_name = row[4].strip()

                    title = row[5].strip()

                    desc = row[6].strip() if len(row) > 6 else ""

                    example = row[7].strip() if len(row) > 7 else ""

                    type_str = row[8].strip() if len(row) > 8 else "自由記述"

                    choices = row[9].strip() if len(row) > 9 else ""

                    

                    if not input_act:

                        logs.append(f"{line_no}行目: スキップ (入力列が空)")

                        continue

                    if input_act not in ['n', 'u', 'd']:

                        logs.append(f"{line_no}行目: スキップ (入力列 '{input_act}' は無効)")

                        continue

                        

                    if not title:

                         errors.append(f"{line_no}行目: 質問名が必須です。")

                         continue

                         

                    category = None

                    if not cat_name: cat_name = 'Unclassified'

                    

                    category = QuestionCategory.objects.filter(

                        Q(user=request.user) | Q(is_shared=True),

                        name=cat_name

                    ).first()

                    

                    if not category:

                         if cat_name == 'Unclassified':

                              errors.append(f"{line_no}行目: カテゴリー「{cat_name}」が見つかりませんでした。")

                              continue

                         else:

                              errors.append(f"{line_no}行目: カテゴリー「{cat_name}」が見つかりませんでした。")

                              continue



                    rank = None

                    if rank_name and rank_name != 'Null':

                        rank = QuestionRank.objects.filter(user=request.user, name=rank_name).first()

                        if not rank:

                             errors.append(f"{line_no}行目: ランク「{rank_name}」が見つかりませんでした。")

                             continue

                    

                    answer_type = 'TEXT'

                    if type_str == '選択式':

                        answer_type = 'SELECTION'

                        if not choices:

                             errors.append(f"{line_no}行目: 選択式を選んだ場合、選択肢は必須です。")

                             continue

                    elif type_str == '自由記述':

                        answer_type = 'TEXT'

                    else:

                         errors.append(f"{line_no}行目: 回答形式「{type_str}」が見つかりませんでした。")

                         continue

                         

                    is_shared = False

                    if is_shared_str == 'TRUE': is_shared = True

                    

                    try:

                        order = int(order_str) if order_str else 0

                    except ValueError:

                        order = 0



                    existing_q = Question.objects.filter(

                        Q(user=request.user) | Q(is_shared=True),

                        title=title

                    ).first()

                    

                    if input_act == 'n':

                        if existing_q:

                            errors.append(f"{line_no}行目: 同じ質問名の質問が存在します。")

                            continue

                        Question.objects.create(

                            user=request.user,

                            category=category,

                            rank=rank,

                            title=title,

                            description=desc,

                            example=example,

                            answer_type=answer_type,

                            choices=choices,

                            is_shared=is_shared,

                            order=order

                        )

                        success_count += 1

                        

                    elif input_act == 'u':

                        if not existing_q:

                            errors.append(f"{line_no}行目: 更新対象の質問「{title}」が見つかりませんでした。")

                            continue

                        existing_q.category = category

                        existing_q.rank = rank

                        existing_q.description = desc

                        existing_q.example = example

                        existing_q.answer_type = answer_type

                        existing_q.choices = choices

                        existing_q.is_shared = is_shared

                        existing_q.order = order

                        existing_q.save()

                        success_count += 1

                        

                    elif input_act == 'd':

                        if not existing_q:

                             logs.append(f"{line_no}行目: 削除対象の質問「{title}」が見つかりませんでした。")

                             continue

                        existing_q.delete()

                        success_count += 1



                if errors:

                    raise Exception("Validation Error")

                    

        except Exception as e:

            if str(e) == "Validation Error":

                pass

            else:

                errors.append(f"システムエラー: {str(e)}")

        

        if errors:

            return render(request, self.template_name, {

                'form': form, 

                'error_list': errors,

                'logs': logs

            })

            

        return render(request, self.template_name, {

            'form': form,

            'success_msg': f'{success_count}件の処理が完了しました。',

            'logs': logs

        })


class CalendarView(LoginRequiredMixin, MobileTemplateMixin, View):
    template_name = 'mobile/calendar_mobile.html'
    
    def get(self, request):
        import datetime
        from django.utils import timezone
        import calendar
        
        # 1. Determine Selected Month (Default: Today)
        today = datetime.date.today()
        year_param = request.GET.get('year')
        month_param = request.GET.get('month')
        
        try:
            year = int(year_param) if year_param else today.year
            month = int(month_param) if month_param else today.month
            selected_date = datetime.date(year, month, 1)
        except ValueError:
            selected_date = today.replace(day=1)
            year = selected_date.year
            month = selected_date.month

        # 2. Calculate Date Range (1 month prior, 3 months future -> Total ~5 months)
        # User request: "1 month prior... combined 5 months"
        # Actually logic: Start = 1 month before selected. End = 3 months after selected.
        
        # Start: 1st day of previous month
        start_date = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        # If user selected a specific month, base it on that?
        # "Display 1 year prior" was the old logic based on `today` usually, or selected?
        # Let's base it on the selected month if provided, else today.
        
        base_date = datetime.date(year, month, 1)
        # 1 month prior
        start_date = (base_date - datetime.timedelta(days=1)).replace(day=1)
        # 3 months after (End of 3rd month)
        # month + 3
        # Logic: 
        # m=1, +3 = 4. End date = Last day of Month 4.
        
        def add_months(d, months):
            month = d.month - 1 + months
            year = d.year + month // 12
            month = month % 12 + 1
            day = min(d.day, [31,
                29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            return d.replace(year=year, month=month, day=day)

        end_date = add_months(base_date, 3) 
        # Get end of that month
        next_month = end_date.replace(day=28) + datetime.timedelta(days=4)
        end_date = next_month - datetime.timedelta(days=next_month.day)
        
        # 3. Fetch Data within Range
        user = request.user
        
        # A. Plans (Manual Events) - Type='Event'
        plans = TimelineItem.objects.filter(
            target__user=user,
            date__range=[start_date, end_date],
            type='Event'
        ).select_related('target').order_by('date')
        
        # B. Activity Logs (Contact, Note, Question...) - Exclude Event & DailyState
        # Distinct targets per day
        activities = TimelineItem.objects.filter(
            target__user=user,
            date__range=[start_date, end_date]
        ).exclude(type__in=['Event', 'DailyState']).select_related('target').order_by('date')
        
        # C. Group Rotations (DailyTargetState) - Count per day
        from django.db.models import Count
        group_states = TimelineItem.objects.filter(
            target__user=user,
            date__range=[start_date, end_date],
            type='DailyState'
        ).values('date').annotate(count=Count('id'))
        group_counts = {item['date']: item['count'] for item in group_states}
        
        custom_anniversaries = CustomAnniversary.objects.filter(target__user=user).select_related('target')
        targets = Target.objects.filter(user=user)
        
        # 4. Organize into Days
        days_data = []
        current = start_date
        
        plans_by_date = {}
        for p in plans:
            if p.date not in plans_by_date: plans_by_date[p.date] = []
            plans_by_date[p.date].append(p)
            
        activities_by_date = {}
        for a in activities:
            if a.date not in activities_by_date: activities_by_date[a.date] = set()
            activities_by_date[a.date].add(a.target) # Use set for uniqueness
            
        while current <= end_date:
            day_info = {
                'date': current,
                'is_today': (current == today),
                'is_selected_month': (current.year == year and current.month == month),
                'plans': plans_by_date.get(current, []),
                'activity_targets': list(activities_by_date.get(current, [])),
                'anniversaries': [],
                'group_count': group_counts.get(current, 0)
            }
            
            # Anniversaries logic matches previous...
            for anniv in custom_anniversaries:
                if anniv.date.month == current.month and anniv.date.day == current.day:
                    years_diff = current.year - anniv.date.year
                    label = f"{anniv.label}"
                    if years_diff > 0: label += f" ({years_diff}周年)"
                    day_info['anniversaries'].append({'target': anniv.target, 'label': label, 'type': 'anniv'})
                    
            for t in targets:
                if t.birth_month == current.month and t.birth_day == current.day:
                    if t.birth_year:
                        age_at_date = current.year - t.birth_year
                        label = f"誕生日 ({age_at_date}歳)"
                    else:
                        label = "誕生日"
                    day_info['anniversaries'].append({'target': t, 'label': label, 'type': 'birthday'})

            days_data.append(day_info)
            current += datetime.timedelta(days=1)
            
        context = {
            'days': days_data,
            'selected_year': year,
            'selected_month': month,
            'all_targets': targets, 
            'today': today
        }
        
        return render(request, self.template_name, context)

    def post(self, request):
        try:
            target_id = request.POST.get('target_id')
            date_str = request.POST.get('date')
            title = request.POST.get('title')
            
            if not target_id or not date_str or not title:
                return JsonResponse({'success': False, 'error': 'Missing fields'})
                
            target = Target.objects.get(pk=target_id, user=request.user)
            
            TimelineItem.objects.create(
                target=target,
                date=date_str,
                type='Event',
                title=title,
                contact_made=False
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

