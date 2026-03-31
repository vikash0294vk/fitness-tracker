from django import forms
from django.forms import inlineformset_factory
from .models import Workout, WorkoutSet, Meal, FoodItem, Measurement, Goal, HydrationLog

class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['notes', 'image']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

WorkoutSetFormSet = inlineformset_factory(
    Workout, WorkoutSet, fields=('exercise', 'reps', 'weight'),
    extra=3, can_delete=False
)

class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['meal_type']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
        }

FoodItemFormSet = inlineformset_factory(
    Meal, FoodItem, fields=('name', 'calories', 'protein', 'carbs', 'fats'),
    extra=5, can_delete=False
)

class MeasurementForm(forms.ModelForm):
    class Meta:
        model = Measurement
        fields = ['weight', 'body_fat_percentage']
        widgets = {
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'body_fat_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = [
            'title',
            'description',
            'category',
            'period',
            'target_value',
            'unit',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: 5 workouts this week'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Why this goal matters'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'target_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'workouts, km, sessions'}),
        }


class GoalProgressForm(forms.Form):
    goal_id = forms.IntegerField(widget=forms.HiddenInput())
    increment = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))


class HydrationForm(forms.ModelForm):
    amount = forms.FloatField(
        min_value=0.1,
        initial=0.25,
        help_text="Amount of water you drank in litres.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0.1'})
    )

    class Meta:
        model = HydrationLog
        fields = ['target_litres']
        widgets = {
            'target_litres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0.5'}),
        }


class HydrationQuickAddForm(forms.Form):
    amount = forms.FloatField(min_value=0.1)
