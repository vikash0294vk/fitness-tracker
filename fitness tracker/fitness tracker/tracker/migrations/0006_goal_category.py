from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_goal_targets_hydrationlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='goal',
            name='category',
            field=models.CharField(choices=[('fitness', 'Fitness'), ('nutrition', 'Nutrition'), ('hydration', 'Hydration'), ('wellness', 'Wellness')], default='fitness', max_length=20),
        ),
    ]
