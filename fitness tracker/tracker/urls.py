from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('goals/', views.goals_page, name='goals_page'),
    path('workout/log/', views.log_workout, name='log_workout'),
    path('workout/<int:workout_id>/edit/', views.edit_workout, name='edit_workout'),
    path('workout/<int:workout_id>/delete/', views.delete_workout, name='delete_workout'),
    path('cardio/log/', views.log_cardio, name='log_cardio'),
    path('cardio/<int:cardio_id>/edit/', views.edit_cardio, name='edit_cardio'),
    path('cardio/<int:cardio_id>/delete/', views.delete_cardio, name='delete_cardio'),
    path('meal/log/', views.log_meal, name='log_meal'),
    path('measurement/log/', views.log_measurement, name='log_measurement'),
    path('history/', views.workout_history, name='workout_history'),
    path('records/', views.all_personal_records, name='personal_records'),
    path('templates/', views.my_templates, name='my_templates'),
    path('templates/create/', views.create_template, name='create_template'),
    path('templates/<int:template_id>/use/', views.use_template, name='use_template'),
    path('templates/<int:template_id>/delete/', views.delete_template, name='delete_template'),
    path('goals/create/', views.create_goal, name='create_goal'),
    path('goals/<int:goal_id>/progress/', views.update_goal_progress, name='update_goal_progress'),
    path('goals/<int:goal_id>/toggle-active/', views.toggle_goal_active, name='toggle_goal_active'),
    path('hydration/log/', views.log_hydration, name='log_hydration'),
    path('hydration/quick-add/', views.quick_add_hydration, name='quick_add_hydration'),
    path('workout/<int:workout_id>/kudo/', views.toggle_kudo, name='toggle_kudo'),
    path('workout/<int:workout_id>/comment/', views.add_comment, name='add_comment'),
]
