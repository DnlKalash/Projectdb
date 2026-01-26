import jwt as pyjwt
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from functools import wraps
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from django.db import connection
from django.contrib.auth.hashers import make_password, check_password
from .sql_users import create_users_table



def htmlshablon(request):
    create_users_table()
    token = request.COOKIES.get('jwt')
    username = None

    if token:
        try:
            payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT username FROM users WHERE id = %s",
                    [user_id]
                )
                row = cursor.fetchone()

            if row:
                username = row[0]

        except pyjwt.ExpiredSignatureError:
            pass
        except pyjwt.InvalidTokenError:
            pass

    return render(request, 'users/main.html', {'username': username})



def register(request):
    create_users_table()
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        hashed_password = make_password(password)

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    [username, email, hashed_password]
                )

            messages.success(request, "Registration successful")
            return redirect('login')  

        except Exception:
            messages.error(request, "Username or email already exists")

    
    return render(request, 'users/register.html')


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Username and password are required")
            return render(request, 'users/login.html')

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, password FROM users WHERE username = %s",
                [username]
            )
            row = cursor.fetchone()

        if row is None:
            messages.error(request, "Invalid username or password")
            return render(request, 'users/login.html')

        user_id, hashed_password = row

        if not check_password(password, hashed_password):
            messages.error(request, "Invalid username or password")
            return render(request, 'users/login.html')

        payload = {
            'user_id': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24),
        }

        token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        response = redirect('htmlshablon')  # убедись, что такой url есть
        response.set_cookie(
            'jwt',
            token,
            httponly=True,
            max_age=86400,
            samesite='Lax'
        )
        return response

    return render(request, 'users/login.html')

@require_POST
def logout(request):
    response = redirect('htmlshablon')
    response.delete_cookie('jwt')
    return response

def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.COOKIES.get('jwt')
        if not token:
            return redirect('login')

        try:
            payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE id = %s",
                    [user_id]
                )
                exists = cursor.fetchone()

            if not exists:
                return redirect('login')

            request.user_id = user_id

        except pyjwt.ExpiredSignatureError:
            return redirect('login')
        except pyjwt.InvalidTokenError:
            return redirect('login')

        return view_func(request, *args, **kwargs)

    return wrapper
