from django.urls import path
from . import views

urlpatterns = [
    # Главная страница / пользователи (главный шаблон)
    path('', views.htmlshablon, name='htmlshablon'),

    # Регистрация
    path('register/', views.register, name='register'),

    # Логин
    path('login/', views.login, name='login'),

    # Логаут (POST только)
    path('logout/', views.logout, name='logout'),
]
