from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegisterForm, UserUpdateForm
from .models import CustomUser, UserFollow
from tracker.models import Workout

def register(request):
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
        'streak': streak
    }
    return render(request, 'users/profile.html', context)

@login_required
def user_list(request):
   
    users = CustomUser.objects.exclude(id=request.user.id)
    
   
    following_ids = request.user.following.values_list('followed_id', flat=True)
    
    context = {
        'users': users,
        'following_ids': following_ids
    }
    return render(request, 'users/user_list.html', context)

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
