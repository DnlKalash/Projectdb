from django.urls import path
from . import views

app_name = 'comments'

urlpatterns = [
    # Добавить комментарий к посту (без parent_id)
    path('post/<int:post_id>/comment/', views.add_comment_view, name='add-comment'),
    
    # Добавить ответ на комментарий (с parent_id)
    path('post/<int:post_id>/comment/<int:parent_id>/', views.add_comment_view, name='add-reply'),
    
    # Удалить комментарий
    path('comment/<int:comment_id>/delete/<int:post_id>/', views.comment_delete_view, name='delete-comment'),
]