from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models

from .forms import RoleSelectionForm, ApplicantProfileForm, JobForm, ApplicationForm
from .models import ApplicantProfile, HiringPartnerProfile, Job, Application
from notifications.models import Notification


@login_required
def index(request):
	# If user already has a role, redirect to respective dashboard
	if request.method == 'GET':
		if hasattr(request.user, 'applicantprofile'):
			return redirect('applicant_dashboard')
		if hasattr(request.user, 'hiringpartnerprofile'):
			return redirect('hiring_dashboard')

	if request.method == 'POST':
		form = RoleSelectionForm(request.POST)
		if form.is_valid():
			role = form.cleaned_data['role']
			if role == 'applicant':
				if hasattr(request.user, 'applicantprofile'):
					return redirect('job_list')
				else:
					return redirect('applicant_profile_create')
			else:
				if hasattr(request.user, 'hiringpartnerprofile'):
					return redirect('hiring_dashboard')
				else:
					return redirect('create_job')
	else:
		form = RoleSelectionForm()
	return render(request, 'jobPanel/index.html', {'form': form})


@login_required
def applicant_profile_create(request):
	try:
		profile = request.user.applicantprofile
		messages.info(request, 'Applicant profile already exists.')
		return redirect('job_list')
	except ApplicantProfile.DoesNotExist:
		pass

	if request.method == 'POST':
		form = ApplicantProfileForm(request.POST, request.FILES)
		if form.is_valid():
			profile = form.save(commit=False)
			profile.user = request.user
			profile.save()
			messages.success(request, 'Applicant profile saved.')
			return redirect('job_list')
	else:
		form = ApplicantProfileForm()
	return render(request, 'jobPanel/applicant_profile_form.html', {'form': form})


@login_required
def create_job(request):
	if request.method == 'POST':
		form = JobForm(request.POST)
		if form.is_valid():
			job = form.save(commit=False)
			job.created_by = request.user
			job.save()
			# ensure hiring partner profile exists
			HiringPartnerProfile.objects.get_or_create(user=request.user)
			messages.success(request, 'Job created.')
			return redirect('job_list')
	else:
		form = JobForm()
	return render(request, 'jobPanel/create_job.html', {'form': form})


def job_list(request):
	jobs = Job.objects.all().order_by('-created_at')

	# Search functionality
	search_query = request.GET.get('search', '')
	if search_query:
		jobs = jobs.filter(
			models.Q(title__icontains=search_query) |
			models.Q(company__icontains=search_query) |
			models.Q(description__icontains=search_query) |
			models.Q(skills_required__icontains=search_query)
		)

	# Filters
	location_filter = request.GET.get('location', '')
	if location_filter:
		jobs = jobs.filter(location__icontains=location_filter)

	job_type_filter = request.GET.get('job_type', '')
	if job_type_filter:
		jobs = jobs.filter(job_type=job_type_filter)

	salary_min_filter = request.GET.get('salary_min', '')
	if salary_min_filter:
		try:
			salary_min = float(salary_min_filter)
			jobs = jobs.filter(salary_max__gte=salary_min)
		except ValueError:
			pass

	experience_filter = request.GET.get('experience', '')
	if experience_filter:
		jobs = jobs.filter(experience_required__icontains=experience_filter)

	return render(request, 'jobPanel/job_list.html', {
		'jobs': jobs,
		'search_query': search_query,
		'location_filter': location_filter,
		'job_type_filter': job_type_filter,
		'salary_min_filter': salary_min_filter,
		'experience_filter': experience_filter,
	})


@login_required
def hiring_dashboard(request):
	# jobs created by current user and their applications
	jobs = Job.objects.filter(created_by=request.user).order_by('-created_at')

	# Add application counts to each job for template use
	for job in jobs:
		job.hired_count = job.applications.filter(status='hired').count()
		job.pending_count = job.applications.filter(status='applied').count()
		job.rejected_count = job.applications.filter(status='rejected').count()

	return render(request, 'jobPanel/hiring_dashboard.html', {'jobs': jobs})


@login_required
def applicant_dashboard(request):
	# show available jobs and applications by this user
	jobs = Job.objects.all().order_by('-created_at')
	applications = Application.objects.filter(applicant=request.user).select_related('job')
	applied_job_ids = set(app.job_id for app in applications)

	# Search functionality
	search_query = request.GET.get('search', '')
	if search_query:
		jobs = jobs.filter(
			models.Q(title__icontains=search_query) |
			models.Q(company__icontains=search_query) |
			models.Q(description__icontains=search_query) |
			models.Q(skills_required__icontains=search_query)
		)

	# Filters
	location_filter = request.GET.get('location', '')
	if location_filter:
		jobs = jobs.filter(location__icontains=location_filter)

	job_type_filter = request.GET.get('job_type', '')
	if job_type_filter:
		jobs = jobs.filter(job_type=job_type_filter)

	salary_min_filter = request.GET.get('salary_min', '')
	if salary_min_filter:
		try:
			salary_min = float(salary_min_filter)
			jobs = jobs.filter(salary_max__gte=salary_min)
		except ValueError:
			pass

	experience_filter = request.GET.get('experience', '')
	if experience_filter:
		jobs = jobs.filter(experience_required__icontains=experience_filter)

	return render(request, 'jobPanel/applicant_dashboard.html', {
		'jobs': jobs,
		'applications': applications,
		'applied_job_ids': applied_job_ids,
		'search_query': search_query,
		'location_filter': location_filter,
		'job_type_filter': job_type_filter,
		'salary_min_filter': salary_min_filter,
		'experience_filter': experience_filter,
	})



def job_detail(request, pk):
	job = get_object_or_404(Job, pk=pk)
	is_hiring_partner = request.user.is_authenticated and job.created_by == request.user

	context = {
		'job': job,
		'is_hiring_partner': is_hiring_partner,
	}

	if not is_hiring_partner:
		# Show application form for applicants
		form = ApplicationForm()
		context['form'] = form

	return render(request, 'jobPanel/job_detail.html', context)


@login_required
def apply_to_job(request, pk):
	job = get_object_or_404(Job, pk=pk)
	# ensure applicant profile exists
	try:
		request.user.applicantprofile
	except ApplicantProfile.DoesNotExist:
		messages.error(request, 'Please complete your applicant profile before applying.')
		return redirect('applicant_profile_create')

	if request.method == 'POST':
		form = ApplicationForm(request.POST, request.FILES)
		if form.is_valid():
			application = form.save(commit=False)
			application.job = job
			application.applicant = request.user
			# if resume not provided, use applicant profile resume
			if not application.resume and hasattr(request.user, 'applicantprofile'):
				application.resume = request.user.applicantprofile.resume
			application.save()

			# Create notification for job creator
			Notification.objects.create(
				recipient=job.created_by,
				sender=request.user,
				notification_type='job_application',
				message=f"{request.user.username} applied to your job '{job.title}'!",
				related_job=job,
				related_application=application
			)

			messages.success(request, 'Applied to job successfully.')
			return redirect('job_detail', pk=job.pk)
	messages.error(request, 'There was a problem with your application.')
	return redirect('job_detail', pk=job.pk)


@login_required
def hire_applicant(request, application_id):
	application = get_object_or_404(Application, pk=application_id)
	# only allow job creator to hire
	if application.job.created_by != request.user:
		messages.error(request, 'Not authorized')
		return redirect('job_detail', pk=application.job.pk)
	application.status = 'hired'
	application.save()
	messages.success(request, f"{application.applicant.get_username()} hired.")
	return redirect('job_detail', pk=application.job.pk)


@login_required
def reject_applicant(request, application_id):
	application = get_object_or_404(Application, pk=application_id)
	# only allow job creator to reject
	if application.job.created_by != request.user:
		messages.error(request, 'Not authorized')
		return redirect('job_detail', pk=application.job.pk)

	if request.method == 'POST':
		rejection_reason = request.POST.get('rejection_reason', '').strip()
		if rejection_reason:
			application.status = 'rejected'
			application.rejection_reason = rejection_reason
			application.save()
			messages.success(request, f"{application.applicant.get_username()} rejected.")
		else:
			messages.error(request, 'Please provide a reason for rejection.')
		return redirect('hiring_dashboard')

	# If GET request, redirect to job detail (shouldn't happen normally)
	return redirect('job_detail', pk=application.job.pk)


@login_required
def withdraw_application(request, application_id):
	application = get_object_or_404(Application, pk=application_id)
	# only allow applicant to withdraw their own application
	if application.applicant != request.user:
		messages.error(request, 'Not authorized')
		return redirect('applicant_dashboard')

	if request.method == 'POST':
		if application.status == 'applied':
			application.delete()
			messages.success(request, 'Application withdrawn successfully.')
		else:
			messages.error(request, 'Cannot withdraw an application that has already been reviewed.')
		return redirect('applicant_dashboard')

	# If GET request, redirect to dashboard
	return redirect('applicant_dashboard')
