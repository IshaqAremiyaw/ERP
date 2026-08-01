"""
Recruitment / Job Application System - Data Models
====================================================

Covers:
1. Applicant registration, job applications, and application tracking.
2. HR full control: post/edit/close jobs, review applications, change
   statuses, schedule interviews, and leave internal notes.

Built with Django's ORM. Assumes `django.contrib.auth` custom user model
setup (AUTH_USER_MODEL = 'app_name.User' in settings.py).
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# 1. USER & ROLES
# ---------------------------------------------------------------------------

class User(AbstractUser):
    """Base user. Role determines which profile & permissions apply."""

    class Role(models.TextChoices):
        APPLICANT = "APPLICANT", "Applicant"
        HR = "HR", "HR"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT)
    phone_number = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_hr(self):
        return self.role == self.Role.HR

    def is_applicant(self):
        return self.role == self.Role.APPLICANT

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class ApplicantProfile(models.Model):
    """Extended profile for applicant registration."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="applicant_profile")
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    resume = models.FileField(
        upload_to="resumes/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
        null=True, blank=True,
    )
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    experience_years = models.PositiveSmallIntegerField(default=0)
    linkedin_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Applicant: {self.user}"


class HRProfile(models.Model):
    """Extended profile for HR staff."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="hr_profile")
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    can_publish_jobs = models.BooleanField(default=True)
    can_manage_all_applications = models.BooleanField(
        default=True, help_text="Overrides visibility to only own postings if False"
    )

    def __str__(self):
        return f"HR: {self.user}"


# ---------------------------------------------------------------------------
# 2. JOB POSTINGS (HR CONTROLLED)
# ---------------------------------------------------------------------------

class JobPosting(models.Model):
    """A job opening, fully controlled by HR."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    department = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=[("FULL_TIME", "Full Time"), ("PART_TIME", "Part Time"),
                  ("CONTRACT", "Contract"), ("INTERN", "Internship")],
        default="FULL_TIME",
    )
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vacancies = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="job_postings", limit_choices_to={"role": User.Role.HR},
    )
    application_deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def is_open(self):
        if self.status != self.Status.OPEN:
            return False
        if self.application_deadline and timezone.now() > self.application_deadline:
            return False
        return True

    def __str__(self):
        return f"{self.title} ({self.status})"


# ---------------------------------------------------------------------------
# 3. APPLICATIONS (APPLICANT SUBMITS, TRACKS)
# ---------------------------------------------------------------------------

class Application(models.Model):
    """An applicant's application to a specific job posting."""

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED", "Interview Scheduled"
        OFFERED = "OFFERED", "Offered"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        HIRED = "HIRED", "Hired"

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="applications", limit_choices_to={"role": User.Role.APPLICANT},
    )
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="applications")
    cover_letter = models.TextField(blank=True)
    resume_snapshot = models.FileField(
        upload_to="application_resumes/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
        null=True, blank=True,
        help_text="Resume as of the time of this application",
    )
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.SUBMITTED)

    # HR-side control fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_applications", limit_choices_to={"role": User.Role.HR},
    )
    hr_notes = models.TextField(blank=True, help_text="Internal notes, not visible to applicant")
    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1-5 HR rating")

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        unique_together = ("applicant", "job_posting")  # one application per job

    def withdraw(self):
        self.status = self.Status.WITHDRAWN
        self.save(update_fields=["status", "updated_at"])

    def set_status(self, new_status, changed_by, notes=""):
        """HR-controlled status transition, logged to history."""
        old_status = self.status
        self.status = new_status
        self.reviewed_by = changed_by
        self.save(update_fields=["status", "reviewed_by", "updated_at"])
        ApplicationStatusHistory.objects.create(
            application=self, from_status=old_status, to_status=new_status,
            changed_by=changed_by, notes=notes,
        )

    def __str__(self):
        return f"{self.applicant} -> {self.job_posting} [{self.status}]"


class ApplicationStatusHistory(models.Model):
    """Audit trail so applicants (and HR) can track how status changed over time."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=25, blank=True)
    to_status = models.CharField(max_length=25)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.application_id}: {self.from_status} -> {self.to_status}"


class Interview(models.Model):
    """HR schedules and manages interviews for an application."""

    class Mode(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        ONSITE = "ONSITE", "Onsite"
        PHONE = "PHONE", "Phone"

    class Outcome(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"
        NO_SHOW = "NO_SHOW", "No Show"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="scheduled_interviews", limit_choices_to={"role": User.Role.HR},
    )
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ONLINE)
    scheduled_at = models.DateTimeField()
    location_or_link = models.CharField(max_length=255, blank=True)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.PENDING)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"Interview for {self.application} at {self.scheduled_at}"


# ---------------------------------------------------------------------------
# 4. EMPLOYEE MANAGEMENT (HR CONVERTS A HIRED APPLICANT)
# ---------------------------------------------------------------------------

class Employee(models.Model):
    """Created by HR once an application reaches HIRED status."""

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        TERMINATED = "TERMINATED", "Terminated"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="employee_record")
    application = models.OneToOneField(
        Application, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employee_record",
    )
    employee_id = models.CharField(max_length=20, unique=True)
    job_title = models.CharField(max_length=150)
    department = models.CharField(max_length=100, blank=True)
    date_joined = models.DateField(default=timezone.now)
    status = models.CharField(max_length=15, choices=EmploymentStatus.choices,
                               default=EmploymentStatus.ACTIVE)
    managed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_employees", limit_choices_to={"role": User.Role.HR},
    )

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.user} - {self.job_title} ({self.status})"
