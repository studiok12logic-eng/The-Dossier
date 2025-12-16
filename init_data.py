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
        role_rank="A",
        # origin="Neo-Tokyo Sector 7", # Field removed
        # intel_depth=60.0, # Field removed
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
# Ensure Admin has MASTER role
if hasattr(admin_user, 'role') and admin_user.role != 'MASTER':
    admin_user.role = 'MASTER'
    admin_user.save()
    print("Admin role updated to MASTER.")

# 1. Categories
system_cat, _ = QuestionCategory.objects.get_or_create(user=admin_user, name="その他", description="Fundamental details")

# 2. Questions Configuration
# title: 質問名（画面に表示される名前）
# desc:  質問の説明・意図（入力時のヒントになります）
# type:  回答形式 ('TEXT'=自由記述, 'SELECTION'=選択式)
# choices: 選択肢（カンマ区切り文字列）。type='SELECTION'の場合に必須です。
# order: 表示順（数字が小さい順に表示されます）
# category: カテゴリ名（指定しない場合は "その他" になります）
default_questions = [
    {"title": "現住所", "desc": "今現在住んでいる住所", "type": "TEXT", "order": 1, "category": "基本情報"},
    {"title": "職業", "desc": "現在の職業や役職", "type": "TEXT", "order": 2, "category": "基本情報"},
    {"title": "趣味", "desc": "趣味や興味のあること", "type": "TEXT", "order": 3, "category": "パーソナリティ"},
    {"title": "弱点/苦手なもの", "desc": "弱点や苦手なこと", "type": "TEXT", "order": 4, "category": "パーソナリティ"},
    {"title": "得意なこと", "desc": "得意なことや得意なスキル", "type": "TEXT", "order": 5, "category": "パーソナリティ"},
    {"title": "家族構成", "desc": "家族構成や関係", "type": "TEXT", "order": 6, "category": "基本情報"},
    {"title": "性格", "desc": "性格や性格の特徴", "type": "SELECTION", "choices": "内向型,外向型,内向型,外向型,内向型,外向型", "order": 7, "category": "パーソナリティ"},
]

print("Initializing System Questions...")
for q_data in default_questions:
    cat_name = q_data.get("category", "Basic Profile")
    cat_obj, _ = QuestionCategory.objects.get_or_create(user=admin_user, name=cat_name)

    q, created = Question.objects.get_or_create(
        user=admin_user,
        title=q_data["title"],
        defaults={
            "description": q_data["desc"],
            "category": cat_obj,
            "answer_type": q_data["type"],
            "choices": q_data.get("choices", ""), # Add choices here
            "is_shared": True, 
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
