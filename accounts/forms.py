from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': 'Enter password'}
    ))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': 'Confirm password'}
    ))
    role = forms.ChoiceField(choices=User.Roles.choices, widget=forms.RadioSelect(
        attrs={'class': 'form-check-input'}
    ), label='Select Account Type')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'age', 'sex', 
                  'phone_number', 'region', 'country', 'professional_qualification', 'role']
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'age': 'Age',
            'sex': 'Gender',
            'phone_number': 'Phone Number',
            'region': 'Region/State',
            'country': 'Country',
            'professional_qualification': 'Professional Qualification',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter your age', 'min': '13', 'max': '120'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number', 'type': 'tel'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Lagos, California'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter country'}),
            'professional_qualification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bachelor\'s Degree'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'age', 'sex', 'phone_number', 
                  'region', 'country', 'professional_qualification', 'bio', 'profile_picture']
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'age': 'Age',
            'sex': 'Gender',
            'phone_number': 'Phone Number',
            'region': 'Region/State',
            'country': 'Country',
            'professional_qualification': 'Professional Qualification',
            'bio': 'About You',
            'profile_picture': 'Profile Picture'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter your age', 'min': '13', 'max': '120'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number', 'type': 'tel'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Lagos, California'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter country'}),
            'professional_qualification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bachelor\'s Degree'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Tell us about yourself', 'rows': 4}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }