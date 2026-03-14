from django.urls import path
from .views import DeliveryCreateView, DeliveryUpdateView, DeliveryListView

app_name = "delivery"

urlpatterns = [
    path("", DeliveryListView.as_view(), name="list"),
    path("cases/<int:case_pk>/create/", DeliveryCreateView.as_view(), name="create"),
    path("<int:pk>/update/", DeliveryUpdateView.as_view(), name="update"),
]
