from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('strava/connect/', views.connect_strava, name='connect_strava'),
    path('strava/callback/', views.strava_callback, name='strava_callback'),
    path('strava/sync/', views.sync_strava, name='sync_strava'),
    path('strava/activities/json/', views.strava_activities_json, name='strava_activities_json'),
    path('strava/disconnect/', views.disconnect_strava, name='disconnect_strava'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('community/', views.user_list, name='user_list'),
    path('community/groups/create/', views.create_group, name='create_group'),
    path('community/groups/<slug:slug>/', views.group_detail, name='group_detail'),
    path('community/groups/<slug:slug>/membership/', views.toggle_group_membership, name='toggle_group_membership'),
    path('community/follow/<int:user_id>/', views.toggle_follow, name='toggle_follow'),
]
