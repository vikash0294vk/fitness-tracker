from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('goals/', views.goals_page, name='goals_page'),
    path('workout/log/', views.log_workout, name='log_workout'),
    path('meal/log/', views.log_meal, name='log_meal'),
    path('measurement/log/', views.log_measurement, name='log_measurement'),
    path('goals/create/', views.create_goal, name='create_goal'),
    path('goals/<int:goal_id>/progress/', views.update_goal_progress, name='update_goal_progress'),
    path('hydration/log/', views.log_hydration, name='log_hydration'),
    path('hydration/quick-add/', views.quick_add_hydration, name='quick_add_hydration'),
    
    
    path('workout/<int:workout_id>/kudo/', views.toggle_kudo, name='toggle_kudo'),
    path('workout/<int:workout_id>/comment/', views.add_comment, name='add_comment'),
]
