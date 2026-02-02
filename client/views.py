from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .sql_client import (
    get_profile, 
    create_profile, 
    update_profile, 
    delete_profile,
    # ДОБАВЛЕНО: импорт функций статистики
    get_user_activity,
    get_top_users_by_reputation,
    get_most_active_users,
    get_all_users_activity
)
from users.views import jwt_required

# =========================
# Получение профиля (API)
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["GET"])
def profile_detail(request):
    profile = get_profile(request.user_id)
    if not profile:
        profile = create_profile(request.user_id)
    return JsonResponse(profile)

# =========================
# Обновление профиля (API)
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["POST"])
def profile_update_view(request):
    try:
        data = json.loads(request.body)
        avatar_url = data.get("avatar_url")
        bio = data.get("bio")

        updated = update_profile(request.user_id, avatar_url, bio)
        if updated:
            profile = get_profile(request.user_id)
            return JsonResponse(profile)
        else:
            return JsonResponse({"error": "Profile not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

# =========================
# Удаление профиля (API)
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["DELETE"])
def profile_delete_view(request):
    deleted = delete_profile(request.user_id)
    if deleted:
        return JsonResponse({"message": "Profile deleted"})
    else:
        return JsonResponse({"error": "Profile not found"}, status=404)

# =========================
# Страница профиля (HTML)
# =========================
@jwt_required
def profile_page(request):
    profile = get_profile(request.user_id)
    if not profile:
        profile = create_profile(request.user_id)
    return render(request, "client/client.html", {"profile": profile})

# =========================
# НОВОЕ: Страница профиля со статистикой
# =========================
@jwt_required
def profile_stats_page(request):
    """Профиль пользователя со статистикой активности"""
    profile = get_profile(request.user_id)
    if not profile:
        profile = create_profile(request.user_id)
    
    # Получаем статистику пользователя
    activity = get_user_activity(request.user_id)
    
    return render(request, "client/profile_stats.html", {
        "profile": profile,
        "activity": activity
    })

# =========================
# НОВОЕ: API для получения статистики
# =========================
@jwt_required
@csrf_exempt
@require_http_methods(["GET"])
def profile_stats_api(request):
    """API для получения статистики пользователя"""
    activity = get_user_activity(request.user_id)
    if activity:
        return JsonResponse(activity)
    else:
        return JsonResponse({"error": "User not found"}, status=404)

# =========================
# НОВОЕ: Таблица лидеров (Leaderboard)
# =========================
def leaderboard_page(request):
    """Топ пользователей по репутации"""
    top_users = get_top_users_by_reputation(limit=20)
    return render(request, "client/leaderboard.html", {"users": top_users})

# =========================
# НОВОЕ: Самые активные пользователи
# =========================
def most_active_users_page(request):
    """Самые активные пользователи (по вкладу)"""
    active_users = get_most_active_users(limit=20)
    return render(request, "client/most_active.html", {"users": active_users})

# =========================
# НОВОЕ: Все пользователи со статистикой
# =========================
def all_users_page(request):
    """Список всех пользователей со статистикой"""
    users = get_all_users_activity()
    return render(request, "client/all_users.html", {"users": users})