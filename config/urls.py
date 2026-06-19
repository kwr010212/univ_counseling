# config/urls.py
from django.contrib import admin
from django.urls import path, include
from counseling import views as counseling_views  # 안전하게 앱 단위로 views 가져오기

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. 루트 주소(로그인 후 이동할 메인 홈)를 counseling의 홈으로 연결
    path('', counseling_views.counseling_home, name='main_home'),  
    
    # 2. 회원관리(로그인/로그아웃) 주소 체계
    path('accounts/', include('accounts.urls')),
    
    # 3. 상담 앱 세부 주소 체계
    path('counseling/', include('counseling.urls')), 
]