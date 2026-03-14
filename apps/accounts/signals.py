import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    from apps.audit.services import audit_log
    audit_log(
        user=user,
        action="user_login",
        entity_type="user",
        entity_id=user.id,
        details={"ip": _get_client_ip(request)},
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is None:
        return
    from apps.audit.services import audit_log
    audit_log(
        user=user,
        action="user_logout",
        entity_type="user",
        entity_id=user.id,
        details={"ip": _get_client_ip(request)},
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    logger.warning(
        "Failed login attempt for username=%s ip=%s",
        credentials.get("username"),
        _get_client_ip(request),
    )


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
