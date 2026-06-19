# counseling/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.counseling_home, name='counseling_home'),
    path('process/', views.process_counseling, name='process_counseling'),
    path('detail/<int:log_id>/', views.counseling_detail, name='counseling_detail'),
    path('category/<str:category_name>/', views.category_counseling, name='category_counseling'),
    path('calendar/', views.emotion_calendar, name='emotion_calendar'),
    path('diary/write/', views.write_diary, name='write_diary'),
    
    # 👥 커뮤니티 게시판 기능
    path('community/', views.community_list, name='community_list'),
    path('community/post/<int:post_id>/', views.community_detail, name='community_detail'),
    path('community/write/', views.community_write, name='community_write'),
    path('community/comment/<int:post_id>/', views.community_comment, name='community_comment'),
    
    # 💬 실시간 소모임 채팅 페이지 및 API
    path('community/chat/', views.real_time_chat, name='matching_chat'), # 채팅 화면 랜더링
    path('community/chat/api/messages/', views.chat_api, name='chat_api'), # 대화 데이터 API
    path('community/chat/api/users/', views.room_users_api, name='room_users_api'), # 참여자 데이터 API
    
    # 기타 마이페이지 및 토픽
    path('my_page/', views.my_page, name='my_page'),
    path('counseling/start_topic/', views.start_topic_counseling, name='start_topic_counseling'),
]