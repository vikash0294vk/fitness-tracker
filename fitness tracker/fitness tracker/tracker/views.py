import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Sum
from django.forms import inlineformset_factory
from django import forms
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    CardioSessionForm,
    FoodItemFormSet,
    GoalForm,
    GoalProgressForm,
    HydrationForm,
    HydrationQuickAddForm,
    MealForm,
    MeasurementForm,
    TemplateExerciseFormSet,
    WorkoutForm,
    WorkoutSetFormSet,
    WorkoutTemplateForm,
)
from .models import (
    CardioSession,
    Comment,
    Goal,
    HydrationLog,
    Kudo,
    Meal,
    Measurement,
    PersonalRecord,
    TemplateExercise,
    Workout,
    WorkoutSet,
    WorkoutTemplate,
)


def queue_activity_celebration(request, *, title, detail, icon):
    request.session['activity_celebration'] = {
        'title': title,
        'detail': detail,
        'icon': icon,
    }


def check_and_update_pr(user, workout):
    # Load workout sets with exercises once so PR checks stay efficient.
    workout_sets = workout.sets.select_related('exercise').all()
    existing_prs = {
        pr.exercise_id: pr
        for pr in PersonalRecord.objects.filter(
            user=user,
            exercise_id__in=workout_sets.values_list('exercise_id', flat=True),
        ).select_related('exercise')
    }
    new_prs = []

    # Compare each set against the current PR and create or update records as needed.
    for workout_set in workout_sets:
        personal_record = existing_prs.get(workout_set.exercise_id)
        if personal_record is None:
            existing_prs[workout_set.exercise_id] = PersonalRecord.objects.create(
                user=user,
                exercise=workout_set.exercise,
                max_weight=workout_set.weight,
                reps_at_max=workout_set.reps,
                achieved_on=workout.date,
            )
            continue

        if workout_set.weight > personal_record.max_weight:
            personal_record.max_weight = workout_set.weight
            personal_record.reps_at_max = workout_set.reps
            personal_record.achieved_on = workout.date
            personal_record.save(update_fields=['max_weight', 'reps_at_max', 'achieved_on'])
            new_prs.append(workout_set.exercise.name)

    return new_prs


def build_template_workout_formset(data=None, instance=None, initial=None):
    # Match the form count to the template size so all exercises appear on first load.
    extra_forms = max(len(initial or []), 3)
    template_formset_class = inlineformset_factory(
        Workout,
        WorkoutSet,
        fields=('exercise', 'reps', 'weight'),
        extra=extra_forms,
        can_delete=False,
    )

    # Keep Bootstrap classes on the dynamic formset widgets.
    for field_name, field in template_formset_class.form.base_fields.items():
        if not isinstance(field.widget, forms.HiddenInput):
            field.widget.attrs['class'] = 'form-control'

    return template_formset_class(data=data, instance=instance, initial=initial)


@login_required
def dashboard(request):
    today = date.today()
    week_start = today - timedelta(days=6)

    # Gather the user's workout and cardio summary for today and the current week.
    workouts_today = Workout.objects.filter(user=request.user, date=today).count()
    total_minutes_this_week = Workout.objects.filter(
        user=request.user,
        date__gte=week_start,
        duration_minutes__isnull=False,
    ).aggregate(total_minutes=Sum('duration_minutes'))['total_minutes'] or 0
    cardio_today = CardioSession.objects.filter(user=request.user, date=today)
    cardio_this_week = CardioSession.objects.filter(user=request.user, date__gte=week_start).count()
    walks_this_week = CardioSession.objects.filter(
        user=request.user,
        activity_type='walking',
        date__gte=week_start,
    )
    walk_minutes_this_week = walks_this_week.aggregate(total_minutes=Sum('duration_minutes'))['total_minutes'] or 0
    walk_distance_this_week = walks_this_week.aggregate(total_distance=Sum('distance_km'))['total_distance'] or 0
    recent_walks = CardioSession.objects.filter(
        user=request.user,
        activity_type='walking',
    ).order_by('-date', '-id')[:3]

    # Pull today's meals and the latest health tracking records.
    meals_today = Meal.objects.filter(user=request.user, date=today).prefetch_related('food_items')
    calories_today = sum(meal.total_calories for meal in meals_today)
    goal = Goal.objects.filter(user=request.user).first()
    active_goals = Goal.objects.filter(user=request.user, is_active=True).order_by('-start_date', '-id')[:5]
    measurement = Measurement.objects.filter(user=request.user).order_by('-date').first()
    hydration_log, _ = HydrationLog.objects.get_or_create(user=request.user, date=today)
    personal_records = PersonalRecord.objects.filter(user=request.user).select_related('exercise').order_by('-achieved_on')[:5]

    progress = "N/A"
    if goal and goal.target_weight and measurement:
        diff = measurement.weight - goal.target_weight
        if diff > 0:
            progress = f"{diff:.1f} kg to lose"
        elif diff < 0:
            progress = f"{abs(diff):.1f} kg to gain"
        else:
            progress = "Goal met!"

    # Build the social feed with related workout, set, comment, and kudo data.
    from itertools import chain
    following_users = list(request.user.following.values_list('followed', flat=True))
    feed_users = following_users + [request.user.id]

    recent_workouts = list(Workout.objects.filter(
        user__in=feed_users
    ).select_related('user').prefetch_related(
        Prefetch('sets', queryset=WorkoutSet.objects.select_related('exercise')),
        Prefetch('comments', queryset=Comment.objects.select_related('user')),
        'kudos',
    )[:15])

    recent_cardio = list(CardioSession.objects.filter(
        user__in=feed_users
    ).select_related('user')[:15])

    for w in recent_workouts:
        w.is_cardio = False
    for c in recent_cardio:
        c.is_cardio = True

    # Sort combined activities by date descending (and id descending to keep it somewhat stable)
    recent_activities = sorted(
        chain(recent_workouts, recent_cardio),
        key=lambda x: (x.date, x.id),
        reverse=True
    )[:15]

    # Compute the top athletes leaderboard across the app.
    User = get_user_model()
    top_athletes = User.objects.annotate(
        workout_count=Count('workouts')
    ).filter(workout_count__gt=0).order_by('-workout_count')[:5]

    # Calculate the user's workout streak based on distinct workout dates.
    workouts_dates = Workout.objects.filter(user=request.user).order_by('-date').values_list('date', flat=True).distinct()
    streak = 0
    if workouts_dates:
        check_date = today
        if workouts_dates[0] == today or workouts_dates[0] == today - timedelta(days=1):
            check_date = workouts_dates[0]
            for workout_date in workouts_dates:
                if workout_date == check_date:
                    streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break

    # Serialize weight history for the dashboard chart.
    measurements = Measurement.objects.filter(user=request.user).order_by('date')
    history_data = [{'date': measurement.date.strftime('%Y-%m-%d'), 'weight': measurement.weight} for measurement in measurements]
    weight_history_json = json.dumps(history_data)

    context = {
        'workouts_today': workouts_today,
        'calories_today': calories_today,
        'progress': progress,
        'recent_activities': recent_activities,
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
        'total_minutes_this_week': total_minutes_this_week,
        'cardio_today': cardio_today,
        'cardio_this_week': cardio_this_week,
        'walk_sessions_this_week': walks_this_week.count(),
        'walk_minutes_this_week': walk_minutes_this_week,
        'walk_distance_this_week': walk_distance_this_week,
        'recent_walks': recent_walks,
        'personal_records': personal_records,
        'celebration': request.session.pop('activity_celebration', None),
        # Dashboard display note: Total Training Time This Week: {{ total_minutes_this_week }} mins
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
            # Save the workout first so the inline set entries can be attached to it.
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()

            # Save workout sets and then evaluate whether any new PRs were hit.
            formset.instance = workout
            formset.save()
            new_prs = check_and_update_pr(request.user, workout)

            messages.success(request, 'Workout logged successfully!')
            if new_prs:
                messages.success(request, f"🏆 New Personal Record(s): {', '.join(new_prs)}")
            queue_activity_celebration(
                request,
                title='Kudos, nice workout!',
                detail='Your workout is in the feed and ready for more kudos.',
                icon='fa-dumbbell',
            )
            return redirect('dashboard')
    else:
        form = WorkoutForm()
        formset = WorkoutSetFormSet()

    context = {'form': form, 'formset': formset, 'title': 'Log Workout'}
    return render(request, 'tracker/log_form.html', context)


@login_required
def log_cardio(request):
    if request.method == 'POST':
        form = CardioSessionForm(request.POST)
        if form.is_valid():
            # Attach the cardio session to the logged-in user before saving.
            cardio_session = form.save(commit=False)
            cardio_session.user = request.user
            cardio_session.save()
            is_walk = cardio_session.activity_type == 'walking'
            messages.success(request, 'Walk logged successfully!' if is_walk else 'Cardio session logged successfully!')
            queue_activity_celebration(
                request,
                title='Kudos, nice walk!' if is_walk else 'Kudos, nice workout!',
                detail='Your walk is now part of your weekly progress.' if is_walk else 'Your cardio session is in the feed and ready for more kudos.',
                icon='fa-shoe-prints' if is_walk else 'fa-bolt',
            )
            return redirect('dashboard')
    else:
        initial_activity = request.GET.get('activity_type')
        valid_choices = {choice[0] for choice in CardioSession.ACTIVITY_CHOICES}
        initial = {'activity_type': initial_activity} if initial_activity in valid_choices else None
        form = CardioSessionForm(initial=initial)

    selected_activity = form.initial.get('activity_type')
    context = {
        'form': form,
        'title': 'Log Walk' if selected_activity == 'walking' else 'Log Cardio',
        'single_form': True,
        'show_route_builder': True,
    }
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
def all_personal_records(request):
    # Load all PRs with exercise data for the dedicated records page.
    personal_records = PersonalRecord.objects.filter(user=request.user).select_related('exercise').order_by('-achieved_on')
    return render(request, 'tracker/personal_records.html', {'personal_records': personal_records})


@login_required
def create_template(request):
    if request.method == 'POST':
        form = WorkoutTemplateForm(request.POST)
        formset = TemplateExerciseFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            # Save the template and attach it to the current user.
            template = form.save(commit=False)
            template.user = request.user
            template.save()

            # Save all template exercises after the parent template exists.
            formset.instance = template
            formset.save()
            messages.success(request, 'Workout template created successfully!')
            return redirect('my_templates')
    else:
        form = WorkoutTemplateForm()
        formset = TemplateExerciseFormSet()

    context = {'form': form, 'formset': formset, 'title': 'Create Workout Template'}
    return render(request, 'tracker/log_form.html', context)


@login_required
def my_templates(request):
    # Prefetch nested exercise records so the template list renders without extra queries.
    templates = WorkoutTemplate.objects.filter(user=request.user).prefetch_related(
        Prefetch('exercises', queryset=TemplateExercise.objects.select_related('exercise'))
    )
    return render(request, 'tracker/my_templates.html', {'templates': templates})


@login_required
def use_template(request, template_id):
    template = get_object_or_404(
        WorkoutTemplate.objects.prefetch_related(
            Prefetch('exercises', queryset=TemplateExercise.objects.select_related('exercise'))
        ),
        id=template_id,
        user=request.user,
    )

    if request.method == 'POST':
        form = WorkoutForm(request.POST, request.FILES)
        formset = build_template_workout_formset(data=request.POST, instance=Workout())
        if form.is_valid() and formset.is_valid():
            # Save the workout first, then persist the generated sets from the template.
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()

            formset.instance = workout
            formset.save()
            new_prs = check_and_update_pr(request.user, workout)

            messages.success(request, 'Workout logged successfully!')
            if new_prs:
                messages.success(request, f"🏆 New Personal Record(s): {', '.join(new_prs)}")
            queue_activity_celebration(
                request,
                title='Kudos, nice workout!',
                detail='Your workout is in the feed and ready for more kudos.',
                icon='fa-dumbbell',
            )
            return redirect('dashboard')
    else:
        # Expand each template exercise into workout sets so the user can tweak before saving.
        initial_sets = []
        for template_exercise in template.exercises.all():
            for _ in range(template_exercise.sets):
                initial_sets.append({
                    'exercise': template_exercise.exercise,
                    'reps': template_exercise.reps,
                    'weight': template_exercise.weight,
                })

        form = WorkoutForm(initial={'notes': template.description})
        formset = build_template_workout_formset(instance=Workout(), initial=initial_sets)

    context = {
        'form': form,
        'formset': formset,
        'title': f'Use Template: {template.name}',
        'template': template,
    }
    return render(request, 'tracker/log_form.html', context)


@login_required
@require_POST
def delete_template(request, template_id):
    # Only allow owners to delete their own workout templates.
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)
    template_name = template.name
    template.delete()
    messages.success(request, f'Template "{template_name}" deleted successfully!')
    return redirect('my_templates')


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
            # If the kudo already existed, the user is un-liking the workout.
            kudo.delete()
            liked = False
        else:
            liked = True

        kudo_count = workout.kudos.count()
        return JsonResponse({"liked": liked, "count": kudo_count})

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def edit_workout(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    EditSetFormSet = inlineformset_factory(
        Workout,
        WorkoutSet,
        fields=('exercise', 'reps', 'weight'),
        extra=1,
        can_delete=True,
    )

    for field_name, field in EditSetFormSet.form.base_fields.items():
        if isinstance(field.widget, forms.HiddenInput):
            continue
        field.widget.attrs['class'] = 'form-control'

    if request.method == 'POST':
        form = WorkoutForm(request.POST, request.FILES, instance=workout)
        formset = EditSetFormSet(request.POST, instance=workout)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            check_and_update_pr(request.user, workout)
            messages.success(request, 'Workout updated!')
            return redirect('dashboard')
    else:
        form = WorkoutForm(instance=workout)
        formset = EditSetFormSet(instance=workout)

    context = {
        'form': form,
        'formset': formset,
        'title': 'Edit Workout',
        'editing': True,
    }
    return render(request, 'tracker/log_form.html', context)


@login_required
@require_POST
def delete_workout(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    workout.delete()
    messages.success(request, 'Workout deleted.')
    return redirect('dashboard')


@login_required
def edit_cardio(request, cardio_id):
    cardio = get_object_or_404(CardioSession, id=cardio_id, user=request.user)

    if request.method == 'POST':
        form = CardioSessionForm(request.POST, instance=cardio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cardio session updated!')
            return redirect('dashboard')
    else:
        form = CardioSessionForm(instance=cardio)

    context = {
        'form': form,
        'title': 'Edit Cardio Session',
        'single_form': True,
        'show_route_builder': True,
    }
    return render(request, 'tracker/log_form.html', context)


@login_required
@require_POST
def delete_cardio(request, cardio_id):
    cardio = get_object_or_404(CardioSession, id=cardio_id, user=request.user)
    cardio.delete()
    messages.success(request, 'Cardio session deleted.')
    return redirect('dashboard')


@login_required
def workout_history(request):
    workouts = Workout.objects.filter(user=request.user).prefetch_related('sets__exercise').order_by('-date')
    cardio_sessions = CardioSession.objects.filter(user=request.user).order_by('-date')[:10]
    paginator = Paginator(workouts, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        'tracker/workout_history.html',
        {
            'page_obj': page_obj,
            'cardio_sessions': cardio_sessions,
        },
    )


@login_required
@require_POST
def toggle_goal_active(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    goal.is_active = not goal.is_active
    goal.save()
    status = 'resumed' if goal.is_active else 'paused'
    messages.success(request, f'Goal "{goal.title or "Untitled"}" {status}.')
    return redirect('goals_page')


@login_required
def add_comment(request, workout_id):
    if request.method == "POST":
        workout = get_object_or_404(Workout, id=workout_id)

        try:
            data = json.loads(request.body)
            text = data.get("text", "").strip()
        except Exception:
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
