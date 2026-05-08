from datetime import date

from django.db import migrations, models


def backfill_goal_start_dates(apps, schema_editor):
    Goal = apps.get_model('tracker', 'Goal')
    Goal.objects.filter(start_date__isnull=True).update(start_date=date.today())


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0010_workouttemplate_templateexercise'),
    ]

    operations = [
        migrations.RunPython(backfill_goal_start_dates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='goal',
            name='start_date',
            field=models.DateField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='cardiosession',
            name='date',
            field=models.DateField(default=date.today),
        ),
        migrations.AddField(
            model_name='cardiosession',
            name='strava_activity_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='cardiosession',
            constraint=models.UniqueConstraint(fields=('user', 'strava_activity_id'), name='unique_user_strava_activity'),
        ),
    ]
