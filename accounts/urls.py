from django.contrib import admin # type: ignore
from django.urls import path # type: ignore
from django.contrib.auth.views import LogoutView
from .views import signup_view, login_view, dashboard,auth_view, user_dashboard, user_search_api


urlpatterns = [
    path("", auth_view, name="auth"),
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    
    path('user-dashboard/', user_dashboard, name='accounts_home'),
    path('search-users/', user_search_api, name='user_search_api'),
    
    path('logout/', LogoutView.as_view(next_page='auth'), name='logout'),
]
