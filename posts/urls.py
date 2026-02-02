from django.urls import path
from django.views.generic import RedirectView
from . import views
from comments import views as comments_views

app_name = 'posts'

urlpatterns = [
    # =========================
    # Основные маршруты постов
    # =========================
    path('', views.posts_list_page, name='all-posts'),
    path('my/', views.my_posts_view, name='my-posts'),
    path('create/', views.post_create_page, name='post-create-page'),
    
    # =========================
    # НОВОЕ: Посты со статистикой
    # =========================
    path('stats/', views.posts_list_with_stats_page, name='posts-list-stats'),
    path('trending/', views.trending_posts_page, name='trending-posts'),
    
    # =========================
    # Теги
    # =========================
    path('tags/', RedirectView.as_view(url='/tags/', permanent=False), name='tags-redirect'),
    path('tag/<str:tag_name>/', views.posts_by_tag_page, name='posts-by-tag-page'),
    path('tag/<str:tag_name>/stats/', views.posts_by_tag_with_stats_page, name='posts-by-tag-stats'),  # НОВОЕ
    
    # =========================
    # Детали поста
    # =========================
    path('<int:post_id>/', views.post_detail_page, name='post-detail-page'),
    path('<int:post_id>/update/', views.post_update_page, name='post-update-page'),
    path('<int:post_id>/delete/', views.delete_post_view, name='post-delete-page'),
    
    # =========================
    # Управление тегами
    # =========================
    path('<int:post_id>/add-tag/', views.add_tag_to_post_view, name='add-tag'),
    path('<int:post_id>/remove-tag/<str:tag_name>/', views.remove_tag_from_post_view, name='remove-tag'),
    
    # =========================
    # Комментарии
    # =========================
    path('<int:post_id>/comment/', comments_views.add_comment_view, name='add-comment'),
    path('<int:post_id>/comment/<int:parent_id>/', comments_views.add_comment_view, name='add-comment'),
    path('<int:post_id>/comment/', comments_views.comment_delete_view, name='delete-comment'),
]