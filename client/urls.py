from django.urls import path
from . import views

urlpatterns = [
    # =========================
    # JSON API endpoints
    # =========================
    path('api/me/', views.profile_detail, name='profile-detail'),
    path('api/update/', views.profile_update_view, name='profile-update'),
    path('api/delete/', views.profile_delete_view, name='profile-delete'),

    # =========================
    # HTML pages
    # =========================
    path('me/', views.profile_page, name='profile-detail-page'),
    path('edit/', views.profile_page, name='profile-edit-page'),
]
