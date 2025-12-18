from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_list, name='profile_list'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('edit/', views.profile_update, name='profile_update'),
    path('<str:username>/', views.profile_detail, name='profile_detail'),
]
