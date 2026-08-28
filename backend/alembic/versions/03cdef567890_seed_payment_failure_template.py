"""seed payment_failure email template

Revision ID: 03cdef567890
Revises: 02abc1234def
Create Date: 2026-08-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '03cdef567890'
down_revision: Union[str, None] = '02abc1234def'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO email_templates (id, name, subject, body_html, body_text, description, variables, is_active)
        VALUES (
            gen_random_uuid(),
            'payment_failure',
            'We noticed your payment didn''t go through — let''s fix that',
            '<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a2e;">Hi {{customer_name}},</h2>
  <p>We noticed your recent payment of <strong>₹{{amount}}</strong> didn''t go through.</p>
  <p><strong>Reason:</strong> {{failure_reason}}</p>
  <p>Don''t worry — this happens sometimes. You can retry your payment using the link below:</p>
  <div style="text-align: center; margin: 30px 0;">
    <a href="{{recovery_link}}" style="background-color: #6c5ce7; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">Retry Payment</a>
  </div>
  <p style="color: #888; font-size: 13px;">If you have any questions, reply to this email and we''ll help you out.</p>
  <p style="color: #888; font-size: 13px;">— The RecoverFlow Team</p>
</body>
</html>',
            'Hi {{customer_name}},\n\nYour payment of ₹{{amount}} didn''t go through.\n\nReason: {{failure_reason}}\n\nRetry here: {{recovery_link}}\n\n— The RecoverFlow Team',
            'Email sent to customers when a payment fails. Includes retry link and failure reason.',
            '["customer_name", "amount", "failure_reason", "recovery_link"]'::jsonb,
            true
        )
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM email_templates WHERE name = 'payment_failure'")
