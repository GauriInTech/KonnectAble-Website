from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import authenticate, login  # type: ignore
from .forms import SignupForm
from django.http import HttpResponse  # type: ignore




def home(request):
    return render(request, "home.html", {"username": request.user.username})

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # set password manually because clean() only compares, not saves
            password = form.cleaned_data.get("password")
            user.set_password(password)

            user.save()

            login(request, user)  # auto login after signup
            return redirect('accounts_home')

    else:
        form = SignupForm()

    return render(request, "signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('accounts_home')   # redirect after login
        else:
            return render(request, "login.html", {"error": "Invalid username or password"})

    return render(request, "login.html")
