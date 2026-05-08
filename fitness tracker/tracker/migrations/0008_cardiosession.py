from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0007_workout_duration'),
    ]

    operations = [
        migrations.CreateModel(
            name='CardioSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(auto_now_add=True)),
                ('activity_type', models.CharField(choices=[('running', 'Running'), ('cycling', 'Cycling'), ('swimming', 'Swimming'), ('walking', 'Walking'), ('rowing', 'Rowing'), ('jump_rope', 'Jump Rope'), ('other', 'Other')], max_length=20)),
                ('duration_minutes', models.PositiveIntegerField()),
                ('distance_km', models.FloatField(blank=True, null=True)),
                ('avg_heart_rate', models.PositiveIntegerField(blank=True, null=True)),
                ('calories_burned', models.PositiveIntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='cardio_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
    ]
