from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from .models import (
    User, ApplicantProfile, HRProfile, JobPosting,
    Application, ApplicationStatusHistory, Interview,
)


class RecruitmentFlowTest(TestCase):
    def setUp(self):
        # --- Registration ---
        self.hr_user = User.objects.create_user(
            username="hr_jane", password="pass1234", role=User.Role.HR,
        )
        HRProfile.objects.create(user=self.hr_user, department="Engineering")

        self.applicant_user = User.objects.create_user(
            username="applicant_sam", password="pass1234", role=User.Role.APPLICANT,
        )
        ApplicantProfile.objects.create(
            user=self.applicant_user, skills="Python, Django", experience_years=3,
        )

    def test_hr_creates_and_controls_job_posting(self):
        job = JobPosting.objects.create(
            title="Backend Engineer",
            description="Build APIs",
            posted_by=self.hr_user,
            status=JobPosting.Status.OPEN,
            application_deadline=timezone.now() + timedelta(days=7),
        )
        self.assertTrue(job.is_open())

        # HR closes it
        job.status = JobPosting.Status.CLOSED
        job.save()
        self.assertFalse(job.is_open())

    def test_applicant_applies_and_tracks_application(self):
        job = JobPosting.objects.create(
            title="Backend Engineer", description="Build APIs",
            posted_by=self.hr_user, status=JobPosting.Status.OPEN,
        )

        application = Application.objects.create(
            applicant=self.applicant_user, job_posting=job,
            cover_letter="I'd love to join.",
        )
        self.assertEqual(application.status, Application.Status.SUBMITTED)

        # Duplicate application should fail (one per job)
        with self.assertRaises(Exception):
            Application.objects.create(applicant=self.applicant_user, job_posting=job)

    def test_hr_reviews_and_changes_status_with_history(self):
        job = JobPosting.objects.create(
            title="Backend Engineer", description="Build APIs",
            posted_by=self.hr_user, status=JobPosting.Status.OPEN,
        )
        application = Application.objects.create(applicant=self.applicant_user, job_posting=job)

        application.set_status(
            Application.Status.UNDER_REVIEW, changed_by=self.hr_user, notes="Looks promising"
        )
        application.set_status(
            Application.Status.SHORTLISTED, changed_by=self.hr_user, notes="Strong Python background"
        )

        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.SHORTLISTED)
        self.assertEqual(application.reviewed_by, self.hr_user)

        history = list(application.status_history.all())
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].to_status, Application.Status.UNDER_REVIEW)
        self.assertEqual(history[1].to_status, Application.Status.SHORTLISTED)

    def test_hr_schedules_interview(self):
        job = JobPosting.objects.create(
            title="Backend Engineer", description="Build APIs",
            posted_by=self.hr_user, status=JobPosting.Status.OPEN,
        )
        application = Application.objects.create(applicant=self.applicant_user, job_posting=job)
        application.set_status(Application.Status.INTERVIEW_SCHEDULED, changed_by=self.hr_user)

        interview = Interview.objects.create(
            application=application, scheduled_by=self.hr_user,
            mode=Interview.Mode.ONLINE, scheduled_at=timezone.now() + timedelta(days=2),
            location_or_link="https://meet.example.com/abc",
        )
        self.assertEqual(interview.outcome, Interview.Outcome.PENDING)

        interview.outcome = Interview.Outcome.PASSED
        interview.feedback = "Strong technical answers"
        interview.save()
        self.assertEqual(application.interviews.count(), 1)

    def test_applicant_can_withdraw(self):
        job = JobPosting.objects.create(
            title="Backend Engineer", description="Build APIs",
            posted_by=self.hr_user, status=JobPosting.Status.OPEN,
        )
        application = Application.objects.create(applicant=self.applicant_user, job_posting=job)
        application.withdraw()
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.WITHDRAWN)


class WebViewsTest(TestCase):
    """Smoke tests hitting real URLs through the Django test client, Bootstrap templates included."""

    def setUp(self):
        self.hr_user = User.objects.create_user(
            username="hr_jane", password="pass1234", role=User.Role.HR,
        )
        HRProfile.objects.create(user=self.hr_user, department="Engineering")
        self.applicant_user = User.objects.create_user(
            username="applicant_sam", password="pass1234", role=User.Role.APPLICANT,
        )
        ApplicantProfile.objects.create(user=self.applicant_user)
        self.job = JobPosting.objects.create(
            title="Backend Engineer", description="Build APIs",
            posted_by=self.hr_user, status=JobPosting.Status.OPEN,
        )

    def test_public_job_list_loads(self):
        response = self.client.get("/jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Engineer")

    def test_login_page_loads(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_applicant_dashboard_after_login(self):
        self.client.login(username="applicant_sam", password="pass1234")
        response = self.client.get("/dashboard/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Dashboard".split()[0])  # basic sanity check

    def test_hr_dashboard_after_login(self):
        self.client.login(username="hr_jane", password="pass1234")
        response = self.client.get("/hr/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HR Dashboard")

    def test_applicant_cannot_access_hr_dashboard(self):
        self.client.login(username="applicant_sam", password="pass1234")
        response = self.client.get("/hr/dashboard/")
        self.assertEqual(response.status_code, 302)  # blocked by hr_required

    def test_hr_analytics_page_loads(self):
        self.client.login(username="hr_jane", password="pass1234")
        response = self.client.get("/hr/analytics/")
        self.assertEqual(response.status_code, 200)

    def test_apply_flow_via_client(self):
        self.client.login(username="applicant_sam", password="pass1234")
        response = self.client.post(f"/jobs/{self.job.pk}/apply/", {
            "cover_letter": "I'd love this role.",
        })
        self.assertEqual(response.status_code, 302)  # redirect to my_applications
        self.assertTrue(
            Application.objects.filter(applicant=self.applicant_user, job_posting=self.job).exists()
        )
