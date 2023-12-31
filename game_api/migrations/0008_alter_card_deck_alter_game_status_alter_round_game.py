# Generated by Django 4.2.5 on 2023-09-22 19:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game_api', '0007_alter_player_game'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='deck',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cards', to='game_api.deck'),
        ),
        migrations.AlterField(
            model_name='game',
            name='status',
            field=models.CharField(choices=[('WT', 'Waiting'), ('PL', 'Playing'), ('FN', 'Finished')], default='PL', max_length=2),
        ),
        migrations.AlterField(
            model_name='round',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rounds', to='game_api.game'),
        ),
    ]
