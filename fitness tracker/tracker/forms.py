from django import forms
from django.forms import inlineformset_factory

from .models import (
    CardioSession,
    FoodItem,
    Goal,
    HydrationLog,
    Meal,
    Measurement,
    TemplateExercise,
    Workout,
    WorkoutSet,
    WorkoutTemplate,
)


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['notes', 'image', 'duration_minutes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }


WorkoutSetFormSet = inlineformset_factory(
    Workout,
    WorkoutSet,
    fields=('exercise', 'reps', 'weight'),
    extra=3,
    can_delete=False,
)


class CardioSessionForm(forms.ModelForm):
    class Meta:
        model = CardioSession
        fields = [
            'activity_type',
            'duration_minutes',
            'distance_km',
            'avg_heart_rate',
            'calories_burned',
            'notes',
            'map_polyline',
        ]
        widgets = {
            'activity_type': forms.Select(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'avg_heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'calories_burned': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control'}),
            'map_polyline': forms.HiddenInput(attrs={'id': 'id_map_polyline'}),
        }


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
    increment = forms.IntegerField(
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'placeholder': '+1 or -1'})
    )

    def clean_increment(self):
        increment = self.cleaned_data['increment']
        if increment == 0:
            raise forms.ValidationError('Enter a positive or negative number.')
        return increment


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


class WorkoutTemplateForm(forms.ModelForm):
    class Meta:
        model = WorkoutTemplate
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }


TemplateExerciseFormSet = inlineformset_factory(
    WorkoutTemplate,
    TemplateExercise,
    fields=('exercise', 'sets', 'reps', 'weight'),
    extra=3,
    can_delete=True,
)


for formset in (WorkoutSetFormSet, TemplateExerciseFormSet):
    for field_name, field in formset.form.base_fields.items():
        if isinstance(field.widget, forms.HiddenInput):
            continue
        if isinstance(field.widget, forms.Select):
            field.widget.attrs['class'] = 'form-select'
        else:
            field.widget.attrs['class'] = 'form-control'
