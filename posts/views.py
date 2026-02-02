from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.views import jwt_required
from comments import sql_comments
from reactions import sql_reactions
from django.db import connection
from posts.sql_posts import (
    init_posts_table,
    create_post_with_tags,
    get_all_posts,
    get_post_by_id,
    get_post_with_tags,
    delete_post as delete_post_sql,
    get_posts_by_tag,
    add_tag_to_post,
    remove_tag_from_post,
    get_all_tags,
    update_my_post,
    get_my_posts,
)

# ДОБАВЛЕНО: импорт функций статистики из client.sql_client
from client.sql_client import (
    get_posts_with_stats,
    get_post_stats_by_id,
    get_most_engaged_posts,
    get_posts_by_tag_with_stats
)


_table_initialized = False

def ensure_posts_table():
    global _table_initialized
    if not _table_initialized:
        init_posts_table()
        _table_initialized = True

# ======================
# LIST ALL POSTS
# ======================

def dict_fetchall(cursor):
    """Преобразуем результат SQL в список словарей"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def posts_list_page(request):
    ensure_posts_table()
    posts = get_all_posts(limit=50, offset=0)
    return render(request, "posts/posts_list.html", {"posts": posts})

# ======================
# НОВОЕ: LIST POSTS WITH STATS
# ======================
def posts_list_with_stats_page(request):
    """Список постов со статистикой"""
    ensure_posts_table()
    posts = get_posts_with_stats(limit=50, offset=0)
    return render(request, "posts/posts_list_stats.html", {"posts": posts})

# ======================
# НОВОЕ: TRENDING POSTS
# ======================
def trending_posts_page(request):
    """Самые популярные посты"""
    ensure_posts_table()
    posts = get_most_engaged_posts(limit=20)
    return render(request, "posts/trending.html", {"posts": posts})

# ======================
# LIST POSTS BY TAG
# ======================
def posts_by_tag_page(request, tag_name):
    ensure_posts_table()
    posts = get_posts_by_tag(tag_name)
    return render(request, "posts/posts_by_tag.html", {
        "posts": posts, 
        "tag_name": tag_name
    })

# ======================
# НОВОЕ: POSTS BY TAG WITH STATS
# ======================
def posts_by_tag_with_stats_page(request, tag_name):
    """Посты по тегу со статистикой"""
    ensure_posts_table()
    posts = get_posts_by_tag_with_stats(tag_name, limit=50)
    return render(request, "posts/posts_by_tag_stats.html", {
        "posts": posts,
        "tag_name": tag_name
    })

# ======================
# POST DETAIL WITH COMMENTS AND REACTIONS
# ======================
@jwt_required
def post_detail_page(request, post_id):
    """
    Детальная страница поста с комментариями и реакциями
    """
    ensure_posts_table()
    post = get_post_with_tags(post_id)
    if not post:
        return render(request, "posts/post_not_found.html", status=404)

    # ДОБАВЛЕНО: получаем статистику поста
    post_stats = get_post_stats_by_id(post_id)
    
    comments_tree = sql_comments.get_comments_tree(post_id)

    # Строим дерево комментариев
    comments_dict = {c['id']: dict(c, children=[]) for c in comments_tree}
    root_comments = []

    for c in comments_tree:
        if c['parent_id']:
            parent = comments_dict.get(c['parent_id'])
            if parent:
                parent['children'].append(comments_dict[c['id']])
        else:
            root_comments.append(comments_dict[c['id']])

    # Получаем реакции
    reactions_stats = sql_reactions.get_post_reactions_stats(post_id)
    likes_count = 0
    loves_count = 0
    dislikes_count = 0
    
    for stat in reactions_stats:
        if stat['reaction_type'] == 'like':
            likes_count = stat['count']
        elif stat['reaction_type'] == 'love':
            loves_count = stat['count']
        elif stat['reaction_type'] == 'dislike':
            dislikes_count = stat['count']

    # Получаем реакцию текущего пользователя
    user_id = request.session.get('user_id', 1)
    user_reaction = sql_reactions.get_user_reaction_on_post(user_id, post_id)

    return render(request, "posts/post_detail.html", {
        "post": post,
        "post_stats": post_stats,  # ДОБАВЛЕНО
        "comments": root_comments,
        "current_user_id": request.user_id,
        "likes_count": likes_count,
        "loves_count": loves_count,
        "dislikes_count": dislikes_count,
        "user_reaction": user_reaction,
    })

# ======================
# CREATE POST WITH TAGS
# ======================
@jwt_required
@require_http_methods(["GET", "POST"])
def post_create_page(request):
    ensure_posts_table()
    tags = get_all_tags()

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        selected_tags = request.POST.getlist("tags")
        author_id = request.user_id

        if not title or not content:
            error = "Title and content are required."
            return render(request, "posts/post_create.html", {"tags": tags, "error": error})

        create_post_with_tags(title, content, author_id, selected_tags)
        return redirect("posts:my-posts")

    return render(request, "posts/post_create.html", {"tags": tags})

# ======================
# DELETE POST
# ======================
@jwt_required
@require_http_methods(["POST"])
def delete_post_view(request, post_id):
    user_id = request.user_id
    try:
        deleted_id = delete_post_sql(post_id, user_id)
    except Exception as e:
        posts = get_my_posts(user_id)
        return render(request, "posts/my_posts.html", {"error": str(e), "posts": posts})

    return redirect("posts:my-posts")

# ======================
# ADD TAG TO POST
# ======================
@jwt_required
def add_tag_to_post_view(request, post_id):
    ensure_posts_table()
    if request.method == 'POST':
        tag_name = request.POST.get('tag_name', '').strip()
        if tag_name:
            user_id = request.user_id
            try:
                add_tag_to_post(post_id, tag_name, user_id)
            except Exception as e:
                return redirect('posts:post-detail-page', post_id=post_id)
        
        return redirect('posts:post-detail-page', post_id=post_id)
    
    return redirect('posts:post-detail-page', post_id=post_id)

# ======================
# REMOVE TAG FROM POST
# ======================
@jwt_required
def remove_tag_from_post_view(request, post_id, tag_name):
    ensure_posts_table()
    if request.method == 'POST':
        remove_tag_from_post(post_id, tag_name)
    
    # Редирект обратно на пост
    return redirect('posts:post-detail-page', post_id=post_id)

# ======================
# MY POSTS
# ======================
@jwt_required
def my_posts_view(request):
    """HTTP-запрос для отображения только моих постов"""
    user_id = request.user_id
    posts = get_my_posts(user_id)
    
    return render(request, "posts/my_posts.html", {"posts": posts})

# ======================
# UPDATE POST
# ======================
@jwt_required
@require_http_methods(["GET", "POST"])
def post_update_page(request, post_id):
    """HTTP-запрос для редактирования поста пользователя через SQL"""
    user_id = request.user_id

    post = get_post_with_tags(post_id)
    if not post:
        return render(request, "posts/error.html", {"error": "Post not found"})

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            return render(request, "posts/post_update.html", {"post": post, "error": "Title and content cannot be empty."})

        updated_post = update_my_post(post_id, user_id, title, content)

        return redirect("posts:my-posts")

    return render(request, "posts/post_update.html", {"post": post})