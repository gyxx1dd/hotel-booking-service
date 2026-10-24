from django.urls import path

from payments.views import PaymentWebHookView

urlpatterns = [
    path("webhook/", PaymentWebHookView.as_view(), name="webhook"),
]

app_name = "payments"
