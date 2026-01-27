from django.urls import path
from . import views

app_name = 'reactions'

urlpatterns = [
    path('<str:reactable_type>/<int:reactable_id>/<str:reaction_type>/', 
         views.toggle_reaction_view, 
         name='toggle-reaction'),
]