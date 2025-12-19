from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='job_index'),
    path('applicant/profile/create/', views.applicant_profile_create, name='applicant_profile_create'),
    path('create/', views.create_job, name='create_job'),
    path('list/', views.job_list, name='job_list'),
    path('applicant/', views.applicant_dashboard, name='applicant_dashboard'),
    path('hiring/', views.hiring_dashboard, name='hiring_dashboard'),
    
    path('<int:pk>/', views.job_detail, name='job_detail'),
    path('<int:pk>/apply/', views.apply_to_job, name='apply_to_job'),
    path('application/<int:application_id>/hire/', views.hire_applicant, name='hire_applicant'),
]
