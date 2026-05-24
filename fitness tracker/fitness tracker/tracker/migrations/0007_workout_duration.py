from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_goal_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='workout',
            name='duration_minutes',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
