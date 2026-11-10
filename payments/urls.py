from django.urls import path

from payments.views import PaymentRenewView, PaymentWebHookView

urlpatterns = [
    path("webhook/", PaymentWebHookView.as_view(), name="webhook"),
    path("<int:pk>/renew/", PaymentRenewView.as_view(), name="payment-renew"),
]

app_name = "payments"
