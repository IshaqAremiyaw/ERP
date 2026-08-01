from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    # Dashboard router
    path("dashboard/", views.dashboard, name="dashboard"),

    # Auth
    path("login/", views.RoleAwareLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("register/", views.register_choice, name="register_choice"),
    path("register/applicant/", views.register_applicant, name="register_applicant"),
    path("register/hr/", views.register_hr, name="register_hr"),

    # Applicant portal
    path("applicant/dashboard/", views.applicant_dashboard, name="applicant_dashboard"),
    path("applicant/applications/", views.my_applications, name="my_applications"),
    path("applicant/applications/<int:pk>/", views.application_detail, name="application_detail"),
    path("applicant/applications/<int:pk>/withdraw/", views.withdraw_application, name="withdraw_application"),
    path("applicant/resume/", views.resume_upload, name="resume_upload"),

    # Jobs (public + apply)
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/apply/", views.apply_job, name="apply_job"),

    # HR dashboard & job management
    path("hr/dashboard/", views.hr_dashboard, name="hr_dashboard"),
    path("hr/jobs/", views.hr_job_list, name="hr_job_list"),
    path("hr/jobs/new/", views.job_create, name="job_create"),
    path("hr/jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("hr/jobs/<int:pk>/applications/", views.job_applications, name="job_applications"),
    path("hr/applications/<int:pk>/review/", views.application_review, name="application_review"),

    # Interviews
    path("hr/interviews/", views.interview_list, name="interview_list"),
    path("hr/interviews/schedule/<int:application_pk>/", views.interview_schedule, name="interview_schedule"),
    path("hr/interviews/<int:pk>/edit/", views.interview_update, name="interview_update"),

    # Analytics
    path("hr/analytics/", views.analytics, name="analytics"),

    # Employees
    path("hr/employees/", views.employee_list, name="employee_list"),
    path("hr/employees/<int:pk>/", views.employee_detail, name="employee_detail"),
]
