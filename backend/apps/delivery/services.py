"""Write interface of the delivery domain. Per ADR-002 defaults, an administrator is the delivery operator."""

from django.db import IntegrityError, transaction

from apps.delivery import selectors
from apps.delivery.models import Delivery, DeliveryEvent, DeliveryStatus
from apps.notifications.services import notify
from apps.orders import selectors as orders
from apps.orders import services as order_services
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

S = DeliveryStatus
ALLOWED = {
    S.PENDING: {S.DISPATCHED, S.FAILED},
    S.DISPATCHED: {S.DELIVERED, S.FAILED},
    S.FAILED: {S.PENDING},  # re-schedule after a failed attempt
    S.DELIVERED: set(),
}
_MESSAGES = {
    S.DISPATCHED: ("Order on its way", "Your order is dispatched or ready for collection."),
    S.DELIVERED: ("Order delivered", "Your order was delivered or collected. Thank you for using MazaoX."),
    S.FAILED: ("Delivery problem", "There was a problem with your delivery. We will be in touch."),
    S.PENDING: ("Delivery rescheduled", "Your delivery was rescheduled."),
}


def _require_admin(actor: Actor) -> None:
    if not actor.is_admin:
        raise ForbiddenError("Only an administrator can manage deliveries.")


def view_delivery_for_order(actor: Actor, order_id) -> Delivery:
    order = orders.get_order_snapshot(order_id)
    if order is None or not (actor.is_admin or actor.id in (order.buyer_id, order.farmer_id)):
        raise NotFoundError("Order not found.")
    delivery = selectors.get_delivery_for_order(order.id)
    if delivery is None:
        raise NotFoundError("No delivery record exists for this order yet.")
    return delivery


def create_delivery(actor: Actor, order_id) -> Delivery:
    _require_admin(actor)
    order = orders.get_order_snapshot(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    if order.status != "paid":
        raise ConflictError("A delivery can only be created for a paid order.", code="ORDER_NOT_PAID")
    try:
        with transaction.atomic():
            delivery = Delivery.objects.create(
                order_id=order.id, buyer_id=order.buyer_id, farmer_id=order.farmer_id, method=order.delivery_method,
                location=order.delivery_location, operator_id=actor.id,
            )
            DeliveryEvent.objects.create(delivery=delivery, from_status="", to_status=S.PENDING, actor_id=actor.id, note="Delivery record created")
    except IntegrityError as exc:
        raise ConflictError("A delivery record already exists for this order.", code="DELIVERY_EXISTS") from exc
    return selectors.get_delivery(delivery.id)


@transaction.atomic
def update_status(actor: Actor, delivery_id, new_status: str, note: str = "") -> Delivery:
    _require_admin(actor)
    if new_status not in DeliveryStatus.values:
        raise InvalidInputError("Unknown delivery status.", "status")
    visible = selectors.get_delivery(delivery_id)
    if visible is None:
        raise NotFoundError("Delivery not found.")
    delivery = Delivery.objects.select_for_update().get(pk=visible.pk)
    if delivery.status == new_status:
        return selectors.get_delivery(delivery.id)  # idempotent
    if new_status not in ALLOWED[delivery.status]:
        raise ConflictError(f"Cannot change a {delivery.status} delivery to {new_status}.", code="INVALID_TRANSITION")
    previous = delivery.status
    delivery.status, delivery.operator_id = new_status, actor.id
    delivery.save(update_fields=["status", "operator_id", "updated_at"])
    DeliveryEvent.objects.create(delivery=delivery, from_status=previous, to_status=new_status, actor_id=actor.id, note=(note or "").strip()[:255])
    if new_status == S.DELIVERED:
        order_services.complete_order(delivery.order_id, actor.id, "Delivery completed")
    title, message = _MESSAGES[S(new_status)]
    notify(delivery.buyer_id, f"delivery_{new_status}", title, message, delivery.order_id)
    return selectors.get_delivery(delivery.id)
