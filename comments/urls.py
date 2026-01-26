from django.urls import path
from . import views

urlpatterns = [
    path('', views.dummy_view, name='comments_dummy'),
]
