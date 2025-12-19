from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import authenticate, login  # type: ignore
from .forms import SignupForm
from .models import User
from django.http import HttpResponse  # type: ignore
from django.http import JsonResponse
from posts.models import Post
from profiles.models import Profile
from jobPanel.models import Application, Job
from django.urls import reverse
import urllib.parse


def auth_view(request):
    signup_form = SignupForm()
    mode = request.GET.get("mode", "signup")

    return render(request, "auth.html", {
        "form": signup_form,
        "mode": mode
    })

def dashboard(request):
    return render(request, "dashboard.html")

def user_dashboard(request):
    posts = []
    search_results = []
    if request.user.is_authenticated:
        posts = Post.objects.all().order_by('-created_at')

        # handle user search via GET ?q=
        query = request.GET.get('q', '').strip()
        search_results = []
        if query:
            # search by username, first_name, last_name, email (case-insensitive contains)
            search_results = User.objects.filter(
                username__icontains=query
            ) | User.objects.filter(first_name__icontains=query) | User.objects.filter(last_name__icontains=query) | User.objects.filter(email__icontains=query)
            # avoid including current user in results
            search_results = search_results.exclude(pk=request.user.pk).distinct()
        else:
            search_results = []

        # profile and social stats
        profile = Profile.objects.filter(user=request.user).first()
        supporters_count = profile.supporters_count() if profile else 0
        supporting_count = profile.supports_count() if profile else 0
        recent_supporting = profile.get_supporting()[:5] if profile else []
        recent_supporters = profile.get_supporters()[:5] if profile else []

        # job applications and recommended jobs
        my_applications = Application.objects.filter(applicant=request.user).order_by('-applied_at')[:5]
        applications_count = Application.objects.filter(applicant=request.user).count()
        recommended_jobs = Job.objects.exclude(created_by=request.user).order_by('-created_at')[:5]

    return render(request, "UserDashboard.html", {
        "username": request.user.username,
        "posts": posts,
        "search_results": search_results,
        "query": request.GET.get('q', ''),
        "profile": profile if request.user.is_authenticated else None,
        "supporters_count": supporters_count if request.user.is_authenticated else 0,
        "supporting_count": supporting_count if request.user.is_authenticated else 0,
        "recent_supporting": recent_supporting if request.user.is_authenticated else [],
        "recent_supporters": recent_supporters if request.user.is_authenticated else [],
        "my_applications": my_applications if request.user.is_authenticated else [],
        "applications_count": applications_count if request.user.is_authenticated else 0,
        "recommended_jobs": recommended_jobs if request.user.is_authenticated else [],
    })


def user_search_api(request):
    """AJAX endpoint returning matching users for live suggestions."""
    if not request.user.is_authenticated:
        return JsonResponse({'results': []})

    q = request.GET.get('q', '').strip()
    results = []
    if q:
        qs = User.objects.filter(username__icontains=q) | User.objects.filter(first_name__icontains=q) | User.objects.filter(last_name__icontains=q) | User.objects.filter(email__icontains=q)
        qs = qs.exclude(pk=request.user.pk).distinct()[:10]
        for u in qs:
            results.append({
                'username': u.username,
                'full_name': u.get_full_name() or u.username,
                'profile_url': reverse('profile_detail', args=[u.username]),
                'image_url': (getattr(getattr(u, 'profile', None), 'profile_image', None).url
                              if getattr(getattr(u, 'profile', None), 'profile_image', None) else '')
            })

    return JsonResponse({'results': results})

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # set password manually because clean() only compares, not saves
            password = form.cleaned_data.get("password")
            if password:
                user.set_password(password)
            else:
                # If password is not provided, raise an error
                form.add_error('password', 'Password is required.')
                return render(request, "auth.html", {"form": form, "mode": "signup"})

            user.save()

            # Do not auto-login after signup; redirect user to the login form
            redirect_url = reverse('auth') + '?mode=login&created=1'
            return redirect(redirect_url)

    else:
        form = SignupForm()

    # Render the unified auth page with signup mode so the robot UI is used
    return render(request, "auth.html", {"form": form, "mode": "signup"})

def login_view(request):
    # preserve any next parameter from GET or default to accounts_home
    next_target = request.GET.get('next') or reverse('accounts_home')

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        # Try to authenticate with username first
        user = authenticate(request, username=username_or_email, password=password)

        # If that fails, try with email
        if user is None and '@' in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            return redirect(next_target)
        else:
            # Render the unified auth page in login mode with an error message
            form = SignupForm()
            return render(request, "auth.html", {"form": form, "mode": "login", "error": "Invalid username or password"})
    # For GET requests, show the unified auth page in login mode.
    form = SignupForm()
    created = request.GET.get('created')
    ctx = {"form": form, "mode": "login"}
    if created:
        ctx['created'] = created
    return render(request, "auth.html", ctx)
