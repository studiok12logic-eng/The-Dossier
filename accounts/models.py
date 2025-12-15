from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # Role Constants
    MASTER = 'MASTER'
    ELITE_AGENT = 'ELITE_AGENT'
    AGENT = 'AGENT'
    
    ROLE_CHOICES = [
        (MASTER, 'Master (Admin)'),
        (ELITE_AGENT, 'Elite Agent'),
        (AGENT, 'Agent (Standard)'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=AGENT,
        verbose_name='階級'
    )

    def __str__(self):
        return f"{self.username} [{self.role}]"
