from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum 

# Profile Model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mmr = models.IntegerField(default=1000)
    highest_mmr = models.IntegerField(default=1000)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    current_streak = models.IntegerField(default=0) 
    highest_streak = models.IntegerField(default=0)
    games_played = models.IntegerField(default=0)
    avg_accuracy = models.FloatField(default=0.0) 

    def __str__(self):
        return f"{self.user.username} - Lvl {self.level}"

# GameRecord Model
class GameRecord(models.Model):
    MODE_CHOICES = [
        ("zen", "Zen Mode"),
        ("timetrial", "Time Trial"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    topics = models.JSONField(default=list) 
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    score = models.IntegerField(default=0)
    duration = models.IntegerField(null=True, blank=True)
    difficulty = models.CharField(max_length=20, default="adaptive") 
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.total_questions > 0:
            self.accuracy = round((self.correct_answers / self.total_questions) * 100, 2)
        else:
            self.accuracy = 0.0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.mode} ({self.score} pts)"


class WordProblem(models.Model):
    TOPIC_CHOICES = [
        ('addition', 'Addition'),
        ('subtraction', 'Subtraction'),
        ('multiplication', 'Multiplication'),
        ('division', 'Division'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    question_text = models.TextField()
    answer = models.IntegerField()
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')

    def __str__(self):
        return f"[{self.topic}] {self.question_text[:30]}..."

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=GameRecord)
def update_profile_stats(sender, instance, created, **kwargs):

    if instance.user:
        profile = instance.user.profile        
        profile.games_played = GameRecord.objects.filter(user=instance.user).count()
        aggregates = GameRecord.objects.filter(user=instance.user).aggregate(
            total_correct=Sum('correct_answers'),
            total_attempted=Sum('total_questions')
        )        
        total_correct = aggregates['total_correct'] or 0
        total_attempted = aggregates['total_attempted'] or 0
        
        if total_attempted > 0:
            profile.avg_accuracy = round((total_correct / total_attempted) * 100, 2)
        else:
            profile.avg_accuracy = 0.0
            
        profile.save()