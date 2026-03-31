from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date
from tracker.models import Exercise, Workout, WorkoutSet, Meal, FoodItem, Goal, HydrationLog

User = get_user_model()

class TrackingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.exercise = Exercise.objects.create(name='Squat')
        
    def test_workout_creation(self):
        workout = Workout.objects.create(user=self.user, notes='Leg day')
        workout_set = WorkoutSet.objects.create(
            workout=workout, exercise=self.exercise, reps=10, weight=100
        )
        self.assertEqual(workout.sets.count(), 1)
        self.assertEqual(workout.sets.first().weight, 100)
        
    def test_meal_creation(self):
        meal = Meal.objects.create(user=self.user, meal_type='Breakfast')
        FoodItem.objects.create(meal=meal, name='Oats', calories=300)
        FoodItem.objects.create(meal=meal, name='Milk', calories=150)
        self.assertEqual(meal.food_items.count(), 2)
        self.assertEqual(meal.total_calories, 450)

    def test_goal_completion_percentage(self):
        goal = Goal.objects.create(
            user=self.user,
            title='Weekly workouts',
            category='fitness',
            period='weekly',
            target_value=5,
            current_value=3,
            unit='workouts',
        )
        self.assertEqual(goal.completion_percentage, 60)
        self.assertEqual(goal.remaining_value, 2)

    def test_hydration_log_percentage(self):
        hydration = HydrationLog.objects.create(
            user=self.user,
            target_litres=3,
            consumed_litres=1.5,
        )
        self.assertEqual(hydration.completion_percentage, 50)
        self.assertEqual(hydration.remaining_litres, 1.5)


class DashboardFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='goaluser', password='password')
        self.client.login(username='goaluser', password='password')

    def test_create_goal_from_dashboard(self):
        response = self.client.post(reverse('create_goal'), {
            'title': 'Drink more water',
            'description': 'Stay consistent this week',
            'category': 'hydration',
            'period': 'weekly',
            'target_value': 7,
            'unit': 'days',
        })
        self.assertRedirects(response, reverse('goals_page'))
        goal = Goal.objects.get(user=self.user)
        self.assertEqual(goal.title, 'Drink more water')
        self.assertEqual(goal.category, 'hydration')
        self.assertTrue(goal.accepted)

    def test_goals_page_loads(self):
        response = self.client.get(reverse('goals_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Goal')

    def test_log_hydration_updates_today_entry(self):
        response = self.client.post(reverse('log_hydration'), {
            'amount': 0.5,
            'target_litres': 2.5,
        })
        self.assertRedirects(response, reverse('dashboard'))
        hydration = HydrationLog.objects.get(user=self.user)
        self.assertEqual(hydration.target_litres, 2.5)
        self.assertEqual(hydration.consumed_litres, 0.5)

    def test_quick_add_hydration_updates_existing_entry(self):
        response = self.client.post(reverse('quick_add_hydration'), {
            'amount': 1.0,
            'target_litres': 3.5,
        })
        self.assertRedirects(response, reverse('dashboard'))
        hydration = HydrationLog.objects.get(user=self.user)
        self.assertEqual(hydration.target_litres, 3.5)
        self.assertEqual(hydration.consumed_litres, 1.0)

    def test_log_hydration_uses_local_date_existing_log(self):
        HydrationLog.objects.create(
            user=self.user,
            target_litres=3.0,
            consumed_litres=0.5,
        )
        response = self.client.post(reverse('log_hydration'), {
            'amount': 0.5,
            'target_litres': 3.0,
        })
        self.assertRedirects(response, reverse('dashboard'))
        hydration = HydrationLog.objects.get(user=self.user, date=date.today())
        self.assertEqual(hydration.consumed_litres, 1.0)
