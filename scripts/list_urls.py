import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','KonnectAble.settings')
import django
django.setup()
from django.urls import get_resolver
resolver=get_resolver()
# reverse_dict keys can be bytes for unnamed; we iterate and print named ones
for name, val in resolver.reverse_dict.items():
    if isinstance(name, str):
        print(name)
