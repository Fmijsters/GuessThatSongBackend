# Generated by Django 4.2.4 on 2023-08-19 13:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("GTS", "0004_pub_members"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pub",
            name="type",
            field=models.CharField(
                choices=[("TP", "Typing Game"), ("MC", "Multiple Choice Game")],
                default="TP",
                max_length=2,
            ),
        ),
    ]