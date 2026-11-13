from django.urls import path

from apps.payments.api import views

urlpatterns = [
    path("orders/<uuid:order_id>/payment-simulation", views.StartPaymentView.as_view(), name="payment-start"),
    path("payments/simulations/<uuid:payment_id>", views.PaymentDetailView.as_view(), name="payment-detail"),
    path("payments/simulations/<uuid:payment_id>/complete", views.CompletePaymentView.as_view(), name="payment-complete"),
]
