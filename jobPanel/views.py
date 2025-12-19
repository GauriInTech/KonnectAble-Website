from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import RoleSelectionForm, ApplicantProfileForm, JobForm, ApplicationForm
from .models import ApplicantProfile, HiringPartnerProfile, Job, Application


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
	return render(request, 'jobPanel/job_list.html', {'jobs': jobs})


@login_required
def hiring_dashboard(request):
	# jobs created by current user and their applications
	jobs = Job.objects.filter(created_by=request.user).order_by('-created_at')
	return render(request, 'jobPanel/hiring_dashboard.html', {'jobs': jobs})


@login_required
def applicant_dashboard(request):
	# show available jobs and applications by this user
	jobs = Job.objects.all().order_by('-created_at')
	applications = Application.objects.filter(applicant=request.user).select_related('job')
	applied_job_ids = set(app.job_id for app in applications)
	return render(request, 'jobPanel/applicant_dashboard.html', {
		'jobs': jobs,
		'applications': applications,
		'applied_job_ids': applied_job_ids,
	})



def job_detail(request, pk):
	job = get_object_or_404(Job, pk=pk)
	form = ApplicationForm()
	return render(request, 'jobPanel/job_detail.html', {'job': job, 'form': form})


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

