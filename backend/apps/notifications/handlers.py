"""Turns domain events into notifications. Notifications owns the wording; publishers only state facts."""

from decimal import Decimal

from apps.notifications.services import notify
from core import events

_DELIVERY_MESSAGES = {
    "dispatched": ("Order on its way", "Your order is dispatched or ready for collection."),
    "delivered": ("Order delivered", "Your order was delivered or collected. Thank you for using MazaoX."),
    "failed": ("Delivery problem", "There was a problem with your delivery. We will be in touch."),
    "pending": ("Delivery rescheduled", "Your delivery was rescheduled."),
}


def on_order_placed(order_id, buyer_id, farmer_id, label, ttl_minutes):
    notify(buyer_id, "order_placed", "Order placed", f"Your {label} was placed. Pay within {ttl_minutes} minutes to confirm it.", order_id)
    notify(farmer_id, "order_received", "New order", f"You have a new {label} awaiting payment.", order_id)


def on_order_cancelled(order_id, buyer_id, farmer_id, label, cancelled_by):
    for user_id in {buyer_id, farmer_id} - {cancelled_by}:
        notify(user_id, "order_cancelled", "Order cancelled", f"The {label} was cancelled.", order_id)


def on_order_expired(order_id, buyer_id, label):
    notify(buyer_id, "order_expired", "Order expired", f"The {label} expired because it was not paid in time.", order_id)


def on_order_paid(order_id, buyer_id, farmer_id, label):
    notify(buyer_id, "payment_received", "Payment received", f"Payment for {label} was received.", order_id)
    notify(farmer_id, "order_paid", "Order paid", f"The {label} is paid. Please prepare it.", order_id)


def on_payment_failed(order_id, buyer_id):
    notify(buyer_id, "payment_failed", "Payment failed", "Your payment did not go through. You can try again while the order is still open.", order_id)


def on_review_created(order_id, farmer_id, rating):
    notify(farmer_id, "review_received", "New review", f"A buyer left you a {rating}-star review.", order_id)


def on_issue_updated(order_id, reporter_id, status):
    notify(reporter_id, "issue_updated", "Issue update", f"Your issue is now {status}.", order_id)


def on_demand_matched(farmer_id, produce_name, quantity, quantity_unit, county):
    notify(farmer_id, "demand_match", "A buyer wants your produce",
           f"A buyer is looking for {Decimal(quantity).normalize():f} {quantity_unit} of {produce_name} in {county}.")


def on_delivery_status_changed(order_id, buyer_id, status):
    title, message = _DELIVERY_MESSAGES[status]
    notify(buyer_id, f"delivery_{status}", title, message, order_id)


def register() -> None:
    events.subscribe("order.placed", on_order_placed)
    events.subscribe("order.cancelled", on_order_cancelled)
    events.subscribe("order.expired", on_order_expired)
    events.subscribe("order.paid", on_order_paid)
    events.subscribe("payment.failed", on_payment_failed)
    events.subscribe("review.created", on_review_created)
    events.subscribe("issue.updated", on_issue_updated)
    events.subscribe("demand.matched", on_demand_matched)
    events.subscribe("delivery.status_changed", on_delivery_status_changed)
