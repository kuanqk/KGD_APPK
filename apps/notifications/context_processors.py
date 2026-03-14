from .models import Notification


def notifications(request):
    """
    Добавляет в контекст каждого запроса:
    - unread_count: число непрочитанных уведомлений
    - recent_notifications: последние 5 непрочитанных (для dropdown)
    """
    if not request.user.is_authenticated:
        return {"unread_count": 0, "recent_notifications": []}

    qs = (
        Notification.objects
        .for_user(request.user)
        .unread()
        .select_related("case")
        .order_by("-created_at")
    )

    recent = list(qs[:5])
    unread_count = qs.count()

    return {
        "unread_count": unread_count,
        "recent_notifications": recent,
    }
