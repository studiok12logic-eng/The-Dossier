from django.db import models
from django.conf import settings
import uuid

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Quest(models.Model):
    text = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    difficulty = models.IntegerField(default=1)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.text

class TargetGroup(models.Model):
    name = models.CharField(max_length=100) # Removed unique=True for multi-tenancy
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1)
    description = models.TextField(blank=True)
    # Contact Frequency (Days of Week)
    is_mon = models.BooleanField(default=False, verbose_name="月")
    is_tue = models.BooleanField(default=False, verbose_name="火")
    is_wed = models.BooleanField(default=False, verbose_name="水")
    is_thu = models.BooleanField(default=False, verbose_name="木")
    is_fri = models.BooleanField(default=False, verbose_name="金")
    is_sat = models.BooleanField(default=False, verbose_name="土")
    is_sun = models.BooleanField(default=False, verbose_name="日")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Target(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1)
    
    # 1. Identity
    nickname = models.CharField(max_length=100, verbose_name="ニックネーム")
    first_name = models.CharField(max_length=100, blank=True, verbose_name="名")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="姓")
    first_name_kana = models.CharField(max_length=100, blank=True, verbose_name="めい")
    last_name_kana = models.CharField(max_length=100, blank=True, verbose_name="せい")
    
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # 2. Bio-Metrics
    birth_year = models.IntegerField(null=True, blank=True)
    birth_month = models.IntegerField(null=True, blank=True)
    birth_day = models.IntegerField(null=True, blank=True)
    zodiac_sign = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, blank=True, choices=[('Male', '男性'), ('Female', '女性'), ('Other', 'その他')])
    blood_type = models.CharField(max_length=5, blank=True, choices=[('A', 'A'), ('B', 'B'), ('O', 'O'), ('AB', 'AB')])
    birthplace = models.CharField(max_length=100, blank=True)
    
    # 3. Affiliation
    groups = models.ManyToManyField(TargetGroup, blank=True)
    role_rank = models.CharField(max_length=100, blank=True) # Kept for backward compat if needed, though removed from form
    
    # 5. Notes
    description = models.TextField(blank=True) # Use description for general notes
    
    # Metadata
    last_contact = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nickname} ({self.last_name} {self.first_name})"

    @property
    def age(self):
        if self.birth_year:
            import datetime
            today = datetime.date.today()
            return today.year - self.birth_year - ((today.month, today.day) < (self.birth_month or 1, self.birth_day or 1))
        return None

class DailyTargetState(models.Model):
    target = models.ForeignKey(Target, on_delete=models.CASCADE)
    date = models.DateField()
    is_manual_add = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['target', 'date'], name='unique_target_date_state')
        ]
        
    def __str__(self):
        return f"{self.target} on {self.date}: +{self.is_manual_add} / -{self.is_hidden}"

class CustomAnniversary(models.Model):
    target = models.ForeignKey(Target, on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    date = models.DateField()
    
    def __str__(self):
        return f"{self.label} ({self.date})"

class TimelineItem(models.Model):
    TYPE_CHOICES = [
        ('Contact', 'Contact'),
        ('Quest', 'Quest'),
        ('Note', 'Note'),
        ('Event', 'Event'),      # New: Events/Happenings
        ('Question', 'Question') # New: Questions asked/answered
    ]
    SENTIMENT_CHOICES = [
        ('Positive', 'Positive'),
        ('Neutral', 'Neutral'),
        ('Negative', 'Negative'),
    ]
    
    target = models.ForeignKey(Target, on_delete=models.CASCADE)
    date = models.DateField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True) # Blank allowed if just contact check?
    related_quest = models.ForeignKey(Quest, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='Neutral')
    
    # New Fields for Dossier Feature
    contact_made = models.BooleanField(default=False)
    
    # Question specific
    question_category = models.CharField(max_length=100, blank=True)
    question_text = models.CharField(max_length=255, blank=True)
    question_answer = models.TextField(blank=True)
    question = models.ForeignKey('Question', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.target} - {self.type} ({self.date.strftime('%Y-%m-%d')})"

class QuestionCategory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class QuestionRank(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.points}pt)"

class Question(models.Model):
    ANSWER_TYPES = [
        ('SELECTION', '選択式'),
        ('TEXT', '自由記述'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(QuestionCategory, on_delete=models.SET_NULL, null=True, blank=True)
    rank = models.ForeignKey(QuestionRank, on_delete=models.SET_NULL, null=True, blank=True)
    
    title = models.CharField(max_length=200, verbose_name="質問名")
    description = models.TextField(blank=True, verbose_name="説明（意図）")
    example = models.TextField(blank=True, verbose_name="質問例")
    
    answer_type = models.CharField(max_length=20, choices=ANSWER_TYPES, default='TEXT', verbose_name="回答形式")
    choices = models.TextField(blank=True, verbose_name="選択肢 (カンマ区切り)")
    
    is_shared = models.BooleanField(default=False, verbose_name="共通/個別") # True=Shared, False=Individual
    order = models.IntegerField(default=0, verbose_name="表示順")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
