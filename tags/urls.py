from django.urls import path
from . import views  # Импортируем views из этого же приложения

urlpatterns = [
    path('', views.dummy_view, name='tags_dummy'),  # Список с хотя бы одной view
]
