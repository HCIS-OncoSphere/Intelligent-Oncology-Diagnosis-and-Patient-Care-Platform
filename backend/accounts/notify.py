"""In-app notifications and e-mail. Without SMTP settings, e-mails are printed to the server console
(see EMAIL_BACKEND in settings), so nothing breaks while developing."""
import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification, User

log = logging.getLogger(__name__)


def notify(user, title, message="", link=""):
    return Notification.objects.create(user=user, title=title[:120], message=message[:500], link=link[:120])


def notify_admins(title, message="", link=""):
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        notify(admin, title, message, link)


def email_user(user, subject, body):
    """Never raises: a mail server problem must not undo an approval or a registration."""
    if not user.email:
        return False
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return True
    except Exception:  # noqa: BLE001
        log.exception("Could not send e-mail to user %s", user.pk)
        return False
