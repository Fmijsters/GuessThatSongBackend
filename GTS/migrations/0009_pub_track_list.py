# Generated by Django 4.2.4 on 2023-08-20 14:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("GTS", "0008_artist_track"),
    ]

    operations = [
        migrations.AddField(
            model_name="pub",
            name="track_list",
            field=models.ManyToManyField(
                blank=True, related_name="pubs", to="GTS.track"
            ),
        ),
    ]
