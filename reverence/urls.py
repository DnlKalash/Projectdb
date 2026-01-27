from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('users.urls')),
    path('client/', include('client.urls')),
    path('posts/', include(('posts.urls', 'posts'), namespace='posts')),
    path('tags/', include(('tags.urls', 'tags'), namespace='tags')),
    path('reactions/', include(('reactions.urls', 'reactions'), namespace='reactions')),
    path('', include(('comments.urls', 'comments'), namespace='comments'))
]