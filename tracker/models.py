from django.db import models
from django.conf import settings

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
    
    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}"

# Workout Sets Models (Multiple sets per Workout)
class WorkoutSet(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='sets')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    reps = models.PositiveIntegerField()
    weight = models.FloatField() # Could be in lbs or kg
    
    def __str__(self):
        return f"{self.exercise.name}: {self.reps}x{self.weight}"

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
