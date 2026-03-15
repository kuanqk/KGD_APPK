import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_deadlines(self):
    """
    Запускается каждый час через Celery Beat.
    1. Протоколы с дедлайном завтра → DEADLINE_SOON (responsible_user)
    2. Просроченные протоколы       → OVERDUE (responsible_user)
    Заменяет старую check_protocol_deadline из hearings/tasks.py.
    """
    from apps.hearings.models import HearingProtocol
    from apps.cases.models import CaseStatus
    from apps.audit.services import audit_log
    from apps.notifications.models import NotificationType
    from apps.notifications.services import notify

    try:
        today = timezone.now().date()
        from datetime import timedelta
        tomorrow = today + timedelta(days=1)

        # ── 1. Дедлайн завтра ─────────────────────────────────────────────
        soon_protocols = HearingProtocol.objects.filter(
            deadline_2days=tomorrow,
            case__status=CaseStatus.PROTOCOL_CREATED,
        ).select_related("case", "case__responsible_user")

        soon_count = 0
        for protocol in soon_protocols:
            responsible = protocol.case.responsible_user
            if responsible:
                from django.urls import reverse
                url = reverse("cases:detail", kwargs={"pk": protocol.case.pk})
                notify(
                    user=responsible,
                    notification_type=NotificationType.DEADLINE_SOON,
                    message=(
                        f"Завтра истекает срок оформления решения по делу "
                        f"{protocol.case.case_number} (протокол {protocol.protocol_number})."
                    ),
                    case=protocol.case,
                    url=url,
                )
            audit_log(
                user=None,
                action="protocol_deadline_soon",
                entity_type="protocol",
                entity_id=protocol.id,
                details={
                    "protocol_number": protocol.protocol_number,
                    "case_number": protocol.case.case_number,
                    "deadline": str(protocol.deadline_2days),
                },
            )
            soon_count += 1

        # ── 2. Просроченные ───────────────────────────────────────────────
        overdue_protocols = HearingProtocol.objects.filter(
            deadline_2days__lt=today,
            case__status=CaseStatus.PROTOCOL_CREATED,
        ).select_related("case", "case__responsible_user")

        overdue_count = 0
        for protocol in overdue_protocols:
            days_overdue = (today - protocol.deadline_2days).days
            responsible = protocol.case.responsible_user
            if responsible:
                from django.urls import reverse
                url = reverse("cases:detail", kwargs={"pk": protocol.case.pk})
                notify(
                    user=responsible,
                    notification_type=NotificationType.OVERDUE,
                    message=(
                        f"Просрочено! Решение по делу {protocol.case.case_number} "
                        f"не оформлено уже {days_overdue} дн. "
                        f"(дедлайн был {protocol.deadline_2days:%d.%m.%Y})."
                    ),
                    case=protocol.case,
                    url=url,
                )
            audit_log(
                user=None,
                action="protocol_deadline_overdue",
                entity_type="protocol",
                entity_id=protocol.id,
                details={
                    "protocol_number": protocol.protocol_number,
                    "case_number": protocol.case.case_number,
                    "deadline": str(protocol.deadline_2days),
                    "days_overdue": days_overdue,
                    "responsible_user_id": (
                        protocol.case.responsible_user_id or None
                    ),
                },
            )
            logger.warning(
                "Protocol overdue: %s case=%s days=%d",
                protocol.protocol_number,
                protocol.case.case_number,
                days_overdue,
            )
            overdue_count += 1

        logger.info(
            "check_deadlines: soon=%d overdue=%d checked_at=%s",
            soon_count, overdue_count, today,
        )
        return {"soon_count": soon_count, "overdue_count": overdue_count}

    except Exception as exc:
        logger.exception("check_deadlines failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_stagnant_cases(self):
    """
    Запускается ежедневно в 9:00 через Celery Beat.
    Находит дела без движения дольше порога и уведомляет руководителей офиса.
    Не дублирует: пропускает дела, по которым уведомление уже отправлено сегодня.
    """
    from apps.cases.services import get_stagnant_cases, StagnationSettings, FINAL_STATUSES
    from apps.cases.models import StagnationSettings as SS
    from apps.audit.services import audit_log
    from apps.notifications.models import Notification, NotificationType
    from apps.notifications.services import notify
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        settings_obj = SS.get()
        if not settings_obj.notify_reviewer:
            logger.info("check_stagnant_cases: notify_reviewer=False, skipping")
            return {"skipped": True}

        today = timezone.now().date()
        stagnant_qs = get_stagnant_cases()
        notified_count = 0
        skipped_count = 0

        for case in stagnant_qs:
            # Определяем получателей — reviewer того же подразделения (или все reviewer)
            reviewer_qs = User.objects.filter(role="reviewer", is_active=True)
            if case.department_id:
                dept_reviewers = reviewer_qs.filter(department_id=case.department_id)
                if dept_reviewers.exists():
                    reviewer_qs = dept_reviewers

            days_stagnant = (timezone.now() - case.last_activity_at).days

            for reviewer in reviewer_qs:
                # Защита от дублирования: уведомление за сегодня уже отправлено?
                already_sent = Notification.objects.filter(
                    user=reviewer,
                    case=case,
                    notification_type=NotificationType.STAGNANT,
                    created_at__date=today,
                ).exists()

                if already_sent:
                    skipped_count += 1
                    continue

                from django.urls import reverse
                url = reverse("cases:detail", kwargs={"pk": case.pk})
                notify(
                    user=reviewer,
                    notification_type=NotificationType.STAGNANT,
                    message=(
                        f"Дело {case.case_number} ({case.taxpayer.name}) "
                        f"без движения {days_stagnant} дн. "
                        f"Последняя активность: {case.last_activity_at:%d.%m.%Y}."
                    ),
                    case=case,
                    url=url,
                )
                notified_count += 1

            audit_log(
                user=None,
                action="stagnant_case_detected",
                entity_type="case",
                entity_id=case.id,
                details={
                    "case_number": case.case_number,
                    "days_stagnant": days_stagnant,
                    "status": case.status,
                },
            )

        logger.info(
            "check_stagnant_cases: found=%d notified=%d skipped=%d",
            stagnant_qs.count(), notified_count, skipped_count,
        )
        return {"notified": notified_count, "skipped": skipped_count}

    except Exception as exc:
        logger.exception("check_stagnant_cases failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_pending_emails(self):
    """
    Запускается каждые 30 минут.
    Отправляет email по непрочитанным уведомлениям старше 1 часа
    для пользователей с заполненным email-адресом.
    """
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.conf import settings as django_settings
    from apps.notifications.models import Notification

    try:
        threshold = timezone.now() - timedelta(hours=1)
        pending = (
            Notification.objects
            .filter(
                is_read=False,
                email_sent=False,
                created_at__lte=threshold,
            )
            .select_related("user", "case")
            .order_by("user_id", "created_at")
        )

        sent_count = 0
        ids_to_mark = []

        for notification in pending:
            user = notification.user
            if not user.email:
                ids_to_mark.append(notification.id)
                continue

            try:
                subject = f"АППК: {notification.get_notification_type_display()}"
                body = notification.message
                if notification.url:
                    site = getattr(django_settings, "SITE_URL", "http://localhost")
                    body += f"\n\nПерейти: {site}{notification.url}"

                send_mail(
                    subject=subject,
                    message=body,
                    from_email=getattr(
                        django_settings,
                        "DEFAULT_FROM_EMAIL",
                        "noreply@appk.kz",
                    ),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                ids_to_mark.append(notification.id)
                sent_count += 1
                logger.debug("Email sent to %s for notification %d", user.email, notification.id)
            except Exception as mail_exc:
                logger.warning(
                    "Failed to send email to %s: %s",
                    user.email, mail_exc,
                )

        if ids_to_mark:
            Notification.objects.filter(pk__in=ids_to_mark).update(email_sent=True)

        logger.info("send_pending_emails: sent=%d", sent_count)
        return {"sent_count": sent_count}

    except Exception as exc:
        logger.exception("send_pending_emails failed: %s", exc)
        raise self.retry(exc=exc)
