from django import forms
from .models import Message, Call


class MessageForm(forms.ModelForm):
    """Form for creating and sending messages"""
    
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'image', 'file']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control chat-input',
                'placeholder': 'Type a message...',
                'rows': 2,
                'autocomplete': 'off',
            }),
            'message_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'imageInput',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'fileInput',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        message_type = cleaned_data.get('message_type')
        image = cleaned_data.get('image')
        file = cleaned_data.get('file')

        # Validate that appropriate content is provided for message type
        if message_type == 'text' and not content:
            raise forms.ValidationError('Text message must have content.')
        if message_type == 'image' and not image:
            raise forms.ValidationError('Image message must have an image.')
        if message_type == 'file' and not file:
            raise forms.ValidationError('File message must have a file.')

        return cleaned_data


class CallForm(forms.ModelForm):
    """Form for initiating calls"""
    
    class Meta:
        model = Call
        fields = ['call_type']
        widgets = {
            'call_type': forms.RadioSelect(attrs={
                'class': 'form-check-input',
            }),
        }
