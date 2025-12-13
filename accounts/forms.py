from django import forms  # type: ignore
from .models import User  # type: ignore

class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Enter password',
                'aria-label': 'Password',
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Confirm password',
                'aria-label': 'Confirm password',
            }
        )
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Your name',
                'aria-label': 'Full Name',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email address',
                'aria-label': 'Email',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data
