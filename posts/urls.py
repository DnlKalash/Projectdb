from django.urls import path
from .views import (
    posts_list_page,
    post_detail_page,
    post_create_page,
    post_delete_page
)

app_name = "posts"  # обязательно для namespace

urlpatterns = [
    path("", posts_list_page, name="posts-list-page"),               # /posts/
    path("create/", post_create_page, name="post-create-page"),      # /posts/create/
    path("<int:post_id>/", post_detail_page, name="post-detail-page"),  # /posts/<id>/
    path("<int:post_id>/delete/", post_delete_page, name="post-delete-page"),  # /posts/<id>/delete/
]
