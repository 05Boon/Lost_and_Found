from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render, redirect
from .forms import RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect('report_list')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account is ready. You can now sign in.')
            return redirect('login')

    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def _request_data(request):
    if request.content_type == 'application/json':
        import json

        try:
            return json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return {}
    return request.POST


def api_csrf(request):
    get_token(request)
    return JsonResponse({'detail': 'CSRF cookie initialized.'})


@require_POST
def api_login(request):
    data = _request_data(request)
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse(
            {'detail': 'Invalid username or password.'},
            status=400,
        )

    login(request, user)
    request.session.set_expiry(3600)
    return JsonResponse({
        'id': user.pk,
        'username': user.username,
        'role': user.role,
        'detail': 'Login successful.',
    })


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({'detail': 'Logout successful.'})


def api_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)

    user = request.user
    return JsonResponse({
        'id': user.pk,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'role': user.role,
        'is_staff': user.is_staff,
    })