from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout

# 회원가입 기능
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)  # 회원가입 완료 후 즉시 로그인 처리
            return redirect('/')      # 메인 홈으로 이동
    else:
        form = UserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

# 로그인 기능
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('/')      # 로그인 완료 후 메인 홈으로 이동
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

# 로그아웃 기능
def logout_view(request):
    auth_logout(request)
    return redirect('login')

# 임시 메인 홈 화면 (로그인 확인용)
def home_view(request):
    return render(request, 'home.html')