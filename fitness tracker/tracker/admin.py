from django.contrib import admin
from .models import Exercise, Workout, WorkoutSet, Meal, FoodItem, Goal, Measurement

admin.site.register(Exercise)
class WorkoutSetInline(admin.TabularInline):
    model = WorkoutSet
    extra = 1

class WorkoutAdmin(admin.ModelAdmin):
    inlines = [WorkoutSetInline]
    list_display = ['user', 'date']

admin.site.register(Workout, WorkoutAdmin)

class FoodItemInline(admin.TabularInline):
    model = FoodItem
    extra = 1

class MealAdmin(admin.ModelAdmin):
    inlines = [FoodItemInline]
    list_display = ['user', 'date', 'meal_type']

admin.site.register(Meal, MealAdmin)
admin.site.register(Goal)
admin.site.register(Measurement)
