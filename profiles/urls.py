from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_list, name='profile_list'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('edit/', views.profile_update, name='profile_update'),
    path('support/<str:username>/', views.toggle_support, name='toggle_support'),
    path('<str:username>/supporters/', views.supporters_list, name='supporters_list'),
    path('<str:username>/supporting/', views.supporting_list, name='supporting_list'),
    path('<str:username>/', views.profile_detail, name='profile_detail'),
]
