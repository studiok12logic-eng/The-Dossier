from django.contrib.auth import get_user_model
from intelligence.models import (
    Target, TimelineItem, TargetGroup, Question, Tag, 
    QuestionCategory, QuestionRank, DailyTargetState, CustomAnniversary
)
from django.db import transaction

User = get_user_model()

def reset_db_safe():
    print("WARNING: This will delete ALL intelligence data.")
    print("Master Account (admin) will be PRESERVED.")
    
    with transaction.atomic():
        print("1. Deleting Timeline Logs...")
        TimelineItem.objects.all().delete()
        
        print("2. Deleting Target States & Anniversaries...")
        DailyTargetState.objects.all().delete()
        CustomAnniversary.objects.all().delete()
        
        print("3. Deleting Targets...")
        Target.objects.all().delete()
        
        print("4. Deleting Groups...")
        TargetGroup.objects.all().delete()
        
        print("5. Deleting Questions & Categories...")
        Question.objects.all().delete()
        QuestionCategory.objects.all().delete()
        QuestionRank.objects.all().delete()
        
        print("6. Deleting Tags...")
        Tag.objects.all().delete()
        
        # Optional: Delete non-admin users
        # print("7. Deleting Non-Admin Users...")
        # count, _ = User.objects.exclude(username='admin').delete()
        # print(f"   Deleted {count} users.")
        
    print("Database Reset Complete (Admin preserved).")

if __name__ == "__main__":
    reset_db_safe()
