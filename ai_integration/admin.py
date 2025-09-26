from django.contrib import admin
from .models import SensorReading, AIRecommendation  # Replace with actual model names

# Register your models here.
admin.site.register(SensorReading)
admin.site.register(AIRecommendation)