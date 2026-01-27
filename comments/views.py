from django.shortcuts import render, redirect
from posts import sql_posts
from comments import sql_comments
from users.views import jwt_required


def add_comment_view(request, post_id, parent_id=None):
    """
    POST: Добавить комментарий к посту или ответ на комментарий.
    """
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        
        print(f"DEBUG: POST data: {request.POST}")
        print(f"DEBUG: content: {content}")
        print(f"DEBUG: session: {request.session.items()}")
        
        if not content:
            print("DEBUG: Empty content, redirecting")
            return redirect('posts:post-detail-page', post_id=post_id)

        
        user_id = request.session.get('user_id')
        print(f"DEBUG: user_id from session: {user_id}")
        
        if not user_id:
            print("DEBUG: No user_id in session, using default 1")
            user_id = 1  
        
        print(f"DEBUG: Adding comment with user_id={user_id}, post_id={post_id}, parent_id={parent_id}")
        
        try:
            result = sql_comments.add_comment(post_id, user_id, content, parent_id)
            print(f"DEBUG: Comment added successfully: {result}")
        except Exception as e:
            print(f"DEBUG: Error adding comment: {e}")
            import traceback
            traceback.print_exc()
        
        
        return redirect('posts:post-detail-page', post_id=post_id)
    
    print("DEBUG: Not POST method, redirecting")
    return redirect('posts:post-detail-page', post_id=post_id)


def post_detail_view(request, post_id):
    """
    GET: Отобразить пост и все комментарии в виде дерева
    """
    post = sql_posts.get_post_with_tags(post_id)
    if not post:
        return render(request, "404.html", status=404)

    comments_tree = sql_comments.get_comments_tree(post_id)
    print(f"DEBUG: Comments tree for post {post_id}: {comments_tree}")

    # Словарь комментариев по id для быстрого построения дерева
    comments_dict = {c['id']: dict(c, children=[]) for c in comments_tree}
    root_comments = []

    for c in comments_tree:
        if c['parent_id']:
            parent = comments_dict.get(c['parent_id'])
            if parent:
                parent['children'].append(comments_dict[c['id']])
        else:
            root_comments.append(comments_dict[c['id']])

    print(f"DEBUG: Root comments: {root_comments}")

    return render(request, "posts/post_detail.html", {
        "post": post,
        "comments": root_comments
    })
@jwt_required
def delete_comment_view(request, comment_id, post_id):
    """Обработка удаления комментария по кнопке"""
    if request.method == "POST":
        sql_comments.delete_comment(comment_id)
    return redirect('posts:post-detail-page', post_id=post_id)