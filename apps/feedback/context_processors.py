from .models import Feedback


def unreviewed_feedback(request):
    if request.user.is_authenticated and getattr(request.user, "role", None) in ("admin", "reviewer"):
        return {"unreviewed_feedback_count": Feedback.objects.filter(is_reviewed=False).count()}
    return {"unreviewed_feedback_count": 0}
