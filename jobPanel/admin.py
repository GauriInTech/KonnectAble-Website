from django.contrib import admin
from .models import Job, Application, ApplicantProfile, HiringPartnerProfile


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
	list_display = ('title', 'company', 'created_by', 'created_at')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
	list_display = ('job', 'applicant', 'status', 'applied_at')


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'headline', 'location')


@admin.register(HiringPartnerProfile)
class HiringPartnerProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'company_name')

