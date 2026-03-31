from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from datetime import timedelta, date
from django.contrib.auth import get_user_model
from django.db.models import Count
from .models import Workout, Meal, Measurement, Goal, Kudo, Comment, HydrationLog
from .forms import (
    WorkoutForm,
    WorkoutSetFormSet,
    MealForm,
    FoodItemFormSet,
    MeasurementForm,
    GoalForm,
    GoalProgressForm,
    HydrationForm,
    HydrationQuickAddForm,
)

@login_required
def dashboard(request):
    today = date.today()
    
    # Workouts today
    workouts_today = Workout.objects.filter(user=request.user, date=today).count()
    
    # Calories today
    meals_today = Meal.objects.filter(user=request.user, date=today)
    calories_today = sum(meal.total_calories for meal in meals_today)
    
    # Latest Goal & Measurement
    goal = Goal.objects.filter(user=request.user).first()
    active_goals = Goal.objects.filter(user=request.user, is_active=True).order_by('-start_date', '-id')[:5]
    measurement = Measurement.objects.filter(user=request.user).order_by('-date').first()
    hydration_log, _ = HydrationLog.objects.get_or_create(user=request.user, date=today)
    
    progress = "N/A"
    if goal and goal.target_weight and measurement:
        diff = measurement.weight - goal.target_weight
        if diff > 0:
            progress = f"{diff:.1f} kg to lose"
        elif diff < 0:
            progress = f"{abs(diff):.1f} kg to gain"
        else:
            progress = "Goal met!"
            
    # Social Feed: Get workouts from the user AND users they are following
    following_users = request.user.following.values_list('followed', flat=True)
    recent_workouts = Workout.objects.filter(
        user__in=list(following_users) + [request.user.id]
    ).select_related('user').prefetch_related('sets', 'kudos', 'comments')[:15]
    
    # Top Athletes Leaderboard
    User = get_user_model()
    top_athletes = User.objects.annotate(
        workout_count=Count('workouts')
    ).filter(workout_count__gt=0).order_by('-workout_count')[:5]
    
    # Calculate Streak
    workouts_dates = Workout.objects.filter(user=request.user).order_by('-date').values_list('date', flat=True).distinct()
    streak = 0
    if workouts_dates:
        check_date = today
        if workouts_dates[0] == today or workouts_dates[0] == today - timedelta(days=1):
            check_date = workouts_dates[0]
            for w_date in workouts_dates:
                if w_date == check_date:
                    streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break

    # Weight History JSON for Chart
    measurements = Measurement.objects.filter(user=request.user).order_by('date')
    history_data = [{'date': m.date.strftime('%Y-%m-%d'), 'weight': m.weight} for m in measurements]
    weight_history_json = json.dumps(history_data)
    
    context = {
        'workouts_today': workouts_today,
        'calories_today': calories_today,
        'progress': progress,
        'recent_workouts': recent_workouts,
        'meals_today': meals_today,
        'top_athletes': top_athletes,
        'streak': streak,
        'weight_history_json': weight_history_json,
        'active_goals': active_goals,
        'goal_form': GoalForm(),
        'goal_progress_form': GoalProgressForm(),
        'hydration_form': HydrationForm(initial={'target_litres': hydration_log.target_litres}),
        'hydration_quick_amounts': [0.25, 0.5, 1.0],
        'hydration_log': hydration_log,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def goals_page(request):
    goals = Goal.objects.filter(user=request.user).order_by('-is_active', 'achieved', '-start_date', '-id')
    active_goals = [goal for goal in goals if goal.is_active and not goal.achieved]
    completed_goals = [goal for goal in goals if goal.achieved]
    paused_goals = [goal for goal in goals if not goal.is_active and not goal.achieved]

    context = {
        'goal_form': GoalForm(),
        'goal_progress_form': GoalProgressForm(),
        'active_goals': active_goals,
        'completed_goals': completed_goals,
        'paused_goals': paused_goals,
        'goal_stats': {
            'active': len(active_goals),
            'completed': len(completed_goals),
            'paused': len(paused_goals),
            'total': len(goals),
        }
    }
    return render(request, 'tracker/goals.html', context)

@login_required
def log_workout(request):
    if request.method == 'POST':
        form = WorkoutForm(request.POST, request.FILES)
        formset = WorkoutSetFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            
            formset.instance = workout
            formset.save()
            messages.success(request, 'Workout logged successfully!')
            return redirect('dashboard')
    else:
        form = WorkoutForm()
        formset = WorkoutSetFormSet()
        
    context = {'form': form, 'formset': formset, 'title': 'Log Workout'}
    return render(request, 'tracker/log_form.html', context)

@login_required
def log_meal(request):
    if request.method == 'POST':
        form = MealForm(request.POST)
        formset = FoodItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            meal = form.save(commit=False)
            meal.user = request.user
            meal.save()
            
            formset.instance = meal
            formset.save()
            messages.success(request, 'Meal logged successfully!')
            return redirect('dashboard')
    else:
        form = MealForm()
        formset = FoodItemFormSet()
        
    context = {'form': form, 'formset': formset, 'title': 'Log Meal'}
    return render(request, 'tracker/log_form.html', context)

@login_required
def log_measurement(request):
    if request.method == 'POST':
        form = MeasurementForm(request.POST)
        if form.is_valid():
            measurement = form.save(commit=False)
            measurement.user = request.user
            measurement.save()
            messages.success(request, 'Measurement logged successfully!')
            return redirect('dashboard')
    else:
        form = MeasurementForm()
        
    context = {'form': form, 'title': 'Log Measurement', 'single_form': True}
    return render(request, 'tracker/log_form.html', context)


@login_required
@require_POST
def create_goal(request):
    form = GoalForm(request.POST)
    if form.is_valid():
        goal = form.save(commit=False)
        goal.user = request.user
        goal.accepted = True
        goal.is_active = True
        goal.save()
        messages.success(request, 'Goal target created successfully.')
    else:
        messages.error(request, 'Please check your goal details and try again.')
    return redirect(request.POST.get('next') or 'goals_page')


@login_required
@require_POST
def update_goal_progress(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    form = GoalProgressForm(request.POST)
    if form.is_valid():
        increment = form.cleaned_data['increment']
        goal.current_value += increment
        if goal.target_value and goal.current_value >= goal.target_value:
            goal.achieved = True
            messages.success(request, f'Nice work. You achieved "{goal.title or "your goal"}".')
        else:
            messages.success(request, 'Goal progress updated.')
        goal.save()
    else:
        messages.error(request, 'Progress update was invalid.')
    return redirect(request.POST.get('next') or 'goals_page')


@login_required
@require_POST
def log_hydration(request):
    today = date.today()
    hydration_log, _ = HydrationLog.objects.get_or_create(user=request.user, date=today)
    form = HydrationForm(request.POST, instance=hydration_log)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        hydration_log = form.save(commit=False)
        hydration_log.user = request.user
        hydration_log.date = today
        hydration_log.consumed_litres += amount
        hydration_log.save()
        if hydration_log.consumed_litres >= hydration_log.target_litres:
            messages.success(request, 'Hydration target achieved for today.')
        else:
            messages.success(request, 'Water intake updated.')
    else:
        messages.error(request, 'Please enter a valid water amount.')
    return redirect('dashboard')


@login_required
@require_POST
def quick_add_hydration(request):
    today = date.today()
    hydration_log, _ = HydrationLog.objects.get_or_create(user=request.user, date=today)
    amount_form = HydrationQuickAddForm(request.POST)

    if amount_form.is_valid():
        amount = amount_form.cleaned_data['amount']
        target_value = request.POST.get('target_litres')

        if target_value:
            try:
                hydration_log.target_litres = float(target_value)
            except ValueError:
                pass

        hydration_log.consumed_litres += amount
        hydration_log.save()

        if hydration_log.consumed_litres >= hydration_log.target_litres:
            messages.success(request, 'Hydration target achieved for today.')
        else:
            messages.success(request, f'Added {amount:.2f}L of water.')
    else:
        messages.error(request, 'Quick add water amount was invalid.')

    return redirect('dashboard')


@login_required
def toggle_kudo(request, workout_id):
    if request.method == "POST":
        workout = get_object_or_404(Workout, id=workout_id)
        kudo, created = Kudo.objects.get_or_create(workout=workout, user=request.user)
        
        if not created:
            # If the kudo already existed, the user is un-liking the workout
            kudo.delete()
            liked = False
        else:
            liked = True
            
        kudo_count = workout.kudos.count()
        return JsonResponse({"liked": liked, "count": kudo_count})
        
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def add_comment(request, workout_id):
    if request.method == "POST":
        workout = get_object_or_404(Workout, id=workout_id)
        
        try:
            data = json.loads(request.body)
            text = data.get("text", "").strip()
        except:
            text = request.POST.get("text", "").strip()
            
        if text:
            comment = Comment.objects.create(workout=workout, user=request.user, text=text)
            return JsonResponse({
                "success": True,
                "comment": {
                    "username": comment.user.username,
                    "text": comment.text,
                    "created_at": comment.created_at.strftime("%b %d, %I:%M %p")
                },
                "count": workout.comments.count()
            })
            
    return JsonResponse({"error": "Invalid request or empty comment"}, status=400)
