import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
from .forms import FitnessGroupForm, GroupMessageForm, UserRegisterForm, UserUpdateForm
from .models import CustomUser, FitnessGroup, GroupMessage, UserFollow
from . import strava
from tracker.models import Workout

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if u_form.is_valid():
            u_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        
    # Calculate Streak
    today = timezone.now().date()
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
    
    context = {
        'u_form': u_form,
        'streak': streak,
        'strava_configured': strava.is_configured(),
        'strava_connected': bool(request.user.strava_refresh_token),
        'strava_has_read_scope': strava.has_read_scope(request.user.strava_scopes),
    }
    return render(request, 'users/profile.html', context)


@login_required
def connect_strava(request):
    if not strava.is_configured():
        messages.error(request, 'Add your Strava client ID and client secret to enable this connection.')
        return redirect('profile')

    state = secrets.token_urlsafe(24)
    request.session['strava_oauth_state'] = state
    redirect_uri = request.build_absolute_uri(reverse('strava_callback'))

    try:
        authorize_url = strava.build_authorization_url(redirect_uri, state)
    except strava.StravaError as exc:
        messages.error(request, str(exc))
        return redirect('profile')

    return redirect(authorize_url)


@login_required
def strava_callback(request):
    if request.GET.get('error') == 'access_denied':
        messages.info(request, 'Strava connection was canceled.')
        return redirect('profile')

    expected_state = request.session.pop('strava_oauth_state', '')
    returned_state = request.GET.get('state', '')
    if not expected_state or expected_state != returned_state:
        messages.error(request, 'Strava login could not be verified. Please try again.')
        return redirect('profile')

    code = request.GET.get('code', '')
    accepted_scopes = request.GET.get('scope', '')
    if not code:
        messages.error(request, 'Strava did not return an authorization code.')
        return redirect('profile')
    if not strava.has_read_scope(accepted_scopes):
        messages.error(request, 'Strava needs activity read access before this app can import your workouts.')
        return redirect('profile')

    try:
        strava.exchange_code_for_token(
            request.user,
            code=code,
            redirect_uri=request.build_absolute_uri(reverse('strava_callback')),
            accepted_scopes=accepted_scopes,
        )
        sync_result = strava.sync_recent_activities(request.user)
    except strava.StravaError as exc:
        messages.error(request, str(exc))
        return redirect('profile')

    messages.success(request, 'Strava connected successfully.')
    if sync_result['created'] or sync_result['updated']:
        messages.success(
            request,
            f"Imported {sync_result['created']} new activities and updated {sync_result['updated']} existing ones."
        )
    else:
        messages.info(request, 'Connection worked, but there were no recent Strava activities to import.')
    return redirect('profile')


@login_required
@require_POST
def sync_strava(request):
    try:
        sync_result = strava.sync_recent_activities(request.user)
    except strava.StravaError as exc:
        messages.error(request, str(exc))
        return redirect('profile')

    if sync_result['created'] or sync_result['updated']:
        messages.success(
            request,
            f"Strava sync complete: {sync_result['created']} new and {sync_result['updated']} updated."
        )
    else:
        messages.info(request, 'Strava sync complete. No new activities were found.')
    return redirect('profile')


@login_required
def strava_activities_json(request):
    """
    Returns the user's recent Strava activities as a JSON response.
    """
    try:
        activities = strava.fetch_activities(request.user)
        return JsonResponse({'activities': activities})
    except strava.StravaError as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@login_required
@require_POST
def disconnect_strava(request):
    strava.revoke_access(request.user)
    messages.success(request, 'Strava has been disconnected from your profile.')
    return redirect('profile')

@login_required
def user_list(request):
    users = CustomUser.objects.exclude(id=request.user.id)
    following_ids = request.user.following.values_list('followed_id', flat=True)
    groups = FitnessGroup.objects.annotate(member_count=Count('members')).select_related('created_by')
    joined_group_ids = request.user.fitness_groups.values_list('id', flat=True)

    context = {
        'users': users,
        'following_ids': following_ids,
        'groups': groups,
        'joined_group_ids': joined_group_ids,
        'group_form': FitnessGroupForm(),
    }
    return render(request, 'users/user_list.html', context)


@login_required
def create_group(request):
    if request.method != 'POST':
        return redirect('user_list')

    form = FitnessGroupForm(request.POST)
    if form.is_valid():
        group = form.save(commit=False)
        group.created_by = request.user
        group.save()
        group.members.add(request.user)
        messages.success(request, f'Fitness group "{group.name}" created.')
        return redirect('group_detail', slug=group.slug)

    users = CustomUser.objects.exclude(id=request.user.id)
    following_ids = request.user.following.values_list('followed_id', flat=True)
    groups = FitnessGroup.objects.annotate(member_count=Count('members')).select_related('created_by')
    joined_group_ids = request.user.fitness_groups.values_list('id', flat=True)
    return render(request, 'users/user_list.html', {
        'users': users,
        'following_ids': following_ids,
        'groups': groups,
        'joined_group_ids': joined_group_ids,
        'group_form': form,
    })

@login_required
def toggle_follow(request, user_id):
    if request.method == "POST":
        target_user = get_object_or_404(CustomUser, id=user_id)
        
       
        if target_user == request.user:
            return JsonResponse({"error": "Cannot follow yourself"}, status=400)
            
        follow_record, created = UserFollow.objects.get_or_create(
            follower=request.user, 
            followed=target_user
        )
        
        if not created:
            # Already following, so unfollow
            follow_record.delete()
            is_following = False
        else:
            is_following = True
            
        return JsonResponse({
            "success": True, 
            "is_following": is_following,
            "follower_count": target_user.followers.count()
        })
        
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def toggle_group_membership(request, slug):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request"}, status=400)

    group = get_object_or_404(FitnessGroup, slug=slug)
    is_member = group.members.filter(id=request.user.id).exists()

    if is_member:
        if group.created_by_id == request.user.id:
            messages.error(request, 'Group creators cannot leave their own group.')
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"error": "Creator cannot leave group"}, status=400)
            return redirect('group_detail', slug=group.slug)
        group.members.remove(request.user)
        joined = False
        messages.success(request, f'You left {group.name}.')
    else:
        group.members.add(request.user)
        joined = True
        messages.success(request, f'You joined {group.name}.')

    member_count = group.members.count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "joined": joined,
            "member_count": member_count,
        })
    return redirect(request.POST.get('next') or 'user_list')


@login_required
def group_detail(request, slug):
    group = get_object_or_404(
        FitnessGroup.objects.select_related('created_by').prefetch_related('members', 'messages__user'),
        slug=slug,
    )
    is_member = group.members.filter(id=request.user.id).exists()

    if request.method == 'POST':
        if not is_member:
            messages.error(request, 'Join this fitness group to start chatting.')
            return redirect('group_detail', slug=group.slug)

        form = GroupMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.group = group
            message.user = request.user
            message.save()
            messages.success(request, 'Message sent to the group.')
            return redirect('group_detail', slug=group.slug)
    else:
        form = GroupMessageForm()

    context = {
        'group': group,
        'messages_list': group.messages.select_related('user').all(),
        'is_member': is_member,
        'message_form': form,
    }
    return render(request, 'users/group_detail.html', context)
