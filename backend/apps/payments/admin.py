from django.contrib import admin

from apps.payments.models import PaymentAttempt


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "order_id", "amount", "status", "created_at")
    readonly_fields = [f.name for f in PaymentAttempt._meta.fields]

    def has_add_permission(self, request):
        return False
