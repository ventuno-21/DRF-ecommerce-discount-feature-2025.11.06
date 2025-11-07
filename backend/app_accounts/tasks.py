from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


@shared_task
def send_registration_email(to_email, context):
    """
    Send registration confirmation email in background.
    `context` can include variables for template rendering.
    """
    subject = context.get("subject", "Registration confirmation")
    message = render_to_string("emails/registration_email.txt", context)
    html_message = render_to_string("emails/registration_email.html", context)
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
        html_message=html_message,
    )


@shared_task
def send_password_reset_email(to_email, context):
    """
    Send password reset email in background.
    """
    subject = context.get("subject", "Password reset")
    message = render_to_string("emails/password_reset_email.txt", context)
    html_message = render_to_string("emails/password_reset_email.html", context)
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
        html_message=html_message,
    )
