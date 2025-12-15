from django.db import models
from django.contrib.auth.models import User
import uuid

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Quest(models.Model):
    text = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    difficulty = models.IntegerField(default=1)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.text

class TargetGroup(models.Model):
    name = models.CharField(max_length=100) # Removed unique=True for multi-tenancy
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Target(models.Model):
    RANK_CHOICES = [] # Removed
    GENDER_CHOICES = [
        ('Male', '男性'), ('Female', '女性'), ('Other', 'その他'), ('Unknown', '不明'),
    ]
    BLOOD_CHOICES = [
        ('A', 'A型'), ('B', 'B型'), ('O', 'O型'), ('AB', 'AB型'), ('Unknown', '不明'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    last_name = models.CharField(max_length=50, blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name_kana = models.CharField(max_length=50, blank=True)
    first_name_kana = models.CharField(max_length=50, blank=True)
    nickname = models.CharField(max_length=50)
    # rank removed
    
    reference_code = models.CharField(max_length=20, blank=True) # Future use?
    
    birthdate = models.DateField(null=True, blank=True)
    zodiac_sign = models.CharField(max_length=20, blank=True)
    
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Female')
    blood_type = models.CharField(max_length=10, choices=BLOOD_CHOICES, default='Unknown')
    
    birthplace = models.CharField(max_length=100, blank=True)
    
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    groups = models.ManyToManyField(TargetGroup, blank=True, related_name='targets')
    intel_depth = models.FloatField(default=0.0)
    last_contact = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nickname

class CustomAnniversary(models.Model):
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name='anniversaries')
    label = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.target} - {self.label}"

class TimelineItem(models.Model):
    TYPE_CHOICES = [
        ('EVENT', 'Event'),
        ('ANSWER', 'Answer'),
    ]
    SENTIMENT_CHOICES = [
        ('Positive', 'Positive'),
        ('Neutral', 'Neutral'),
        ('Negative', 'Negative'),
        ('Alert', 'Alert'),
    ]

    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name='timeline')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='EVENT')
    date = models.DateTimeField()
    content = models.TextField()
    related_quest = models.ForeignKey(Quest, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='Neutral')

    def __str__(self):
        return f"{self.target} - {self.type} ({self.date.strftime('%Y-%m-%d')})"
