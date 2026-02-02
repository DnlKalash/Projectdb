from django.urls import path
from . import views

urlpatterns = [
    # =========================
    # JSON API endpoints
    # =========================
    path('api/me/', views.profile_detail, name='profile-detail'),
    path('api/update/', views.profile_update_view, name='profile-update'),
    path('api/delete/', views.profile_delete_view, name='profile-delete'),
    path('api/stats/', views.profile_stats_api, name='profile-stats-api'),  # НОВОЕ

    # =========================
    # HTML pages
    # =========================
    path('me/', views.profile_page, name='profile-detail-page'),
    path('edit/', views.profile_page, name='profile-edit-page'),
    
    # =========================
    # НОВОЕ: Статистика и рейтинги
    # =========================
    path('stats/', views.profile_stats_page, name='profile-stats'),
    path('leaderboard/', views.leaderboard_page, name='leaderboard'),
    path('active/', views.most_active_users_page, name='most-active'),
    path('users/', views.all_users_page, name='all-users'),
]