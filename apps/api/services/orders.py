import uuid
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.models import OrderModel, PackageModel
from packages.shared_types.payment import OrderStatus, PaymentMethod, PaymentProvider


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
            return order

        provider = self._resolve_provider(method)
        order = OrderModel(
            id=uuid.uuid4(),
            telegram_user_id=telegram_user_id,
            package_id=package.id,
            payment_method=method.value,
            provider=provider.value,
            amount_minor=package.amount_minor,
            currency=package.currency,
            status=OrderStatus.pending.value,
            idempotency_key=idempotency_key,
        )
        self.db.add(order)
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

            if order.amount_minor != amount_minor or order.currency != currency:
                order.status = OrderStatus.failed.value
                order.failed_at = datetime.now(UTC)
                order.raw_provider_payload = {**order.raw_provider_payload, "mismatch": raw_payload}
                await self.db.commit()
                return order

            order.status = OrderStatus.paid.value
            order.provider_charge_id = provider_charge_id
            order.paid_at = datetime.now(UTC)
            order.raw_provider_payload = {**order.raw_provider_payload, "payment": raw_payload}
            await self.db.commit()
            await self.db.refresh(order)
            return order
        finally:
            await self.redis.delete(lock_key)

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
        return PaymentProvider.nowpayments
