from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .sql_client import get_profile, create_profile, update_profile, delete_profile

# Для теста используем user_id = 18
TEST_USER_ID = 18

@csrf_exempt
@require_http_methods(["GET"])
def profile_detail(request):
    profile = get_profile(TEST_USER_ID)
    if not profile:
        profile = create_profile(TEST_USER_ID)
    return JsonResponse(profile)

@csrf_exempt
@require_http_methods(["POST"])
def profile_update_view(request):
    try:
        data = json.loads(request.body)
        avatar_url = data.get("avatar_url")
        bio = data.get("bio")
        reputation = data.get("reputation")
        updated = update_profile(TEST_USER_ID, avatar_url, bio, reputation)
        if updated:
            profile = get_profile(TEST_USER_ID)
            return JsonResponse(profile)
        else:
            return JsonResponse({"error": "Profile not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

@csrf_exempt
@require_http_methods(["DELETE"])
def profile_delete_view(request):
    deleted = delete_profile(TEST_USER_ID)
    if deleted:
        return JsonResponse({"message": "Profile deleted"})
    else:
        return JsonResponse({"error": "Profile not found"}, status=404)

def profile_page(request):
    profile = get_profile(TEST_USER_ID)
    if not profile:
        profile = create_profile(TEST_USER_ID)
    return render(request, "client/client.html", {"profile": profile})
