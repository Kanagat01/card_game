# Generated by Django 4.2.5 on 2023-09-22 21:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game_api', '0009_gamecard'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game_api.card')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cards', to='game_api.player')),
            ],
        ),
    ]
