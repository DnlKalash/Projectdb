from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('users.urls')),       # главная страница и auth
    path('client/', include('client.urls')),  # профили и client pages
    path('posts/', include(('posts.urls', 'posts'), namespace='posts')),  # <-- добавили namespace
    path('comments/', include('comments.urls')),
    path('tags/', include('tags.urls')),
]
