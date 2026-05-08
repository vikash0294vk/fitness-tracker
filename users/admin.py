from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'age', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Fitness Details', {'fields': ('age', 'height', 'weight', 'activity_level', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Fitness Details', {'fields': ('age', 'height', 'weight', 'activity_level', 'profile_picture')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
