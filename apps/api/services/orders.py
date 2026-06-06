import uuid

from apps.api.db.time import utc_now_db

import logging

import redis.asyncio as redis

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession



from apps.api.db.models import OrderModel, PackageModel

from apps.api.services.fulfillment import deliver_order, try_deliver_order

from packages.shared_types.payment import OrderStatus, PaymentMethod, PaymentProvider


logger = logging.getLogger(__name__)

_REUSABLE_ORDER_STATUSES = frozenset({
    OrderStatus.pending.value,
    OrderStatus.invoice_created.value,
})

_STATUS_MESSAGES: dict[str, str] = {
    OrderStatus.failed.value: "Payment failed or the amount did not match. Purchase again from the shop.",
    OrderStatus.expired.value: "This order expired. Start a new checkout from the shop.",
}



class PreCheckoutResult:

    def __init__(self, *, ok: bool, error: str = ""):

        self.ok = ok

        self.error = error





class OrderService:

    def __init__(self, db: AsyncSession, redis_client: redis.Redis):

        self.db = db

        self.redis = redis_client



    async def get_package(self, package_id: str) -> PackageModel | None:

        result = await self.db.execute(

            select(PackageModel).where(PackageModel.id == package_id, PackageModel.active.is_(True))

        )

        return result.scalar_one_or_none()



    async def create_order(

        self,

        *,

        telegram_user_id: int,

        package: PackageModel,

        method: PaymentMethod,

        idempotency_key: str,

    ) -> OrderModel:

        existing = await self.db.execute(

            select(OrderModel).where(OrderModel.idempotency_key == idempotency_key)

        )

        if order := existing.scalar_one_or_none():

            if order.status in _REUSABLE_ORDER_STATUSES:

                return order

            idempotency_key = f"{idempotency_key}:{uuid.uuid4()}"



        provider = self._resolve_provider(method)

        currency = package.currency

        amount_minor = package.amount_minor

        if method == PaymentMethod.stars:

            currency = "XTR"

            amount_minor = package.amount_minor



        order = OrderModel(

            id=uuid.uuid4(),

            telegram_user_id=telegram_user_id,

            package_id=package.id,

            payment_method=method.value,

            provider=provider.value,

            amount_minor=amount_minor,

            currency=currency,

            status=OrderStatus.pending.value,

            idempotency_key=idempotency_key,

        )

        self.db.add(order)

        await self.db.commit()

        await self.db.refresh(order)

        return order



    async def set_payment_terms(self, order: OrderModel, *, amount_minor: int, currency: str) -> OrderModel:

        order.amount_minor = amount_minor

        order.currency = currency

        await self.db.commit()

        await self.db.refresh(order)

        return order



    async def mark_invoice_created(

        self,

        order: OrderModel,

        *,

        provider_invoice_id: str,

        raw_payload: dict | None = None,

    ) -> OrderModel:

        order.status = OrderStatus.invoice_created.value

        order.provider_invoice_id = provider_invoice_id

        if raw_payload:

            order.raw_provider_payload = raw_payload

        await self.db.commit()

        await self.db.refresh(order)

        return order



    async def mark_paid(

        self,

        order_id: uuid.UUID,

        *,

        provider_charge_id: str | None,

        amount_minor: int,

        currency: str,

        raw_payload: dict,

    ) -> OrderModel | None:

        lock_key = f"order:pay:{order_id}"

        acquired = await self.redis.set(lock_key, "1", nx=True, ex=60)

        if not acquired:

            result = await self.db.execute(select(OrderModel).where(OrderModel.id == order_id))

            return result.scalar_one_or_none()



        try:

            result = await self.db.execute(select(OrderModel).where(OrderModel.id == order_id))

            order = result.scalar_one_or_none()

            if not order:

                return None



            if order.status == OrderStatus.paid.value:

                return order



            if order.amount_minor != amount_minor or order.currency.upper() != currency.upper():

                order.status = OrderStatus.failed.value

                order.failed_at = utc_now_db()

                order.raw_provider_payload = {**order.raw_provider_payload, "mismatch": raw_payload}

                await self.db.commit()

                return order



            order.status = OrderStatus.paid.value

            order.provider_charge_id = provider_charge_id

            order.paid_at = utc_now_db()

            order.raw_provider_payload = {**order.raw_provider_payload, "payment": raw_payload}

            await self.db.commit()

            await self.db.refresh(order)



            package = await self.get_package(order.package_id)

            if package:

                await deliver_order(order, package, self.db)



            return order

        finally:

            await self.redis.delete(lock_key)



    async def validate_pre_checkout(

        self,

        *,

        invoice_payload: str,

        total_amount: int,

        currency: str,

    ) -> PreCheckoutResult:

        order = await self.get_by_payload(invoice_payload)

        if not order:

            return PreCheckoutResult(ok=False, error="Order not found")



        if order.status not in (OrderStatus.pending.value, OrderStatus.invoice_created.value):

            return PreCheckoutResult(ok=False, error="Order already processed")



        if order.amount_minor != total_amount:

            return PreCheckoutResult(ok=False, error="Amount mismatch")



        if order.currency.upper() != currency.upper():

            return PreCheckoutResult(ok=False, error="Currency mismatch")



        if currency.upper() == "XTR" and order.payment_method != PaymentMethod.stars.value:

            return PreCheckoutResult(ok=False, error="Stars payment required")



        return PreCheckoutResult(ok=True)



    async def get_by_payload(self, payload: str) -> OrderModel | None:

        if not payload.startswith("order:"):

            return None

        try:

            order_id = uuid.UUID(payload.removeprefix("order:"))

        except ValueError:

            return None

        result = await self.db.execute(select(OrderModel).where(OrderModel.id == order_id))

        return result.scalar_one_or_none()



    @staticmethod

    def _resolve_provider(method: PaymentMethod) -> PaymentProvider:

        if method in (PaymentMethod.stars, PaymentMethod.telegram_card):

            return PaymentProvider.telegram

        if method == PaymentMethod.ton:

            return PaymentProvider.ton

        return PaymentProvider.nowpayments



    async def get_order_for_user(self, order_id: uuid.UUID, telegram_user_id: int) -> OrderModel | None:

        result = await self.db.execute(

            select(OrderModel).where(

                OrderModel.id == order_id,

                OrderModel.telegram_user_id == telegram_user_id,

            )

        )

        return result.scalar_one_or_none()



    async def get_order_with_package(

        self,

        order_id: uuid.UUID,

        telegram_user_id: int,

    ) -> tuple[OrderModel, PackageModel] | None:

        order = await self.get_order_for_user(order_id, telegram_user_id)

        if not order:

            return None

        package = await self.get_package(order.package_id)

        if not package:

            return None

        return order, package



    def delivery_message_for(self, order: OrderModel, package: PackageModel) -> str | None:

        if order.status != OrderStatus.paid.value:

            return None

        delivery_meta = order.raw_provider_payload.get("delivery") or {}

        if delivery_meta.get("message"):

            return delivery_meta["message"]

        content = package.delivery_content.strip() or package.description.strip() or package.title
        return content

    @staticmethod
    def status_message_for(status: str) -> str | None:
        return _STATUS_MESSAGES.get(status)

    @staticmethod
    def can_retry_checkout(status: str) -> bool:
        return status in (OrderStatus.failed.value, OrderStatus.expired.value)

    async def ensure_delivery(self, order: OrderModel, package: PackageModel) -> OrderModel:
        if order.status != OrderStatus.paid.value:
            return order
        delivery_meta = order.raw_provider_payload.get("delivery") or {}
        if not delivery_meta.get("sent_at"):
            await try_deliver_order(order, package, self.db)
            await self.db.refresh(order)
        return order

    async def list_orders_for_user(self, telegram_user_id: int, *, limit: int = 50) -> list[OrderModel]:
        result = await self.db.execute(
            select(OrderModel)
            .where(OrderModel.telegram_user_id == telegram_user_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def ton_payment_checkout_payload(order: OrderModel) -> dict[str, str] | None:
        if order.payment_method != PaymentMethod.ton.value:
            return None
        if order.status not in (OrderStatus.pending.value, OrderStatus.invoice_created.value):
            return None
        payload = order.raw_provider_payload or {}
        recipient = payload.get("recipient")
        amount = payload.get("amount_nanoton")
        comment = payload.get("comment")
        network = payload.get("network")
        if not recipient or amount is None or not comment or not network:
            return None
        return {
            "type": "ton_payment",
            "order_id": str(order.id),
            "recipient": str(recipient),
            "amount_nanoton": str(amount),
            "comment": str(comment),
            "network": str(network),
        }
