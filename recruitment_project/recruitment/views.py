from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    ApplicantRegistrationForm, HRRegistrationForm, ResumeUploadForm,
    JobPostingForm, ApplicationForm, ApplicationStatusForm, InterviewForm,
)
from .models import (
    User, JobPosting, Application, ApplicationStatusHistory, Interview, Employee,
)


# ---------------------------------------------------------------------------
# Helpers / access control
# ---------------------------------------------------------------------------

def is_hr(user):
    return user.is_authenticated and user.is_hr()


def is_applicant(user):
    return user.is_authenticated and user.is_applicant()


hr_required = user_passes_test(is_hr, login_url="login")
applicant_required = user_passes_test(is_applicant, login_url="login")


# ---------------------------------------------------------------------------
# 🏠 Dashboard (routes by role)
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    if request.user.is_hr():
        return redirect("hr_dashboard")
    return redirect("applicant_dashboard")


# ---------------------------------------------------------------------------
# 🔐 Login & Registration
# ---------------------------------------------------------------------------

class RoleAwareLoginView(LoginView):
    template_name = "recruitment/login.html"

    def get_success_url(self):
        return "/dashboard/"


def register_choice(request):
    return render(request, "recruitment/register_choice.html")


def register_applicant(request):
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your applicant account is ready.")
            return redirect("applicant_dashboard")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "recruitment/register_applicant.html", {"form": form})


def register_hr(request):
    if request.method == "POST":
        form = HRRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "HR account created.")
            return redirect("hr_dashboard")
    else:
        form = HRRegistrationForm()
    return render(request, "recruitment/register_hr.html", {"form": form})


# ---------------------------------------------------------------------------
# 👤 Applicant Portal
# ---------------------------------------------------------------------------

@login_required
@applicant_required
def applicant_dashboard(request):
    applications = Application.objects.filter(applicant=request.user).select_related("job_posting")
    stats = {
        "total": applications.count(),
        "active": applications.exclude(
            status__in=[Application.Status.REJECTED, Application.Status.WITHDRAWN]
        ).count(),
        "interviews": Interview.objects.filter(application__applicant=request.user).count(),
        "offers": applications.filter(status=Application.Status.OFFERED).count(),
    }
    return render(request, "recruitment/applicant_dashboard.html", {
        "applications": applications[:5], "stats": stats,
    })


@login_required
@applicant_required
def my_applications(request):
    applications = Application.objects.filter(applicant=request.user).select_related("job_posting")
    return render(request, "recruitment/my_applications.html", {"applications": applications})


@login_required
@applicant_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk, applicant=request.user)
    history = application.status_history.all()
    interviews = application.interviews.all()
    return render(request, "recruitment/application_detail.html", {
        "application": application, "history": history, "interviews": interviews,
    })


@login_required
@applicant_required
def withdraw_application(request, pk):
    application = get_object_or_404(Application, pk=pk, applicant=request.user)
    if request.method == "POST":
        application.withdraw()
        messages.info(request, "Application withdrawn.")
    return redirect("my_applications")


# ---------------------------------------------------------------------------
# 📄 Resume Upload
# ---------------------------------------------------------------------------

@login_required
@applicant_required
def resume_upload(request):
    profile = request.user.applicant_profile
    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Resume and profile updated.")
            return redirect("applicant_dashboard")
    else:
        form = ResumeUploadForm(instance=profile)
    return render(request, "recruitment/resume_upload.html", {"form": form})


# ---------------------------------------------------------------------------
# 💼 Job Listings & 📝 Apply for Jobs
# ---------------------------------------------------------------------------

def job_list(request):
    jobs = JobPosting.objects.filter(status=JobPosting.Status.OPEN)
    query = request.GET.get("q")
    if query:
        jobs = jobs.filter(Q(title__icontains=query) | Q(department__icontains=query) |
                            Q(location__icontains=query))
    jobs = [j for j in jobs if j.is_open()]
    return render(request, "recruitment/job_list.html", {"jobs": jobs, "query": query or ""})


def job_detail(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    already_applied = False
    if request.user.is_authenticated and request.user.is_applicant():
        already_applied = Application.objects.filter(applicant=request.user, job_posting=job).exists()
    return render(request, "recruitment/job_detail.html", {
        "job": job, "already_applied": already_applied,
    })


@login_required
@applicant_required
def apply_job(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    if not job.is_open():
        messages.error(request, "This job is no longer accepting applications.")
        return redirect("job_detail", pk=pk)
    if Application.objects.filter(applicant=request.user, job_posting=job).exists():
        messages.warning(request, "You've already applied for this job.")
        return redirect("job_detail", pk=pk)

    if request.method == "POST":
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.job_posting = job
            if not application.resume_snapshot and hasattr(request.user, "applicant_profile"):
                application.resume_snapshot = request.user.applicant_profile.resume
            application.save()
            messages.success(request, "Application submitted!")
            return redirect("my_applications")
    else:
        form = ApplicationForm()
    return render(request, "recruitment/apply_job.html", {"form": form, "job": job})


# ---------------------------------------------------------------------------
# 📊 HR Dashboard
# ---------------------------------------------------------------------------

@login_required
@hr_required
def hr_dashboard(request):
    stats = {
        "open_jobs": JobPosting.objects.filter(status=JobPosting.Status.OPEN).count(),
        "total_jobs": JobPosting.objects.count(),
        "total_applications": Application.objects.count(),
        "pending_review": Application.objects.filter(
            status__in=[Application.Status.SUBMITTED, Application.Status.UNDER_REVIEW]
        ).count(),
        "interviews_upcoming": Interview.objects.filter(
            scheduled_at__gte=timezone.now(), outcome=Interview.Outcome.PENDING
        ).count(),
        "employees": Employee.objects.filter(status=Employee.EmploymentStatus.ACTIVE).count(),
    }
    recent_applications = Application.objects.select_related(
        "applicant", "job_posting"
    ).order_by("-applied_at")[:8]
    return render(request, "recruitment/hr_dashboard.html", {
        "stats": stats, "recent_applications": recent_applications,
    })


@login_required
@hr_required
def hr_job_list(request):
    jobs = JobPosting.objects.annotate(app_count=Count("applications"))
    return render(request, "recruitment/hr_job_list.html", {"jobs": jobs})


@login_required
@hr_required
def job_create(request):
    if request.method == "POST":
        form = JobPostingForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            messages.success(request, "Job posting created.")
            return redirect("hr_job_list")
    else:
        form = JobPostingForm()
    return render(request, "recruitment/job_form.html", {"form": form, "mode": "Create"})


@login_required
@hr_required
def job_edit(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    if request.method == "POST":
        form = JobPostingForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job posting updated.")
            return redirect("hr_job_list")
    else:
        form = JobPostingForm(instance=job)
    return render(request, "recruitment/job_form.html", {"form": form, "mode": "Edit", "job": job})


@login_required
@hr_required
def job_applications(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    applications = job.applications.select_related("applicant").all()
    return render(request, "recruitment/job_applications.html", {"job": job, "applications": applications})


@login_required
@hr_required
def application_review(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.method == "POST":
        form = ApplicationStatusForm(request.POST, instance=application)
        if form.is_valid():
            old_status = application.status
            updated = form.save(commit=False)
            updated.reviewed_by = request.user
            updated.save()
            if updated.status != old_status:
                ApplicationStatusHistory.objects.create(
                    application=updated, from_status=old_status, to_status=updated.status,
                    changed_by=request.user,
                )
            if updated.status == Application.Status.HIRED and not hasattr(updated, "employee_record"):
                Employee.objects.create(
                    user=updated.applicant,
                    application=updated,
                    employee_id=f"EMP-{updated.applicant.id:04d}",
                    job_title=updated.job_posting.title,
                    department=updated.job_posting.department,
                    managed_by=request.user,
                )
                messages.info(request, "Applicant converted to an employee record.")
            messages.success(request, "Application updated.")
            return redirect("job_applications", pk=application.job_posting.pk)
    else:
        form = ApplicationStatusForm(instance=application)
    interviews = application.interviews.all()
    return render(request, "recruitment/application_review.html", {
        "application": application, "form": form, "interviews": interviews,
    })


# ---------------------------------------------------------------------------
# 📅 Interview Scheduling
# ---------------------------------------------------------------------------

@login_required
@hr_required
def interview_list(request):
    interviews = Interview.objects.select_related(
        "application__applicant", "application__job_posting"
    ).order_by("scheduled_at")
    return render(request, "recruitment/interview_list.html", {"interviews": interviews})


@login_required
@hr_required
def interview_schedule(request, application_pk):
    application = get_object_or_404(Application, pk=application_pk)
    if request.method == "POST":
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.scheduled_by = request.user
            interview.save()
            application.set_status(Application.Status.INTERVIEW_SCHEDULED, changed_by=request.user)
            messages.success(request, "Interview scheduled.")
            return redirect("interview_list")
    else:
        form = InterviewForm()
    return render(request, "recruitment/interview_schedule.html", {
        "form": form, "application": application,
    })


@login_required
@hr_required
def interview_update(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if request.method == "POST":
        form = InterviewForm(request.POST, instance=interview)
        if form.is_valid():
            form.save()
            messages.success(request, "Interview updated.")
            return redirect("interview_list")
    else:
        form = InterviewForm(instance=interview)
    return render(request, "recruitment/interview_schedule.html", {
        "form": form, "application": interview.application, "edit_mode": True,
    })


# ---------------------------------------------------------------------------
# 📈 Recruitment Analytics
# ---------------------------------------------------------------------------

@login_required
@hr_required
def analytics(request):
    status_breakdown = (
        Application.objects.values("status").annotate(count=Count("id")).order_by("-count")
    )
    jobs_by_applications = (
        JobPosting.objects.annotate(app_count=Count("applications"))
        .order_by("-app_count")[:8]
    )
    funnel_labels = [s.label for s in Application.Status]
    funnel_counts = [
        Application.objects.filter(status=s.value).count() for s in Application.Status
    ]
    return render(request, "recruitment/analytics.html", {
        "status_breakdown": status_breakdown,
        "jobs_by_applications": jobs_by_applications,
        "funnel_labels": funnel_labels,
        "funnel_counts": funnel_counts,
        "total_jobs": JobPosting.objects.count(),
        "total_applications": Application.objects.count(),
        "total_hired": Application.objects.filter(status=Application.Status.HIRED).count(),
    })


# ---------------------------------------------------------------------------
# 👥 Employee Management
# ---------------------------------------------------------------------------

@login_required
@hr_required
def employee_list(request):
    employees = Employee.objects.select_related("user").all()
    return render(request, "recruitment/employee_list.html", {"employees": employees})


@login_required
@hr_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in Employee.EmploymentStatus.values:
            employee.status = new_status
            employee.save()
            messages.success(request, "Employee status updated.")
    return render(request, "recruitment/employee_detail.html", {"employee": employee})
