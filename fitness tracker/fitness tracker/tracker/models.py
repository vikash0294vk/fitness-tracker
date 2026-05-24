from datetime import date

from django.conf import settings
from django.db import models


# Exercise Dictionary Model
class Exercise(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    body_part = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


# Workout Session Model
class Workout(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workouts')
    date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='workout_images/', blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}"


# Workout Sets Models (Multiple sets per Workout)
class WorkoutSet(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='sets')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    reps = models.PositiveIntegerField()
    weight = models.FloatField()  # Could be in lbs or kg

    def __str__(self):
        return f"{self.exercise.name}: {self.reps}x{self.weight}"


class CardioSession(models.Model):
    ACTIVITY_CHOICES = [
        ('running', 'Running'),
        ('cycling', 'Cycling'),
        ('swimming', 'Swimming'),
        ('walking', 'Walking'),
        ('rowing', 'Rowing'),
        ('jump_rope', 'Jump Rope'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cardio_sessions')
    date = models.DateField(default=date.today)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    duration_minutes = models.PositiveIntegerField()
    distance_km = models.FloatField(blank=True, null=True)
    avg_heart_rate = models.PositiveIntegerField(blank=True, null=True)
    calories_burned = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    strava_activity_id = models.BigIntegerField(blank=True, null=True)
    map_polyline = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'strava_activity_id'],
                name='unique_user_strava_activity',
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} on {self.date}"

    @property
    def pace_per_km(self):
        """Returns pace as 'MM:SS /km' string, or None if distance not set."""
        if self.distance_km and self.distance_km > 0:
            total_seconds = (self.duration_minutes * 60) / self.distance_km
            mins = int(total_seconds // 60)
            secs = int(total_seconds % 60)
            return f"{mins}:{secs:02d} /km"
        return None


class PersonalRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_records')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='personal_records')
    max_weight = models.FloatField()
    reps_at_max = models.PositiveIntegerField()
    achieved_on = models.DateField()

    class Meta:
        unique_together = [['user', 'exercise']]
        ordering = ['-achieved_on']

    def __str__(self):
        return f"PR: {self.user.username} - {self.exercise.name}: {self.max_weight}kg x {self.reps_at_max}"


class WorkoutTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_templates')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s template: {self.name}"


class TemplateExercise(models.Model):
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sets = models.PositiveIntegerField(default=3)
    reps = models.PositiveIntegerField(default=10)
    weight = models.FloatField(default=0)

    def __str__(self):
        return f"{self.exercise.name}: {self.sets}x{self.reps} @ {self.weight}kg"


# Nutrition Meal Model
class Meal(models.Model):
    MEAL_TYPES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snack', 'Snack'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meals')
    date = models.DateField(auto_now_add=True)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.meal_type}"

    @property
    def total_calories(self):
        return sum(item.calories for item in self.food_items.all())


# Nutrition FoodItem Model
class FoodItem(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='food_items')
    name = models.CharField(max_length=100)
    calories = models.PositiveIntegerField()
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fats = models.FloatField(default=0)

    def __str__(self):
        return self.name


# Goal Tracking Model
class Goal(models.Model):
    CATEGORY_CHOICES = [
        ('fitness', 'Fitness'),
        ('nutrition', 'Nutrition'),
        ('hydration', 'Hydration'),
        ('wellness', 'Wellness'),
    ]

    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=120, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='fitness')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='weekly')
    target_value = models.PositiveIntegerField(blank=True, null=True)
    current_value = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=40, default='sessions')
    accepted = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    achieved = models.BooleanField(default=False)
    start_date = models.DateField(auto_now_add=True)
    target_weight = models.FloatField(blank=True, null=True)
    target_calories = models.PositiveIntegerField(default=2000)

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return self.title or f"{self.user.username}'s Goal"

    @property
    def completion_percentage(self):
        if not self.target_value:
            return 0
        return min(100, int((self.current_value / self.target_value) * 100))

    @property
    def remaining_value(self):
        if not self.target_value:
            return 0
        return max(self.target_value - self.current_value, 0)

    def save(self, *args, **kwargs):
        if self.target_value:
            self.achieved = self.current_value >= self.target_value
        super().save(*args, **kwargs)


class HydrationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hydration_logs')
    date = models.DateField(auto_now_add=True)
    target_litres = models.FloatField(default=3.0)
    consumed_litres = models.FloatField(default=0)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='unique_daily_hydration_log')
        ]

    def __str__(self):
        return f"{self.user.username} hydration on {self.date}"

    @property
    def completion_percentage(self):
        if self.target_litres <= 0:
            return 0
        return min(100, int((self.consumed_litres / self.target_litres) * 100))

    @property
    def remaining_litres(self):
        return max(self.target_litres - self.consumed_litres, 0)


# Measurement Logging Model
class Measurement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='measurements')
    date = models.DateField(auto_now_add=True)
    weight = models.FloatField()
    body_fat_percentage = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} on {self.date}: {self.weight}"


# Kudo Model (Likes on a workout)
class Kudo(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='kudos')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_kudos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workout', 'user'], name='unique_kudo')
        ]

    def __str__(self):
        return f"{self.user.username} liked {self.workout}"


# Comment Model
class Comment(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.workout}"
