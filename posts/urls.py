from django.urls import path
from . import views

urlpatterns = [
    path('', views.posts_list, name='posts'),
    path('like/<int:post_id>/', views.like_post, name='like_post'),
    path('comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('delete/<int:post_id>/', views.delete_post, name='delete_post'),

]
