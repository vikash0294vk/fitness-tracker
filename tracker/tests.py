from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date
from tracker.models import CardioSession, Exercise, Workout, WorkoutSet, Meal, FoodItem, Goal, HydrationLog

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


class DurationFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='durationuser', password='password')
        self.client.login(username='durationuser', password='password')
        self.exercise = Exercise.objects.create(name='Deadlift')

    def test_log_workout_saves_duration_minutes(self):
        response = self.client.post(reverse('log_workout'), {
            'notes': 'Heavy pull day',
            'duration_minutes': 45,
            'sets-TOTAL_FORMS': 3,
            'sets-INITIAL_FORMS': 0,
            'sets-MIN_NUM_FORMS': 0,
            'sets-MAX_NUM_FORMS': 1000,
            'sets-0-exercise': self.exercise.id,
            'sets-0-reps': 5,
            'sets-0-weight': 140,
            'sets-1-exercise': '',
            'sets-1-reps': '',
            'sets-1-weight': '',
            'sets-2-exercise': '',
            'sets-2-reps': '',
            'sets-2-weight': '',
        })
        self.assertRedirects(response, reverse('dashboard'))
        workout = Workout.objects.get(user=self.user, notes='Heavy pull day')
        self.assertEqual(workout.duration_minutes, 45)

    def test_edit_workout_updates_duration_minutes(self):
        workout = Workout.objects.create(user=self.user, notes='Before edit', duration_minutes=30)
        workout_set = WorkoutSet.objects.create(
            workout=workout,
            exercise=self.exercise,
            reps=5,
            weight=120,
        )

        response = self.client.post(reverse('edit_workout', args=[workout.id]), {
            'notes': 'After edit',
            'duration_minutes': 50,
            'sets-TOTAL_FORMS': 2,
            'sets-INITIAL_FORMS': 1,
            'sets-MIN_NUM_FORMS': 0,
            'sets-MAX_NUM_FORMS': 1000,
            'sets-0-id': workout_set.id,
            'sets-0-workout': workout.id,
            'sets-0-exercise': self.exercise.id,
            'sets-0-reps': 4,
            'sets-0-weight': 145,
            'sets-1-id': '',
            'sets-1-workout': workout.id,
            'sets-1-exercise': '',
            'sets-1-reps': '',
            'sets-1-weight': '',
        })
        self.assertRedirects(response, reverse('dashboard'))
        workout.refresh_from_db()
        self.assertEqual(workout.duration_minutes, 50)

    def test_log_and_edit_cardio_save_duration_minutes(self):
        response = self.client.post(reverse('log_cardio'), {
            'activity_type': 'running',
            'duration_minutes': 30,
            'distance_km': 5,
            'avg_heart_rate': 150,
            'calories_burned': 300,
            'notes': 'Tempo run',
        })
        self.assertRedirects(response, reverse('dashboard'))
        cardio = CardioSession.objects.get(user=self.user, notes='Tempo run')
        self.assertEqual(cardio.duration_minutes, 30)

        edit_response = self.client.post(reverse('edit_cardio', args=[cardio.id]), {
            'activity_type': 'running',
            'duration_minutes': 35,
            'distance_km': 5.5,
            'avg_heart_rate': 152,
            'calories_burned': 330,
            'notes': 'Tempo run edited',
        })
        self.assertRedirects(edit_response, reverse('dashboard'))
        cardio.refresh_from_db()
        self.assertEqual(cardio.duration_minutes, 35)

    def test_workout_history_displays_workout_and_cardio_duration(self):
        workout = Workout.objects.create(user=self.user, notes='History workout', duration_minutes=40)
        WorkoutSet.objects.create(workout=workout, exercise=self.exercise, reps=6, weight=100)
        CardioSession.objects.create(
            user=self.user,
            activity_type='cycling',
            duration_minutes=25,
            notes='History cardio',
        )

        response = self.client.get(reverse('workout_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '40 mins')
        self.assertContains(response, '25 mins')
