from django.contrib import admin # type: ignore
from django.urls import path # type: ignore
from django.contrib.auth.views import LogoutView
from .views import  signup_view , login_view, home


urlpatterns = [
    path('', home, name='accounts_home'),
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]
