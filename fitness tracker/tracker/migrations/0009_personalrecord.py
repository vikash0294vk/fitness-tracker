from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0008_cardiosession'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_weight', models.FloatField()),
                ('reps_at_max', models.PositiveIntegerField()),
                ('achieved_on', models.DateField()),
                ('exercise', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='personal_records', to='tracker.exercise')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='personal_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-achieved_on'],
                'unique_together': {('user', 'exercise')},
            },
        ),
    ]
