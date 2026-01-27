from django.shortcuts import redirect
from django.http import JsonResponse
from reactions import sql_reactions
from comments import sql_comments


def toggle_reaction_view(request, reactable_type, reactable_id, reaction_type):
    """
    Добавить/изменить/удалить реакцию.
    Если юзер уже поставил такую же реакцию - удалить.
    Если юзер поставил другую реакцию - обновить.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    
    user_id = request.session.get('user_id', 1)
    
    
    if reactable_type not in ['post', 'comment']:
        return JsonResponse({"error": "Invalid reactable_type"}, status=400)
    
    
    if reaction_type not in ['like', 'love', 'dislike']:
        return JsonResponse({"error": "Invalid reaction_type"}, status=400)

    
    if reactable_type == 'post':
        current_reaction = sql_reactions.get_user_reaction_on_post(user_id, reactable_id)
    else:
        current_reaction = sql_reactions.get_user_reaction_on_comment(user_id, reactable_id)

    
    if current_reaction == reaction_type:
        sql_reactions.remove_reaction(user_id, reactable_type, reactable_id)
    else:
        
        sql_reactions.add_or_update_reaction(user_id, reactable_type, reactable_id, reaction_type)

    
    if reactable_type == 'post':
        return redirect('posts:post-detail-page', post_id=reactable_id)
    else:
        
        comment = sql_comments.get_comment(reactable_id)
        if comment:
            return redirect('posts:post-detail-page', post_id=comment['post_id'])
        return redirect('posts:posts-list-page')