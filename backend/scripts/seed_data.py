from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.database import async_session_factory
from app.models.audit_log import AuditLog, AuditAction
from app.models.agent_action import AgentAction, AgentActionType, AgentActionStatus
from app.models.agent_run import AgentRun, AgentRunStatus, AgentType
from app.models.customer import Customer, CustomerStatus
from app.models.customer_email_consent import (
    CustomerEmailConsent,
    ConsentChannel,
    ConsentStatus,
)
from app.models.email_message import EmailMessage, EmailDirection, EmailStatus
from app.models.email_template import EmailTemplate
from app.models.payment import Payment, PaymentStatus
from app.models.policy_decision import PolicyDecision, PolicyDecisionType, PolicyOutcome
from app.models.recovery_attempt import (
    RecoveryAttempt,
    RecoveryAttemptStatus,
    RecoveryChannel,
)

# ── Indian names ──────────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai",
    "Rohan", "Vihaan", "Krishna", "Ishaan", "Shaurya",
    "Ananya", "Diya", "Priya", "Neha", "Aisha",
    "Kavya", "Meera", "Pooja", "Riya", "Sneha",
]

LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Singh", "Reddy",
    "Nair", "Gupta", "Joshi", "Desai", "Mishra",
    "Iyer", "Rao", "Choudhary", "Tiwari", "Verma",
    "Bhat", "Kapoor", "Malhotra", "Chauhan", "Saxena",
]

DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com", "hotmail.com"]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
]

FAILURE_REASONS = [
    "Payment declined by issuing bank",
    "Insufficient funds in account",
    "Card expired",
    "Transaction timeout - bank did not respond",
    "Incorrect OTP entered 3 times",
    "Daily transaction limit exceeded",
    "Card blocked by issuer",
    "Network failure during payment",
    "Payment cancelled by user",
    "RBI mandate compliance check failed",
    "Virtual payment address does not exist",
    "Device binding mismatch detected",
]

EMAIL_SUBJECTS = [
    "Complete your payment - Order #{order_id}",
    "Payment failed for your recent order",
    "Don't miss out! Complete your purchase",
    "Your payment of ₹{amount} is pending",
    "Action required: Payment retry needed",
]

EMAIL_TEMPLATES = [
    {
        "name": "payment_failure",
        "subject": "Payment failed — please retry",
        "body_html": """
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Payment failed.</h2>
  <p>Your payment could not be processed. No amount was deducted.</p>
  <p>You can securely retry your payment here:</p>
  <p style="margin: 24px 0;">
    <a href="{{payment_link}}"
       style="display:inline-block;padding:12px 28px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">
      Retry Payment
    </a>
  </p>
  <p style="color:#666;font-size:13px;">If you did not attempt this payment, you can safely ignore this email.</p>
  <p style="color:#666;font-size:13px;">— RecoverFlow</p>
</body>
</html>
""",
        "body_text": "Payment failed. Retry here: {{payment_link}}",
        "description": "Sent when a customer's payment fails. Contains a secure retry link.",
        "variables": {"payment_link": "URL to the payment retry page"},
    },
]


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _ago(hours: int = 0, minutes: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours, minutes=minutes)


def _random_phone() -> str:
    return f"+91{random.choice([7, 8, 9])}{random.randint(100000000, 999999999)}"


def _random_amount() -> int:
    return random.choice([149, 299, 499, 799, 999, 1299, 1999, 2499, 3499, 4999, 7999, 9999])


async def seed() -> None:
    async with async_session_factory() as db:
        # ── Email templates ──────────────────────────────────────────────
        for tpl_data in EMAIL_TEMPLATES:
            existing = (await db.execute(
                select(EmailTemplate).where(EmailTemplate.name == tpl_data["name"])
            )).scalar_one_or_none()
            if not existing:
                tpl = EmailTemplate(
                    id=_uuid(),
                    name=tpl_data["name"],
                    subject=tpl_data["subject"],
                    body_html=tpl_data["body_html"],
                    body_text=tpl_data.get("body_text"),
                    description=tpl_data.get("description"),
                    variables=tpl_data.get("variables"),
                    is_active=True,
                )
                db.add(tpl)
        await db.flush()
        print(f"Seeded {len(EMAIL_TEMPLATES)} email templates")

        # ── Customers ─────────────────────────────────────────────────────
        customers: list[Customer] = []
        used_emails: set[str] = set()

        for i in range(20):
            first = FIRST_NAMES[i]
            last = LAST_NAMES[i]
            domain = random.choice(DOMAINS)
            email = f"{first.lower()}.{last.lower()}@{domain}"
            while email in used_emails:
                email = f"{first.lower()}.{last.lower()}{random.randint(1,99)}@{domain}"
            used_emails.add(email)

            status = random.choices(
                [CustomerStatus.ACTIVE, CustomerStatus.INACTIVE, CustomerStatus.BLOCKED],
                weights=[80, 15, 5],
            )[0]

            c = Customer(
                id=_uuid(),
                email=email,
                phone=_random_phone(),
                name=f"{first} {last}",
                status=status.value,
                metadata_={"city": random.choice(CITIES), "source": random.choice(["organic", "referral", "ads"])},
                created_at=_ago(hours=random.randint(1, 720)),
            )
            db.add(c)
            customers.append(c)

        await db.flush()
        print(f"Created {len(customers)} customers")

        # ── Payments ──────────────────────────────────────────────────────
        payments: list[Payment] = []
        failed_payments: list[Payment] = []

        for i in range(50):
            customer = random.choice(customers)
            amount = _random_amount()
            is_failed = i >= 40  # last 10 are failed

            if is_failed:
                pstatus = random.choice([
                    PaymentStatus.FAILED.value,
                    PaymentStatus.RECOVERY_PENDING.value,
                    PaymentStatus.RECOVERED.value,
                ])
                failure_reason = random.choice(FAILURE_REASONS)
            else:
                pstatus = random.choices(
                    [PaymentStatus.CREATED.value, PaymentStatus.AUTHORIZED.value, PaymentStatus.CAPTURED.value],
                    weights=[10, 20, 70],
                )[0]
                failure_reason = None

            created = _ago(hours=random.randint(1, 336))

            p = Payment(
                id=_uuid(),
                customer_id=customer.id,
                razorpay_order_id=f"order_{_uuid().hex[:14]}",
                razorpay_payment_id=f"pay_{_uuid().hex[:14]}" if pstatus in ("captured", "authorized") else None,
                customer_email=customer.email,
                customer_phone=customer.phone,
                amount=amount,
                currency="INR",
                status=pstatus,
                failure_reason=failure_reason,
                recovery_email_sent=_ago(hours=random.randint(1, 48)) if pstatus in (PaymentStatus.RECOVERY_PENDING.value, PaymentStatus.RECOVERED.value) else None,
                recovery_email_opened=_ago(hours=random.randint(1, 24)) if pstatus == PaymentStatus.RECOVERED.value and random.random() > 0.3 else None,
                payment_link_clicked=_ago(hours=random.randint(1, 12)) if pstatus == PaymentStatus.RECOVERED.value and random.random() > 0.5 else None,
                metadata_={"city": random.choice(CITIES), "device": random.choice(["mobile", "desktop", "tablet"])},
                created_at=created,
                updated_at=created + timedelta(minutes=random.randint(1, 120)),
            )
            db.add(p)
            payments.append(p)
            if is_failed:
                failed_payments.append(p)

        await db.flush()
        print(f"Created {len(payments)} payments ({len(failed_payments)} failed)")

        # ── Consent records ───────────────────────────────────────────────
        consent_count = 0
        for c in customers:
            # Each customer gets 1-3 consent records
            channels = random.sample(
                [ConsentChannel.EMAIL, ConsentChannel.SMS, ConsentChannel.WHATSAPP],
                k=random.randint(1, 3),
            )
            for ch in channels:
                status = random.choices(
                    [ConsentStatus.GRANTED, ConsentStatus.DENIED, ConsentStatus.REVOKED],
                    weights=[70, 15, 15],
                )[0]
                consent = CustomerEmailConsent(
                    id=_uuid(),
                    customer_id=c.id,
                    channel=ch.value,
                    consent_status=status.value,
                    consented_at=_ago(hours=random.randint(1, 200)),
                    revoked_at=_ago(hours=random.randint(1, 50)) if status == ConsentStatus.REVOKED else None,
                    source=random.choice(["signup_form", "checkout", "manual", "webhook"]),
                    created_at=_ago(hours=random.randint(1, 200)),
                )
                db.add(consent)
                consent_count += 1

        await db.flush()
        print(f"Created {consent_count} consent records")

        # ── Email messages ────────────────────────────────────────────────
        email_count = 0
        for p in failed_payments:
            num_emails = random.randint(1, 3)
            for j in range(num_emails):
                email_status = random.choices(
                    [EmailStatus.SENT.value, EmailStatus.DELIVERED.value, EmailStatus.OPENED.value, EmailStatus.CLICKED.value],
                    weights=[20, 30, 30, 20],
                )[0]
                sent = _ago(hours=random.randint(1, 48))
                em = EmailMessage(
                    id=_uuid(),
                    customer_id=p.customer_id,
                    direction=EmailDirection.OUTBOUND.value,
                    status=email_status,
                    subject=random.choice(EMAIL_SUBJECTS).format(order_id=p.razorpay_order_id[-6:], amount=p.amount // 100),
                    recipient_email=p.customer_email,
                    sender_email="payments@recoverflow.in",
                    provider_message_id=f"re_{_uuid().hex[:12]}",
                    sent_at=sent,
                    delivered_at=sent + timedelta(minutes=random.randint(1, 5)) if email_status in ("delivered", "opened", "clicked") else None,
                    opened_at=sent + timedelta(minutes=random.randint(10, 60)) if email_status in ("opened", "clicked") else None,
                    created_at=sent,
                )
                db.add(em)
                email_count += 1

        await db.flush()
        print(f"Created {email_count} email messages")

        # ── Recovery attempts ─────────────────────────────────────────────
        ra_count = 0
        for p in failed_payments:
            num_attempts = random.randint(1, 3)
            for j in range(num_attempts):
                ra_status = random.choices(
                    [RecoveryAttemptStatus.SENT.value, RecoveryAttemptStatus.DELIVERED.value,
                     RecoveryAttemptStatus.OPENED.value, RecoveryAttemptStatus.CLICKED.value,
                     RecoveryAttemptStatus.CONVERTED.value],
                    weights=[15, 25, 25, 20, 15],
                )[0]
                sent = _ago(hours=random.randint(1, 48))
                ra = RecoveryAttempt(
                    id=_uuid(),
                    customer_id=p.customer_id,
                    payment_id=p.id,
                    channel=RecoveryChannel.EMAIL.value,
                    status=ra_status,
                    attempt_number=j + 1,
                    recovery_link=f"https://pay.recoverflow.in/retry/{_uuid().hex[:8]}",
                    sent_at=sent,
                    opened_at=sent + timedelta(minutes=random.randint(5, 30)) if ra_status in ("opened", "clicked", "converted") else None,
                    clicked_at=sent + timedelta(minutes=random.randint(10, 60)) if ra_status in ("clicked", "converted") else None,
                    converted_at=sent + timedelta(minutes=random.randint(15, 90)) if ra_status == "converted" else None,
                    created_at=sent,
                )
                db.add(ra)
                ra_count += 1

        await db.flush()
        print(f"Created {ra_count} recovery attempts")

        # ── Agent runs + actions ──────────────────────────────────────────
        run_count = 0
        action_count = 0
        run_ids: list[uuid.UUID] = []
        for p in failed_payments:
            run_id = _uuid()
            run_ids.append(run_id)
            run = AgentRun(
                id=run_id,
                agent_type=AgentType.RECOVERY.value,
                status=random.choice([AgentRunStatus.COMPLETED.value, AgentRunStatus.RUNNING.value]),
                payment_id=p.id,
                customer_id=p.customer_id,
                input_data={"payment_amount": p.amount, "email": p.customer_email, "failure_reason": p.failure_reason},
                output_data={"recovery_score": round(random.uniform(0.3, 0.95), 2), "recommended_channel": "email"} if random.random() > 0.3 else None,
                started_at=_ago(hours=random.randint(1, 48)),
                completed_at=_ago(hours=random.randint(1, 24)) if random.random() > 0.3 else None,
                created_at=_ago(hours=random.randint(1, 48)),
            )
            db.add(run)
            run_count += 1

        await db.flush()

        for i, p in enumerate(failed_payments):
            run_id = run_ids[i]
            num_actions = random.randint(1, 3)
            for _ in range(num_actions):
                action = AgentAction(
                    id=_uuid(),
                    run_id=run_id,
                    action_type=random.choice([
                        AgentActionType.SEND_EMAIL.value,
                        AgentActionType.UPDATE_STATUS.value,
                        AgentActionType.LOG_EVENT.value,
                    ]),
                    status=random.choice([AgentActionStatus.EXECUTED.value, AgentActionStatus.PENDING.value]),
                    target=p.customer_email,
                    payload={"subject": random.choice(EMAIL_SUBJECTS).format(order_id=p.razorpay_order_id[-6:], amount=p.amount // 100)},
                    result={"status": "sent", "message_id": f"re_{_uuid().hex[:8]}"} if random.random() > 0.4 else None,
                    executed_at=_ago(hours=random.randint(1, 24)) if random.random() > 0.4 else None,
                    created_at=_ago(hours=random.randint(1, 48)),
                )
                db.add(action)
                action_count += 1

        await db.flush()
        print(f"Created {run_count} agent runs, {action_count} agent actions")

        # ── Policy decisions ──────────────────────────────────────────────
        pd_count = 0
        for p in failed_payments:
            pd = PolicyDecision(
                id=_uuid(),
                decision_type=PolicyDecisionType.RECOVERY_ELIGIBLE.value,
                outcome=random.choice([PolicyOutcome.APPROVED.value, PolicyOutcome.DENIED.value]),
                payment_id=p.id,
                customer_id=p.customer_id,
                reason=random.choice([
                    "Customer has good payment history, eligible for recovery",
                    "Too many recent failures, recovery blocked",
                    "Customer opted out of email communications",
                    "Payment amount within recovery threshold",
                    "High-risk customer profile, manual review needed",
                ]),
                context={"previous_payments": random.randint(0, 20), "failure_count": random.randint(1, 5)},
                evaluated_by=random.choice(["policy_engine", "agent", "manual"]),
                created_at=_ago(hours=random.randint(1, 48)),
            )
            db.add(pd)
            pd_count += 1

        await db.flush()
        print(f"Created {pd_count} policy decisions")

        # ── Audit logs ────────────────────────────────────────────────────
        al_count = 0
        for p in payments[:15]:
            al = AuditLog(
                id=_uuid(),
                actor=random.choice(["system", "webhook razorpay", "agent_recovery", "admin"]),
                action=random.choice([
                    AuditAction.PAYMENT_PROCESSED.value,
                    AuditAction.EMAIL_SENT.value,
                    AuditAction.RECOVERY_ATTEMPTED.value,
                    AuditAction.POLICY_EVALUATED.value,
                    AuditAction.AGENT_EXECUTED.value,
                ]),
                resource_type="payment",
                resource_id=p.id,
                description=f"Payment {p.status} for ₹{p.amount // 100}",
                payload={"amount": p.amount, "status": p.status, "email": p.customer_email},
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                created_at=_ago(hours=random.randint(1, 168)),
            )
            db.add(al)
            al_count += 1

        await db.commit()
        print(f"Created {al_count} audit logs")
        print("\nSeed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
