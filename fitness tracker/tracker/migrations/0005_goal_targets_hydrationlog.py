from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_workout_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='goal',
            name='accepted',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='achieved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='goal',
            name='current_value',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='goal',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='period',
            field=models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], default='weekly', max_length=10),
        ),
        migrations.AddField(
            model_name='goal',
            name='start_date',
            field=models.DateField(auto_now_add=True, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='goal',
            name='target_value',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='title',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='unit',
            field=models.CharField(default='sessions', max_length=40),
        ),
        migrations.AlterModelOptions(
            name='goal',
            options={'ordering': ['-start_date', '-id']},
        ),
        migrations.CreateModel(
            name='HydrationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(auto_now_add=True)),
                ('target_litres', models.FloatField(default=3.0)),
                ('consumed_litres', models.FloatField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hydration_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date'],
                'constraints': [models.UniqueConstraint(fields=('user', 'date'), name='unique_daily_hydration_log')],
            },
        ),
    ]
