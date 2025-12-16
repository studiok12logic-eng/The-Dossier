from django.contrib.auth import get_user_model
from intelligence.models import Target, TimelineItem
from django.utils import timezone
import datetime

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
    print("Superuser 'admin' created.")

if not Target.objects.exists():
    t = Target.objects.create(
        nickname="Elara Vance",
        rank="A",
        origin="Neo-Tokyo Sector 7",
        intel_depth=60.0,
        last_contact=timezone.now(),
        gender="Female"
    )
    TimelineItem.objects.create(
        target=t,
        type="EVENT",
        date=timezone.now() - datetime.timedelta(days=1),
        content="Target confirmed preference for 'Synthetic Jazz'. Location identified: 'The Blue Neon' club.",
        sentiment="Neutral"
    )
    TimelineItem.objects.create(
        target=t,
        type="EVENT",
        date=timezone.now() - datetime.timedelta(days=2),
        content="Sub-vocalization intercepted. Keywords: 'Project Chimera', 'Thursday'.",
        sentiment="Alert"
    )
    print("Initial target created.")

# --- System Default Questions ---
from intelligence.models import Question, QuestionCategory

# Ensure Admin User
admin_user = User.objects.get(username='admin')

# 1. Categories
system_cat, _ = QuestionCategory.objects.get_or_create(user=admin_user, name="Basic Profile", description="Fundamental details")

# 2. Questions
default_questions = [
    {"title": "現在の住所", "desc": "Current residence address", "type": "TEXT", "order": 1},
    {"title": "職業", "desc": "Current occupation/role", "type": "TEXT", "order": 2},
    {"title": "趣味", "desc": "Hobbies and interests", "type": "TEXT", "order": 3},
    {"title": "弱点/苦手なもの", "desc": "Weaknesses or dislikes", "type": "TEXT", "order": 4},
    {"title": "得意なこと", "desc": "Strengths or skills", "type": "TEXT", "order": 5},
    {"title": "家族構成", "desc": "Family structure", "type": "TEXT", "order": 6},
    {"title": "性格", "desc": "Personality traits", "type": "TEXT", "order": 7},
]

print("Initializing System Questions...")
for q_data in default_questions:
    q, created = Question.objects.get_or_create(
        user=admin_user,
        title=q_data["title"],
        defaults={
            "description": q_data["desc"],
            "category": system_cat,
            "answer_type": q_data["type"],
            "is_shared": True, # Shared with all users
            "order": q_data["order"]
        }
    )
    if created:
        print(f"Created System Question: {q.title}")
    else:
        # Ensure it is shared if it already exists (updates existing defaults)
        if not q.is_shared:
            q.is_shared = True
            q.save()
            print(f"Updated System Question to Shared: {q.title}")

print("Initialization Complete.")
