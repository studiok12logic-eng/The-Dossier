import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from intelligence.models import TimelineItem, Target
from django.contrib.auth import get_user_model
from django.db.models import Count

# Create Test Data
User = get_user_model()
user, _ = User.objects.get_or_create(username='debug_user', defaults={'password': 'password'})
target, _ = Target.objects.get_or_create(user=user, nickname='DebugTarget')

import datetime
today = datetime.date.today()
start_date = today - datetime.timedelta(days=7)
end_date = today + datetime.timedelta(days=7)

# Ensure data exists
TimelineItem.objects.filter(target=target).delete()

# 1. Create a Plan (Event) on Today
p1 = TimelineItem.objects.create(target=target, date=today, type='Event', title='Dinner Plan')
print(f"Created Plan: {p1}")

# 2. Create a Note on Today
n1 = TimelineItem.objects.create(target=target, date=today, type='Note', title='Note concerning dinner')
print(f"Created Note: {n1}")

# 3. Create a Contact on Today
c1 = TimelineItem.objects.create(target=target, date=today, type='Contact', title='Call')
print(f"Created Contact: {c1}")

# 4. Create an Event on Today (Another plan)
p2 = TimelineItem.objects.create(target=target, date=today, type='Event', title='Lunch Plan')
print(f"Created Plan 2: {p2}")

# 5. Create a Note on Tomorrow
n2 = TimelineItem.objects.create(target=target, date=today + datetime.timedelta(days=1), type='Note', title='Tomorrow note')
print(f"Created Tomorrow Note: {n2}")


# --- Simulate View Logic ---
start_date_range = today - datetime.timedelta(days=2)
end_date_range = today + datetime.timedelta(days=2)

activities = TimelineItem.objects.filter(
    target__user=user,
    date__range=[start_date_range, end_date_range] # Replicating view logic
).exclude(type__in=['DailyState']).select_related('target').order_by('date')

plans = TimelineItem.objects.filter(
    target__user=user,
    date__range=[start_date_range, end_date_range],
    type='Event'
).select_related('target').order_by('date')

print(f"\nActivities found (Excluding Event/DailyState): {[a.title for a in activities]}")
print(f"Plans found: {[p.title for p in plans]}")

# Calculation
log_counts = {} # (date, target_id) -> count
for a in activities:
     key = (a.date, a.target.id)
     log_counts[key] = log_counts.get(key, 0) + 1

print(f"\nLog Counts Map: {log_counts}")

plans_by_date = {}
for p in plans:
    if p.date not in plans_by_date: plans_by_date[p.date] = []
    
    existing_targets = {x.target_id for x in plans_by_date[p.date]}
    if p.target_id not in existing_targets:
        p.target.day_log_count = log_counts.get((p.date, p.target.id), 0)
        plans_by_date[p.date].append(p)
        print(f"Plan '{p.title}' assigned day_log_count: {p.target.day_log_count}")
    else:
        print(f"Plan '{p.title}' skipped as duplicate target for day")

