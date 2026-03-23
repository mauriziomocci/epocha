from django.contrib import admin

from .models import Agent, DecisionLog, Group, Memory, Relationship

admin.site.register(Agent)
admin.site.register(Group)
admin.site.register(Memory)
admin.site.register(Relationship)
admin.site.register(DecisionLog)
