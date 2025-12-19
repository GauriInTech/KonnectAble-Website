from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Profile
from django.utils import timezone
from .forms import ProfileForm
from django.contrib.auth import get_user_model
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST

def profile_list(request):
    my_profile = None
    profiles = Profile.objects.none()
    if request.user.is_authenticated:
        my_profile, _ = Profile.objects.get_or_create(user=request.user)

        # Show only other profiles that are connected to the current user
        # i.e. profiles the user supports or that support the user
        profiles = (my_profile.get_supporting() | my_profile.get_supporters()).distinct()

        # exclude self
        profiles = profiles.exclude(user=request.user)

    # attach helpful attributes for template display
    for p in profiles:
        p.supports_count = p.supports_count()
        p.supporters_count = p.supporters_count()
        p.is_supported_by_me = False
        # lightweight badges
        try:
            age_days = (timezone.now() - p.created_at).days
        except Exception:
            age_days = 9999
        p.is_new = age_days < 7
        p.is_top_supported = p.supporters_count > 10
        if my_profile:
            p.is_supported_by_me = p in my_profile.get_supporting()

    return render(request, 'profiles/profile_list.html', {'profiles': profiles})


def profile_detail(request, username):
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    profile, created = Profile.objects.get_or_create(user=user)
    # annotate profile with counts and whether the current user supports them
    profile.supports_count = profile.supports_count()
    profile.supporters_count = profile.supporters_count()
    profile.supporters_preview = profile.get_supporters()[:5]
    profile.supporting_preview = profile.get_supporting()[:5]
    profile.is_supported_by_me = False
    # badges for profile detail
    try:
        age_days = (timezone.now() - profile.created_at).days
    except Exception:
        age_days = 9999
    profile.is_new = age_days < 7
    profile.is_top_supported = profile.supporters_count > 10
    if request.user.is_authenticated and request.user != user:
        my_profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.is_supported_by_me = profile in my_profile.get_supporting()
    # attach jobPanel related profiles if they exist
    applicant_profile = None
    hiring_profile = None
    try:
        from jobPanel.models import ApplicantProfile, HiringPartnerProfile
        applicant_profile = ApplicantProfile.objects.filter(user=user).first()
        hiring_profile = HiringPartnerProfile.objects.filter(user=user).first()
    except Exception:
        # jobPanel app may not be available yet
        applicant_profile = None
        hiring_profile = None

    return render(request, 'profiles/profile_detail.html', {
        'profile': profile,
        'applicant_profile': applicant_profile,
        'hiring_profile': hiring_profile,
    })


@login_required
def profile_update(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_detail', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profiles/profile_form.html', {'form': form})


@login_required
def my_profile(request):
    """Redirect the authenticated user to their own profile detail page."""
    return redirect('profile_detail', username=request.user.username)


@login_required
@require_POST
def toggle_support(request, username):
    """Toggle support (follow/unfollow) from the request.user to the given username's profile.

    Redirects back to the referring page or the target profile detail page.
    """
    User = get_user_model()
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        # can't support yourself
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('profile_detail', args=[username])))

    # ensure profiles exist
    actor_profile, _ = Profile.objects.get_or_create(user=request.user)
    target_profile, _ = Profile.objects.get_or_create(user=target_user)

    actor_profile.toggle_support(target_profile)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('profile_detail', args=[username])))


def supporters_list(request, username):
    """Show the full list of profiles that support (follow) the given user's profile."""
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    # queryset of Profile objects that support this profile
    supporters = profile.get_supporters()

    return render(request, 'profiles/supporters_list.html', {
        'profile': profile,
        'supporters': supporters,
    })


def supporting_list(request, username):
    """Show the full list of profiles that the given user's profile is supporting (following)."""
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    supporting = profile.get_supporting()

    return render(request, 'profiles/supporting_list.html', {
        'profile': profile,
        'supporting': supporting,
    })
