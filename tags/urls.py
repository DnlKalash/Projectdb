from django.urls import path
from . import views

app_name = "tags"  # <- это важно для namespace 'tags'

urlpatterns = [
    path('', views.tags_list, name='list_tags'),            # Список всех тегов
    path('create/', views.tag_create_view, name='create_tag'),  # Создание тега
    path('<int:tag_id>/', views.tag_detail_view, name='tag_detail'),  # Детали тега
    path('<int:tag_id>/delete/', views.tag_delete_view, name='delete_tag'),  # Удаление тега
    path('<int:tag_id>/update/', views.tag_update_view, name='update_tag'),
]
