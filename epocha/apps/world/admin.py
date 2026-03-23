from django.contrib import admin

from .models import EconomicTransaction, World, Zone

admin.site.register(World)
admin.site.register(Zone)
admin.site.register(EconomicTransaction)
