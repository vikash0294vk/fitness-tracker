from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_fitnessgroup_groupmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='strava_access_token',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='customuser',
            name='strava_athlete_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='strava_last_sync_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='strava_refresh_token',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='customuser',
            name='strava_scopes',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='customuser',
            name='strava_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
