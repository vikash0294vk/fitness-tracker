from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class CustomUser(AbstractUser):
    age = models.PositiveIntegerField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True, help_text="Height in cm")
    weight = models.FloatField(null=True, blank=True, help_text="Weight in kg")

    ACTIVITY_LEVEL_CHOICES = [
        ('Sedentary', 'Sedentary'),
        ('Lightly Active', 'Lightly Active'),
        ('Moderately Active', 'Moderately Active'),
        ('Very Active', 'Very Active'),
        ('Extra Active', 'Extra Active')
    ]
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_LEVEL_CHOICES, blank=True, null=True)

    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    strava_athlete_id = models.BigIntegerField(blank=True, null=True)
    strava_access_token = models.CharField(max_length=255, blank=True)
    strava_refresh_token = models.CharField(max_length=255, blank=True)
    strava_token_expires_at = models.DateTimeField(blank=True, null=True)
    strava_scopes = models.CharField(max_length=255, blank=True)
    strava_last_sync_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.username

class UserFollow(models.Model):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    followed = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'followed'], name='unique_follow')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"


class FitnessGroup(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_fitness_groups')
    members = models.ManyToManyField(CustomUser, related_name='fitness_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:130] or 'fitness-group'
            slug = base_slug
            suffix = 1
            while FitnessGroup.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    group = models.ForeignKey(FitnessGroup, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='group_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} in {self.group.name}'
