from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from users.views import jwt_required
from .sql_tags import (
    create_tags_tables,
    create_tag,
    get_tag,
    get_all_tags,
    update_tag,
    delete_tag,
    update_tag
)

# =========================
# Инициализация таблиц
# =========================
create_tags_tables()

# =========================
# Список всех тегов
# =========================
@jwt_required
def tags_list(request):
    tags = get_all_tags()
    return render(request, "tags/tags_list.html", {"tags": tags})

# =========================
# Просмотр одного тега
# =========================
@jwt_required
def tag_detail_view(request, tag_id):
    tag = get_tag(tag_id)
    if not tag:
        return render(request, "tags/tag_not_found.html", status=404)
    return render(request, "tags/tag_detail.html", {"tag": tag})

# =========================
# Создание тега через форму
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["POST"])
def tag_create_view(request):
    name = request.POST.get("name")
    if not name:
        return render(request, "tags/tag_create.html", {"error": "Name is required"})

    # Проверяем на дубли
    existing_tags = get_all_tags()
    if any(tag["name"].lower() == name.lower() for tag in existing_tags):
        return render(request, "tags/tag_create.html", {"error": f"Tag '{name}' already exists"})

    # Создаем тег
    create_tag(name)
    return redirect("tags:list_tags")

# =========================
# Обновление тега через форму
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def tag_update_view(request, tag_id):
    tag = get_tag(tag_id)
    if not tag:
        return render(request, "tags/tag_not_found.html", status=404)

    if request.method == "POST":
        name = request.POST.get("name")
        if not name:
            return render(request, "tags/tag_update.html", {"tag": tag, "error": "Name is required"})

        # Проверка на дубли
        existing_tags = get_all_tags()
        if any(t["name"].lower() == name.lower() and t["id"] != tag_id for t in existing_tags):
            return render(request, "tags/tag_update.html", {"tag": tag, "error": f"Tag '{name}' already exists"})

        update_tag(tag_id, name)
        return redirect("tags:tag_detail", tag_id=tag_id)

    return render(request, "tags/tag_update.html", {"tag": tag})

# =========================
# Удаление тега через форму
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["POST"])
def tag_delete_view(request, tag_id):
    deleted_id = delete_tag(tag_id)
    if deleted_id:
        return redirect("tags:list_tags")
    else:
        return render(request, "tags/tags_list.html", {"error": "Tag not found", "tags": get_all_tags()})
