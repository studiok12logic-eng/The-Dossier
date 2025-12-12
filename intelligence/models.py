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
    RANK_CHOICES = [
        ('S', 'S'), ('A', 'A'), ('B', 'B'), ('C', 'C'),
        ('Taboo', 'Taboo'), ('System', 'System'),
    ]
    GENDER_CHOICES = [
        ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other'),
    ]
    BLOOD_CHOICES = [
        ('A', 'A'), ('B', 'B'), ('O', 'O'), ('AB', 'AB'), ('Unknown', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50)
    rank = models.CharField(max_length=10, choices=RANK_CHOICES, default='C')
    
    aliases = models.CharField(max_length=200, blank=True)
    birthdate = models.DateField(null=True, blank=True)
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
