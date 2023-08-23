from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


# SUPERUSER
# admin
# admin
# Create your models here.

class Artist(models.Model):
    name = models.CharField(max_length=256)
    id = models.CharField(max_length=256, primary_key=True)

    def __str__(self):
        return self.name


class Track(models.Model):
    name = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256, default="")
    id = models.CharField(max_length=256, primary_key=True)
    album_cover = models.CharField(max_length=256, default="")
    preview_url = models.CharField(max_length=256)
    fastest_guess = models.IntegerField(default=30000)
    fastest_guesser = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, default=None, null=True)
    artists = models.ManyToManyField(Artist, related_name="songs", blank=True)

    def __str__(self):
        return self.name


class Pub(models.Model):
    class GameTypes(models.TextChoices):
        TYPING = 'TP', _('Typing Game')
        MULTIPLECHOICE = 'MC', _('Multiple Choice Game')

    name = models.CharField(max_length=64, unique=True)
    type = models.CharField(max_length=2, choices=GameTypes.choices, default=GameTypes.TYPING)
    teams = models.BooleanField(default=False)
    members = models.ManyToManyField(User, related_name="pubs", blank=True)
    max_members = models.IntegerField(default=12)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, default="")
    password = models.CharField(max_length=64, default=name)
    track_list = models.ManyToManyField(Track, related_name="pubs", blank=True)
    rounds = models.IntegerField(default=10)

    def __str__(self):
        return self.name
