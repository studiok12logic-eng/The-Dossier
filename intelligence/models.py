from django.db import models
from django.conf import settings
import uuid
from django_cryptography.fields import encrypt

class Tag(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

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
    
    # 1. Identity - Encrypted
    nickname = encrypt(models.CharField(max_length=100, verbose_name="ニックネーム"))
    first_name = encrypt(models.CharField(max_length=100, blank=True, verbose_name="名"))
    last_name = encrypt(models.CharField(max_length=100, blank=True, verbose_name="姓"))
    first_name_kana = encrypt(models.CharField(max_length=100, blank=True, verbose_name="めい"))
    last_name_kana = encrypt(models.CharField(max_length=100, blank=True, verbose_name="せい"))
    
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
    
    # 5. Notes - Encrypted
    description = encrypt(models.TextField(blank=True)) # Use description for general notes
    
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

    @property
    def eto(self):
        if not self.birth_year: return None
        etos = ['申','酉','戌','亥','子','丑','寅','卯','辰','巳','午','未']
        return etos[self.birth_year % 12]

    @property
    def gender_symbol(self):
        if self.gender == 'Male': return '♂'
        if self.gender == 'Female': return '♀'
        return '-'

    @property
    def zodiac_hiragana(self):
        mapping = {
            '牡羊座': 'おひつじ座', '牡牛座': 'おうし座', '双子座': 'ふたご座',
            '蟹座': 'かに座', '獅子座': 'しし座', '乙女座': 'おとめ座',
            '天秤座': 'てんびん座', '蠍座': 'さそり座', '射手座': 'いて座',
            '山羊座': 'やぎ座', '水瓶座': 'みずがめ座', '魚座': 'うお座'
        }
        return mapping.get(self.zodiac_sign, self.zodiac_sign or '-')

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
    # Encrypted
    title = encrypt(models.CharField(max_length=200, blank=True, null=True, default=''))
    content = encrypt(models.TextField(blank=True, null=True, default='')) 
    tags = models.ManyToManyField(Tag, blank=True)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='Neutral')
    
    # New Fields for Dossier Feature
    contact_made = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Question specific
    question_category = models.CharField(max_length=100, blank=True, null=True, default='')
    question_text = models.CharField(max_length=255, blank=True, null=True, default='')
    # Encrypted
    question_answer = encrypt(models.TextField(blank=True, default=''))
    question = models.ForeignKey('Question', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.target} - {self.type} ({self.date.strftime('%Y-%m-%d')})"

class TimelineImage(models.Model):
    item = models.ForeignKey(TimelineItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='timeline_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.item}"

class QuestionCategory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_shared = models.BooleanField(default=False)
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
    
    is_shared = models.BooleanField(default=False, verbose_name="共通") # True=Common (System), False=Individual
    order = models.IntegerField(default=0, verbose_name="表示順")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
