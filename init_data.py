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
else:
    print("Targets already exist.")
