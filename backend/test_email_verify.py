"""Real email verification — Hour 10.

Sends a test email via Resend, stores it in the database, and verifies:
1. Email was accepted by Resend (success + provider_message_id)
2. provider_message_id is persisted in email_messages table
3. Database status is set to 'sent'
"""
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/home/yashas-bhagwat/RecoverFlow/backend")

from dotenv import load_dotenv
load_dotenv("/home/yashas-bhagwat/RecoverFlow/.env")

import psycopg
from app.core.config import get_settings
from app.services.email.resend_service import ResendEmailService

settings = get_settings()
TEST_EMAIL = "bhagwatyashas5@gmail.com"
SENDER = settings.RECOVERY_EMAIL_FROM or "onboarding@resend.dev"


def get_db_conn():
    """Connect using the sync psycopg driver (docker-compose port 5433)."""
    dsn = "postgresql://recoverflow:recoverflow123@localhost:5433/recoverflow"
    return psycopg.connect(dsn)


async def main():
    print("=" * 60)
    print("  Hour 10 — Real Email Verification")
    print("=" * 60)

    # ── Step 1: Send email ──────────────────────────────────────────────
    print(f"\n[1] Sending email to {TEST_EMAIL} ...")
    svc = ResendEmailService()
    result = await svc.send_email(
        to=TEST_EMAIL,
        subject="RecoverFlow — Real Email Verification",
        body=(
            "<h2>Hour 10 Verification</h2>"
            "<p>This is an automated test email from RecoverFlow.</p>"
            "<p>If you received this, the Resend integration is working.</p>"
        ),
        from_email=SENDER,
    )

    print(f"    success:          {result.success}")
    print(f"    provider_message_id: {result.provider_message_id}")
    print(f"    error_category:   {result.error_category}")
    print(f"    error_message:    {result.error_message}")
    print(f"    status_code:      {result.status_code}")

    if not result.success:
        print("\n  FAILED — email was not accepted by Resend.")
        sys.exit(1)

    print("\n  ✅ Step 1 PASSED — Resend accepted the email")

    # ── Step 2: Store in database ───────────────────────────────────────
    email_msg_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Use a real customer from the database
    conn = get_db_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM customers LIMIT 1")
        row = cur.fetchone()
        customer_id = row[0] if row else None
    conn.close()

    if not customer_id:
        print("  FAILED — no customers in database. Run seed_data.py first.")
        sys.exit(1)

    print(f"\n[2] Storing email in database (id={email_msg_id}, customer={customer_id}) ...")
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO email_messages (
                    id, customer_id, direction, status, subject,
                    recipient_email, sender_email, provider_message_id,
                    sent_at, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    str(email_msg_id),
                    str(customer_id),
                    "outbound",
                    "sent",
                    "RecoverFlow — Real Email Verification",
                    TEST_EMAIL,
                    SENDER,
                    result.provider_message_id,
                    now,
                    now,
                    now,
                ),
            )
        conn.commit()
        print(f"    Inserted {email_msg_id}")
    except Exception as e:
        conn.rollback()
        print(f"  INSERT FAILED: {e}")
        sys.exit(1)
    finally:
        conn.close()

    print("  ✅ Step 2 PASSED — email record stored in database")

    # ── Step 3: Verify provider_message_id is stored ────────────────────
    print(f"\n[3] Verifying provider_message_id in database ...")
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT provider_message_id, status, sent_at, recipient_email "
                "FROM email_messages WHERE id = %s",
                (str(email_msg_id),),
            )
            row = cur.fetchone()

        if not row:
            print("  FAILED — email record not found in database")
            sys.exit(1)

        stored_pm_id, stored_status, stored_sent_at, stored_recipient = row
        print(f"    provider_message_id: {stored_pm_id}")
        print(f"    status:              {stored_status}")
        print(f"    sent_at:             {stored_sent_at}")
        print(f"    recipient_email:     {stored_recipient}")

        if stored_pm_id != result.provider_message_id:
            print(f"  FAILED — provider_message_id mismatch: got {stored_pm_id}, expected {result.provider_message_id}")
            sys.exit(1)

        print("\n  ✅ Step 3 PASSED — provider_message_id matches")

        # ── Step 4: Verify database status ──────────────────────────────
        print(f"\n[4] Verifying database status ...")
        if stored_status != "sent":
            print(f"  FAILED — status is '{stored_status}', expected 'sent'")
            sys.exit(1)

        print(f"    status = '{stored_status}'")
        print("  ✅ Step 4 PASSED — database status is 'sent'")

    finally:
        conn.close()

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ALL CHECKS PASSED")
    print(f"  Provider message ID: {result.provider_message_id}")
    print(f"  Recipient: {TEST_EMAIL}")
    print(f"  Check your inbox for the verification email.")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
