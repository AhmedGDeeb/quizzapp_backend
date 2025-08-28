from django.urls import path
from . import api

urlpatterns = [
    path('status/', api.status),
    # Add more app-specific URLs here
]