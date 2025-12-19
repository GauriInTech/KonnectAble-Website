from django import forms
from .models import ApplicantProfile, Job, Application


ROLE_CHOICES = (
    ('applicant', 'Applicant'),
    ('hiring', 'Hiring Partner'),
)


class RoleSelectionForm(forms.Form):
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)


class ApplicantProfileForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ['headline', 'location', 'skills', 'experience', 'resume']


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'company', 'description']


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'resume']
