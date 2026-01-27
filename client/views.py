from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .sql_client import get_profile, create_profile, update_profile, delete_profile
from users.views import jwt_required



@jwt_required
@csrf_exempt
@require_http_methods(["GET"])
def profile_detail(request):
    profile = get_profile(request.user_id)
    if not profile:
        profile = create_profile(request.user_id)
    return JsonResponse(profile)

@jwt_required
@csrf_exempt
@require_http_methods(["POST"])
def profile_update_view(request):
    try:
        data = json.loads(request.body)
        avatar_url = data.get("avatar_url")
        bio = data.get("bio")
        reputation = data.get("reputation")
        updated = update_profile(request.user_id, avatar_url, bio, reputation)
        if updated:
            profile = get_profile(request.user_id)
            return JsonResponse(profile)
        else:
            return JsonResponse({"error": "Profile not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
@jwt_required
@csrf_exempt
@require_http_methods(["DELETE"])
def profile_delete_view(request):
    deleted = delete_profile(request.user_id)
    if deleted:
        return JsonResponse({"message": "Profile deleted"})
    else:
        return JsonResponse({"error": "Profile not found"}, status=404)
    
@jwt_required
def profile_page(request):
    profile = get_profile(request.user_id)
    if not profile:
        profile = create_profile(request.user_id)
    return render(request, "client/client.html", {"profile": profile})
