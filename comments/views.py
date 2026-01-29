from django.shortcuts import render, redirect
from posts import sql_posts
from comments import sql_comments
from users.views import jwt_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import connection


@jwt_required
def add_comment_view(request, post_id, parent_id=None):
    if request.method == "POST":
        user_id = request.user_id
        content = request.POST.get("content", "").strip()
        
        if not content:
            return redirect('posts:post-detail-page', post_id=post_id)
        
        try:
            sql_comments.add_comment(post_id, user_id, content, parent_id)
            messages.success(request, "Comment added successfully")
        except Exception as e:
            messages.error(request, f"Error adding comment: {e}")
        
        return redirect('posts:post-detail-page', post_id=post_id)
    
    return redirect('posts:post-detail-page', post_id=post_id)


@jwt_required
def post_detail_view(request, post_id):
    post = sql_posts.get_post_with_tags(post_id)
    if not post:
        return render(request, "404.html", status=404)

    # ✅ Берём user_id из request
    current_user_id = getattr(request, 'user_id', None)
    
    print(f"VIEW DEBUG: current_user_id = {current_user_id}")
    print(f"VIEW DEBUG: Type = {type(current_user_id)}")
    print(f"VIEW DEBUG: request.user_id exists? {hasattr(request, 'user_id')}")

    comments_tree = sql_comments.get_comments_tree(post_id)
    comments_dict = {c['id']: dict(c, children=[]) for c in comments_tree}
    root_comments = []

    for c in comments_tree:
        if c['parent_id']:
            parent = comments_dict.get(c['parent_id'])
            if parent:
                parent['children'].append(comments_dict[c['id']])
        else:
            root_comments.append(comments_dict[c['id']])

    # ✅ Явно создаём словарь контекста
    template_context = {
        "post": post,
        "comments": root_comments,
        "current_user_id": current_user_id,
    }
    
    print(f"VIEW DEBUG: template_context keys = {template_context.keys()}")
    print(f"VIEW DEBUG: template_context['current_user_id'] = {template_context['current_user_id']}")
    
    # ✅ Дополнительная проверка - выведем весь контекст
    for key, value in template_context.items():
        print(f"  {key}: {value} (type: {type(value)})")
    
    return render(request, "posts/post_detail.html", template_context)


@jwt_required
@require_http_methods(["POST"])
def comment_delete_view(request, comment_id, post_id):
    user_id = request.user_id
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT delete_comment_func(%s, %s)",
                (comment_id, user_id)
            )
        messages.success(request, "Comment deleted successfully")
    except Exception as e:
        messages.error(request, f"Error: {e}")
    
    return redirect("posts:post-detail-page", post_id=post_id)
