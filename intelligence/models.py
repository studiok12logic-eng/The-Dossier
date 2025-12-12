from django.db import models
import uuid

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Quest(models.Model):
    text = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    difficulty = models.IntegerField(default=1)

    def __str__(self):
        return self.text

class Target(models.Model):
    RANK_CHOICES = [] # Removed
    GENDER_CHOICES = [
        ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other'),
    ]
    BLOOD_CHOICES = [
        ('A', 'A'), ('B', 'B'), ('O', 'O'), ('AB', 'AB'), ('Unknown', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_name = models.CharField(max_length=50, blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name_kana = models.CharField(max_length=50, blank=True)
    first_name_kana = models.CharField(max_length=50, blank=True)
    nickname = models.CharField(max_length=50)
    # rank removed
    
    aliases = models.CharField(max_length=200, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    zodiac_sign = models.CharField(max_length=20, blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Female')
    blood_type = models.CharField(max_length=10, choices=BLOOD_CHOICES, default='Unknown')
    origin = models.CharField(max_length=100, blank=True)
    
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
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
