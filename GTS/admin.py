from django.contrib import admin
from .models import Pub, Track, Artist

# Register your models here.
admin.site.register(Pub)
admin.site.register(Track)
admin.site.register(Artist)
