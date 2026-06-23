from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm

# 📝 1. 회원가입 기능 (HTML 수동 작성 폼과 100% 호환 및 검증)
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # ❌ 검증 1: 비밀번호와 비밀번호 확인이 일치하지 않는 경우
        if password != password_confirm:
            return render(request, 'accounts/signup.html', {'error': '비밀번호가 일치하지 않습니다.'})
            
        # ❌ 검증 2: 이미 존재하는 아이디인 경우
        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/signup.html', {'error': '이미 존재하는 아이디입니다.'})
            
        # ⭕ 검증 통과: 유저 생성 (이메일 없이 간결하게 가입)
        user = User.objects.create_user(username=username, password=password)
        auth_login(request, user)  # 회원가입 완료 후 즉시 로그인 처리
        return redirect('/')       # 메인 홈으로 이동
        
    return render(request, 'accounts/signup.html')


# 🔒 2. 로그인 기능 (AuthenticationForm 내장 폼 활용)
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('/')  # 로그인 완료 후 메인 홈으로 이동
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


# 🚪 3. 로그아웃 기능
def logout_view(request):
    auth_logout(request)
    return redirect('login')


# 🏠 4. 임시 메인 홈 화면 (로그인 확인용)
def home_view(request):
    return render(request, 'home.html')