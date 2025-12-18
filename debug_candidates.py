
import os
import django
import datetime
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from intelligence.models import Target, DailyTargetState, CustomAnniversary, TargetGroup
from django.db.models import Max, Q

# Mock User - assume first user or specific username
User = get_user_model()
user = User.objects.first()
print(f"User: {user}")

# Method (copied from views.py logic)
def get_daily_target_ids(user, date):
    weekday = date.weekday()
    weekday_map = ['is_mon', 'is_tue', 'is_wed', 'is_thu', 'is_fri', 'is_sat', 'is_sun']
    current_weekday_field = weekday_map[weekday]
    
    # 1. Base Logic (Groups)
    print(f"Checking groups for {current_weekday_field}=True")
    try:
        group_filter = {current_weekday_field: True}
        base_targets = Target.objects.filter(
            user=user,
            groups__in=TargetGroup.objects.filter(**group_filter)
        ).distinct()
        print(f"Base targets: {base_targets.count()}")
    except Exception as e:
        print(f"Error in base logic: {e}")
        base_targets = Target.objects.none()

    # 2. Anniversary Logic
    anniv_ids = set()
    
    # Birthday (Today)
    try:
        birthday_targets = Target.objects.filter(
            user=user,
            birth_month=date.month,
            birth_day=date.day
        )
        anniv_ids.update(birthday_targets.values_list('id', flat=True))
    except Exception as e:
        print(f"Error in birthday logic: {e}")

    # Custom Anniv (Today)
    try:
        custom_annivs = CustomAnniversary.objects.filter(
            target__user=user,
            date__month=date.month,
            date__day=date.day
        )
        anniv_ids.update(custom_annivs.values_list('target_id', flat=True))
    except Exception as e:
        print(f"Error in custom anniv logic: {e}")
    
    # 3. Manual State
    try:
        daily_states = DailyTargetState.objects.filter(target__user=user, date=date)
        manual_add_ids = set(daily_states.filter(is_manual_add=True).values_list('target_id', flat=True))
        hidden_ids = set(daily_states.filter(is_hidden=True).values_list('target_id', flat=True))
    except Exception as e:
        print(f"Error in daily state logic: {e}")
        manual_add_ids = set()
        hidden_ids = set()
    
    # Combine
    final_ids = set(base_targets.values_list('id', flat=True))
    final_ids.update(anniv_ids)
    final_ids.update(manual_add_ids)
    final_ids = final_ids - hidden_ids
    
    return final_ids

# Test Execution
today_date = datetime.date.today()
print(f"Date: {today_date}")

try:
    current_ids = get_daily_target_ids(user, today_date)
    print(f"Current IDs: {len(current_ids)}")
    
    candidates = Target.objects.filter(user=user).exclude(id__in=current_ids).annotate(
        last_contact=Max('timelineitem__date', filter=Q(timelineitem__contact_made=True))
    ).order_by('last_contact', 'nickname')
    
    print(f"Candidates Mock Query Count: {candidates.count()}")
    for c in candidates:
        print(f"- {c.nickname} (Last: {c.last_contact})")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
