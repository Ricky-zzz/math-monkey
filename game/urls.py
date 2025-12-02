from django.urls import path
from . import views

urlpatterns = [
    path('', views.auth_view, name='auth'),     
    path('login/', views.login_api, name='login_api'),
    path('register/', views.register_api, name='register_api'),
    path('guest/', views.guest_api, name='guest_api'),
    path('play/', views.play_view, name='play'), 
    path('logout/', views.logout_view, name='logout'), 
    path('api/questions/', views.get_questions, name='get_questions'),
    path('api/submit/', views.submit_result, name='submit_result'),
    path('api/leaderboard/', views.get_leaderboard, name='get_leaderboard'),
    path('api/profile/', views.get_user_profile, name='get_user_profile'),
]