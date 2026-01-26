from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.views import jwt_required
from .sql_posts import (
    init_posts_table,
    get_all_posts,
    get_post_by_id,
    create_post,
    delete_post
)

# Создаём таблицу при старте
init_posts_table()

# ======================
# LIST
# ======================
def posts_list_page(request):
    posts = get_all_posts()
    return render(request, "posts/posts_list.html", {
        "posts": posts
    })


# ======================
# DETAIL
# ======================
def post_detail_page(request, post_id):
    post = get_post_by_id(post_id)
    if not post:
        return render(request, "posts/post_not_found.html", status=404)

    return render(request, "posts/post_detail.html", {
        "post": post
    })


# ======================
# CREATE
# ======================
@jwt_required
@require_http_methods(["GET", "POST"])
def post_create_page(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        author_id = request.user_id  # берём из JWT декоратора

        if title and content:
            create_post(title, content, author_id)
            return redirect("posts:posts-list-page")

    return render(request, "posts/post_create.html")



# ======================
# DELETE
# ======================
@jwt_required
@require_http_methods(["POST"])
def post_delete_page(request, post_id):
    delete_post(post_id)
    # namespace исправлен
    return redirect("posts:posts-list-page")
