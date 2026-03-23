from django.contrib import admin

from .models import Event, Simulation

admin.site.register(Simulation)
admin.site.register(Event)
