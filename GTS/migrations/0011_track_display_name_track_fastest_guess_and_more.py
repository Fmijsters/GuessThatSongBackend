# Generated by Django 4.2.4 on 2023-08-21 17:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("GTS", "0010_track_album_cover"),
    ]

    operations = [
        migrations.AddField(
            model_name="track",
            name="display_name",
            field=models.CharField(default="", max_length=256),
        ),
        migrations.AddField(
            model_name="track",
            name="fastest_guess",
            field=models.IntegerField(default=30000),
        ),
        migrations.AddField(
            model_name="track",
            name="fastest_guesser",
            field=models.ForeignKey(
                blank=True,
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
