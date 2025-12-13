from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_list, name='profile_list'),
    path('edit/', views.profile_update, name='profile_update'),
    path('<str:username>/', views.profile_detail, name='profile_detail'),
]
