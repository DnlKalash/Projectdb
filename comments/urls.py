from django.urls import path
from . import views

app_name = 'comments'

urlpatterns = [
    
    path('post/<int:post_id>/comment/', views.add_comment_view, name='add-comment'),
    path('comment/<int:comment_id>/delete/<int:post_id>/', views.delete_comment_view, name='delete-comment'),
    
    path('post/<int:post_id>/comment/<int:parent_id>/', views.add_comment_view, name='add-comment'),
]