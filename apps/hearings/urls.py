from django.urls import path
from .views import (
    HearingScheduleView, HearingDetailView, HearingCompleteView,
    ProtocolCreateView, CalendarView,
)

app_name = "hearings"

urlpatterns = [
    path("", CalendarView.as_view(), name="calendar"),
    path("cases/<int:case_pk>/schedule/", HearingScheduleView.as_view(), name="schedule"),
    path("<int:pk>/", HearingDetailView.as_view(), name="detail"),
    path("<int:pk>/complete/", HearingCompleteView.as_view(), name="complete"),
    path("<int:pk>/protocol/create/", ProtocolCreateView.as_view(), name="protocol_create"),
]
