from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Application, ApplicationStatusHistory, Interview


@receiver(post_save, sender=Application)
def notify_application_submitted(sender, instance, created, **kwargs):
    if created:
        send_mail(
            subject=f"Application received: {instance.job_posting.title}",
            message=(
                f"Hi {instance.applicant.get_full_name() or instance.applicant.username},\n\n"
                f"We've received your application for '{instance.job_posting.title}'. "
                f"You can track its status anytime from your dashboard.\n\n— Recruitment Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.applicant.email] if instance.applicant.email else [],
            fail_silently=True,
        )


@receiver(post_save, sender=ApplicationStatusHistory)
def notify_status_change(sender, instance, created, **kwargs):
    if created:
        application = instance.application
        send_mail(
            subject=f"Application update: {application.job_posting.title}",
            message=(
                f"Hi {application.applicant.get_full_name() or application.applicant.username},\n\n"
                f"Your application for '{application.job_posting.title}' is now: "
                f"{instance.get_to_status_display()}.\n\n— Recruitment Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.applicant.email] if application.applicant.email else [],
            fail_silently=True,
        )


@receiver(post_save, sender=Interview)
def notify_interview_scheduled(sender, instance, created, **kwargs):
    if created:
        applicant = instance.application.applicant
        send_mail(
            subject=f"Interview scheduled: {instance.application.job_posting.title}",
            message=(
                f"Hi {applicant.get_full_name() or applicant.username},\n\n"
                f"Your interview for '{instance.application.job_posting.title}' is scheduled "
                f"for {instance.scheduled_at.strftime('%Y-%m-%d %H:%M')} ({instance.mode}).\n"
                f"Details: {instance.location_or_link or 'to be confirmed'}\n\n— Recruitment Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[applicant.email] if applicant.email else [],
            fail_silently=True,
        )
