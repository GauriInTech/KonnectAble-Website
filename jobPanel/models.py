from django.db import models
from django.conf import settings


class HiringPartnerProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	company_name = models.CharField(max_length=255, blank=True)
	website = models.URLField(blank=True)

	def __str__(self):
		return f"HiringPartner: {self.company_name or self.user.get_username()}"


class ApplicantProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	headline = models.CharField(max_length=255, blank=True)
	location = models.CharField(max_length=255, blank=True)
	skills = models.TextField(blank=True)
	experience = models.TextField(blank=True)
	resume = models.FileField(upload_to='resumes/', blank=True, null=True)

	def __str__(self):
		return f"Applicant: {self.user.get_username()}"


class Job(models.Model):
	title = models.CharField(max_length=255)
	description = models.TextField()
	company = models.CharField(max_length=255, blank=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.title} @ {self.company or 'Unknown'}"


class Application(models.Model):
	STATUS_CHOICES = (
		('applied', 'Applied'),
		('review', 'In Review'),
		('hired', 'Hired'),
		('rejected', 'Rejected'),
	)

	job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
	applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	cover_letter = models.TextField(blank=True)
	resume = models.FileField(upload_to='applications/resumes/', blank=True, null=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
	applied_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.applicant.get_username()} -> {self.job.title} ({self.status})"

