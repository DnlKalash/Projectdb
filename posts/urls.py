from django.urls import path
from django.views.generic import RedirectView
from . import views
from comments import views as comments_views

app_name = 'posts'

urlpatterns = [
    path('', views.posts_list_page, name='posts-list-page'),
    path('create/', views.post_create_page, name='post-create-page'),
    path('tags/', RedirectView.as_view(url='/tags/', permanent=False), name='tags-redirect'),
    path('tag/<str:tag_name>/', views.posts_by_tag_page, name='posts-by-tag-page'),
    path('<int:post_id>/', views.post_detail_page, name='post-detail-page'),  # Теперь с комментариями
    path('<int:post_id>/delete/', views.post_delete_page, name='post-delete-page'),
    path('<int:post_id>/add-tag/', views.add_tag_to_post_view, name='add-tag'),
    path('<int:post_id>/remove-tag/<str:tag_name>/', views.remove_tag_from_post_view, name='remove-tag'),
    
    
    path('<int:post_id>/comment/', comments_views.add_comment_view, name='add-comment'),
    path('<int:post_id>/comment/<int:parent_id>/', comments_views.add_comment_view, name='add-comment'),
]