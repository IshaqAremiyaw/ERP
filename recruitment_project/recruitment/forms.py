from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (
    User, ApplicantProfile, JobPosting, Application, Interview,
)


class ApplicantRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=False, max_length=20)
    skills = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}),
                              help_text="Comma-separated, e.g. Python, SQL, Communication")
    experience_years = forms.IntegerField(required=False, min_value=0, initial=0)

    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.APPLICANT
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        if commit:
            user.save()
            ApplicantProfile.objects.create(
                user=user,
                skills=self.cleaned_data.get("skills", ""),
                experience_years=self.cleaned_data.get("experience_years") or 0,
            )
        return user


class HRRegistrationForm(UserCreationForm):
    """Separate signup path for HR staff (in production you'd gate this behind an invite code)."""
    email = forms.EmailField(required=True)
    department = forms.CharField(required=False, max_length=100)
    invite_code = forms.CharField(
        required=True, help_text="Ask your admin for the HR signup code."
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    HR_INVITE_CODE = "HR-ONBOARD-2026"  # replace with an env var / DB-backed code in production

    def clean_invite_code(self):
        code = self.cleaned_data["invite_code"]
        if code != self.HR_INVITE_CODE:
            raise forms.ValidationError("Invalid HR invite code.")
        return code

    def save(self, commit=True):
        from .models import HRProfile
        user = super().save(commit=False)
        user.role = User.Role.HR
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            HRProfile.objects.create(user=user, department=self.cleaned_data.get("department", ""))
        return user


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ["resume", "skills", "experience_years", "linkedin_url", "address"]


class JobPostingForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = [
            "title", "description", "requirements", "department", "location",
            "employment_type", "salary_min", "salary_max", "vacancies",
            "status", "application_deadline",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "application_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["cover_letter", "resume_snapshot"]
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 5})}


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["status", "hr_notes", "rating"]
        widgets = {"hr_notes": forms.Textarea(attrs={"rows": 3})}


class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ["mode", "scheduled_at", "location_or_link", "outcome", "feedback"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "feedback": forms.Textarea(attrs={"rows": 3}),
        }
