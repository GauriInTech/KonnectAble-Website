from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from profiles import views as profile_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('my-profile/', profile_views.my_profile, name='my_profile_root'),
    path('dashboard/', RedirectView.as_view(pattern_name='accounts_home', permanent=False)),
    path('profiles/', include('profiles.urls')),
    path('posts/', include('posts.urls')),   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
