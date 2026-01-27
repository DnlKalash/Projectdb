import jwt as pyjwt
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from functools import wraps
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from django.contrib.auth.hashers import make_password, check_password
from .sql_users import create_users_table, register_user, get_user_by_username, user_exists

# =========================
# Главная страница
# =========================
def htmlshablon(request):
    create_users_table()
    token = request.COOKIES.get('jwt')
    username = None

    if token:
        try:
            payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_exists(user_id):
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT username FROM users WHERE id = %s", [user_id])
                    row = cursor.fetchone()
                    if row:
                        username = row[0]
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
            pass

    return render(request, 'users/main.html', {'username': username})

# =========================
# Регистрация
# =========================
def register(request):
    create_users_table()
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        password = request.POST.get('password').strip()

        if not username or not email or not password:
            messages.error(request, "All fields are required")
            return render(request, 'users/register.html')

        hashed_password = make_password(password)

        try:
            register_user(username, email, hashed_password)
            messages.success(request, "Registration successful")
            return redirect('login')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'users/register.html')

# =========================
# Логин
# =========================
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Username and password are required")
            return render(request, 'users/login.html')

        user = get_user_by_username(username)
        if not user:
            messages.error(request, "Invalid username or password")
            return render(request, 'users/login.html')

        user_id = user['user_id']
        hashed_password = user['password']

        if not check_password(password, hashed_password):
            messages.error(request, "Invalid username or password")
            return render(request, 'users/login.html')

        payload = {
            'user_id': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24),
        }

        token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        response = redirect('htmlshablon')
        response.set_cookie('jwt', token, httponly=True, max_age=86400, samesite='Lax')
        return response

    return render(request, 'users/login.html')

# =========================
# Логаут
# =========================
@require_POST
def logout(request):
    response = redirect('htmlshablon')
    response.delete_cookie('jwt')
    return response

# =========================
# Декоратор JWT
# =========================
def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.COOKIES.get('jwt')
        if not token:
            return redirect('login')

        try:
            payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if not user_exists(user_id):
                return redirect('login')
            request.user_id = user_id
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper
