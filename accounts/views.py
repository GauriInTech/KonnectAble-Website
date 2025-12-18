from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import authenticate, login  # type: ignore
from .forms import SignupForm
from django.http import HttpResponse  # type: ignore
from posts.models import Post
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
    if request.user.is_authenticated:
        if request.method == 'POST':
            content = request.POST.get('content')
            image = request.FILES.get('image')

            if content or image:
                Post.objects.create(
                    user=request.user,
                    content=content,
                    image=image
                )
                return redirect('accounts_home')

        posts = Post.objects.all().order_by('-created_at')

    return render(request, "UserDashboard.html", {"username": request.user.username, "posts": posts})

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # set password manually because clean() only compares, not saves
            password = form.cleaned_data.get("password")
            user.set_password(password)

            user.save()

            # Do not auto-login after signup; redirect user to the login page
            redirect_url = reverse('login') + '?created=1'
            return redirect(redirect_url)

    else:
        form = SignupForm()

    # Render the unified auth page with signup mode so the robot UI is used
    return render(request, "auth.html", {"form": form, "mode": "signup"})

def login_view(request):
    # preserve any next parameter from GET or default to accounts_home
    next_target = request.GET.get('next') or reverse('accounts_home')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

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
