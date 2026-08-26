import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.payment import Payment, PaymentStatus
from app.services.recovery.recovery_service_v2 import (
    CustomerNotFoundError,
    DuplicateRecoveryLinkError,
    InvalidPaymentStateError,
    PaymentNotFoundError,
    RecoveryServiceV2,
)


async def create_test_customer(session: AsyncSession, status: str = "active") -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        status=status,
    )
    session.add(customer)
    await session.flush()
    return customer


@pytest.mark.asyncio
class TestGetCustomer:
    async def test_get_customer_found(self, db_session: AsyncSession):
        customer = await create_test_customer(db_session)
        svc = RecoveryServiceV2(db_session)
        result = await svc.get_customer(customer.id)
        assert result.id == customer.id
        assert result.email == customer.email

    async def test_get_customer_not_found(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        with pytest.raises(CustomerNotFoundError):
            await svc.get_customer(uuid.uuid4())

    async def test_get_customer_by_email_found(self, db_session: AsyncSession):
        customer = await create_test_customer(db_session)
        svc = RecoveryServiceV2(db_session)
        result = await svc.get_customer_by_email(customer.email)
        assert result.email == customer.email

    async def test_get_customer_by_email_not_found(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        with pytest.raises(CustomerNotFoundError):
            await svc.get_customer_by_email("nonexistent@example.com")

    async def test_get_customer_by_email_invalid(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        with pytest.raises(ValueError):
            await svc.get_customer_by_email("")

    async def test_get_customer_by_email_no_at(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        with pytest.raises(ValueError):
            await svc.get_customer_by_email("notanemail")


@pytest.mark.asyncio
class TestGetPayment:
    async def test_get_payment_found(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=10000,
            status=PaymentStatus.FAILED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        result = await svc.get_payment(payment.id)
        assert result.id == payment.id

    async def test_get_payment_not_found(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        with pytest.raises(PaymentNotFoundError):
            await svc.get_payment(uuid.uuid4())

    async def test_get_payment_by_order(self, db_session: AsyncSession):
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=order_id,
            customer_email="test@example.com",
            amount=10000,
            status=PaymentStatus.CAPTURED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        result = await svc.get_payment_by_order(order_id)
        assert result.razorpay_order_id == order_id

    async def test_get_payment_by_order_empty(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        with pytest.raises(ValueError):
            await svc.get_payment_by_order("")

    async def test_get_payment_in_state_valid(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=10000,
            status=PaymentStatus.FAILED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        result = await svc.get_payment_in_state(
            payment.id, PaymentStatus.FAILED.value
        )
        assert result.status == PaymentStatus.FAILED.value

    async def test_get_payment_in_state_invalid(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=10000,
            status=PaymentStatus.CAPTURED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        with pytest.raises(InvalidPaymentStateError):
            await svc.get_payment_in_state(
                payment.id, PaymentStatus.FAILED.value
            )


@pytest.mark.asyncio
class TestPaymentHistory:
    async def test_returns_payments(self, db_session: AsyncSession):
        customer = await create_test_customer(db_session)
        cid = customer.id
        for i in range(5):
            db_session.add(Payment(
                id=uuid.uuid4(),
                customer_id=cid,
                razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
                customer_email=customer.email,
                amount=1000 * (i + 1),
                status=PaymentStatus.CAPTURED.value,
            ))
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        history = await svc.get_payment_history(cid)
        assert len(history) == 5

    async def test_filter_by_status(self, db_session: AsyncSession):
        customer = await create_test_customer(db_session)
        cid = customer.id
        for status in [PaymentStatus.CAPTURED.value, PaymentStatus.FAILED.value, PaymentStatus.CAPTURED.value]:
            db_session.add(Payment(
                id=uuid.uuid4(),
                customer_id=cid,
                razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
                customer_email=customer.email,
                amount=1000,
                status=status,
            ))
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        captured = await svc.get_payment_history(cid, status=PaymentStatus.CAPTURED.value)
        assert len(captured) == 2
        failed = await svc.get_payment_history(cid, status=PaymentStatus.FAILED.value)
        assert len(failed) == 1

    async def test_pagination(self, db_session: AsyncSession):
        customer = await create_test_customer(db_session)
        cid = customer.id
        for i in range(10):
            db_session.add(Payment(
                id=uuid.uuid4(),
                customer_id=cid,
                razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
                customer_email=customer.email,
                amount=100,
                status=PaymentStatus.CAPTURED.value,
            ))
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        page1 = await svc.get_payment_history(cid, limit=3, offset=0)
        assert len(page1) == 3
        page2 = await svc.get_payment_history(cid, limit=3, offset=3)
        assert len(page2) == 3
        total = await svc.get_payment_history_count(cid)
        assert total == 10

    async def test_empty_history(self, db_session: AsyncSession):
        svc = RecoveryServiceV2(db_session)
        history = await svc.get_payment_history(uuid.uuid4())
        assert len(history) == 0


@pytest.mark.asyncio
class TestCreatePaymentLink:
    async def test_creates_link(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=2999,
            status=PaymentStatus.FAILED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        link = await svc.create_payment_link(payment.id)
        assert link["url"].startswith("https://pay.recoverflow.in/retry/")
        assert link["amount"] == 2999
        assert link["payment_id"] == str(payment.id)

    async def test_duplicate_link_blocked(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=2999,
            status=PaymentStatus.FAILED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        await svc.create_payment_link(payment.id)
        with pytest.raises(DuplicateRecoveryLinkError):
            await svc.create_payment_link(payment.id)

    async def test_invalid_state_blocked(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=2999,
            status=PaymentStatus.CAPTURED.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        with pytest.raises(InvalidPaymentStateError):
            await svc.create_payment_link(payment.id)

    async def test_amount_override(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=2999,
            status=PaymentStatus.RECOVERY_PENDING.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        link = await svc.create_payment_link(payment.id, amount_override=1999)
        assert link["amount"] == 1999

    async def test_recovery_pending_also_allowed(self, db_session: AsyncSession):
        payment = Payment(
            id=uuid.uuid4(),
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            customer_email="test@example.com",
            amount=500,
            status=PaymentStatus.RECOVERY_PENDING.value,
        )
        db_session.add(payment)
        await db_session.flush()

        svc = RecoveryServiceV2(db_session)
        link = await svc.create_payment_link(payment.id)
        assert link["payment_id"] == str(payment.id)
