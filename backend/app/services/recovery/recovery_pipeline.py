from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.audit_log import AuditAction
from app.models.payment import Payment, PaymentStatus
from app.models.policy_decision import PolicyDecisionType, PolicyOutcome
from app.services.audit.audit_service import AuditService
from app.services.consent.consent_service import ConsentService
from app.services.email.resend_service import ResendEmailService, EmailSendResult, EmailSendErrorCategory, DEFAULT_FROM_EMAIL
from app.services.email.template_service import EmailTemplateService
from app.services.payments.payment_service import PaymentService
from app.services.payments.payment_transition_service import (
    InvalidTransitionError,
    PaymentTransitionService,
)
from app.services.policy.policy_engine import PolicyContext, PolicyEngine, PolicyVerdict
from app.services.policy.policy_service import PolicyService
from app.services.recovery.recovery_attempt_service import RecoveryAttemptService

logger = get_logger(__name__)
settings = get_settings()


class RecoveryPipelineResult:
    def __init__(
        self,
        *,
        success: bool,
        reason: str,
        payment_id: uuid.UUID | None = None,
        recovery_attempt_id: uuid.UUID | None = None,
        policy_decision_id: uuid.UUID | None = None,
        email_message_id: uuid.UUID | None = None,
        audit_log_id: uuid.UUID | None = None,
    ) -> None:
        self.success = success
        self.reason = reason
        self.payment_id = payment_id
        self.recovery_attempt_id = recovery_attempt_id
        self.policy_decision_id = policy_decision_id
        self.email_message_id = email_message_id
        self.audit_log_id = audit_log_id

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "reason": self.reason,
            "payment_id": str(self.payment_id) if self.payment_id else None,
            "recovery_attempt_id": str(self.recovery_attempt_id) if self.recovery_attempt_id else None,
            "policy_decision_id": str(self.policy_decision_id) if self.policy_decision_id else None,
            "email_message_id": str(self.email_message_id) if self.email_message_id else None,
            "audit_log_id": str(self.audit_log_id) if self.audit_log_id else None,
        }


class RecoveryPipeline:
    """Orchestrates the full recovery flow:

    payment failed → AI agent diagnosis → consent check → policy evaluation →
    payment transition → recovery attempt → send email → audit log
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.payment_svc = PaymentService(db)
        self.transition_svc = PaymentTransitionService(db)
        self.consent_svc = ConsentService(db)
        self.policy_svc = PolicyService(db)
        self.policy_engine = PolicyEngine()
        self.attempt_svc = RecoveryAttemptService(db)
        self.audit_svc = AuditService(db)
        self.email_svc = ResendEmailService()
        self.template_svc = EmailTemplateService(db)

    async def handle_payment_failure(
        self,
        order_id: str,
        failure_reason: str | None = None,
        razorpay_payment_id: str | None = None,
        original_status: str | None = None,
    ) -> RecoveryPipelineResult:
        """Full pipeline: detect failure → evaluate → recover → email → audit."""

        # 1. Find the payment
        payment = await self.payment_svc.get_payment_by_order_id(order_id)
        if not payment:
            logger.warning("pipeline_payment_not_found", extra={"order_id": order_id})
            return RecoveryPipelineResult(success=False, reason="Payment not found")

        # Link customer if not already linked
        if not payment.customer_id:
            from app.models.customer import Customer
            from sqlalchemy import select as sel
            result = await self.db.execute(
                sel(Customer).where(Customer.email == payment.customer_email)
            )
            customer = result.scalar_one_or_none()
            if customer:
                payment.customer_id = customer.id
                await self.db.flush()
                logger.info(
                    "pipeline_linked_customer",
                    extra={"payment_id": str(payment.id), "customer_id": str(customer.id)},
                )

        if not payment.customer_id:
            logger.warning("pipeline_no_customer", extra={"order_id": order_id, "payment_id": str(payment.id)})
            return RecoveryPipelineResult(success=False, reason="Payment has no linked customer")

        logger.info(
            "pipeline_started",
            extra={"payment_id": str(payment.id), "order_id": order_id, "current_status": payment.status},
        )

        # 2. Check if already recovered (use original status before webhook update)
        if original_status == PaymentStatus.RECOVERED.value:
            decision = await self.policy_svc.create(
                decision_type="recovery_eligible",
                outcome="denied",
                payment_id=payment.id,
                customer_id=payment.customer_id,
                reason="Payment has already been recovered",
                context={"failure_reason": failure_reason, "current_status": payment.status},
                evaluated_by="policy_engine",
            )
            await self.audit_svc.create(
                actor="recovery_pipeline",
                action=AuditAction.POLICY_EVALUATED.value,
                resource_type="payment",
                resource_id=payment.id,
                description="Recovery blocked: already recovered",
                payload={"policy_decision_id": str(decision.id)},
            )
            await self.db.commit()
            return RecoveryPipelineResult(
                success=False, reason="Already recovered", payment_id=payment.id,
                policy_decision_id=decision.id,
            )

        # 3. Consent check — hard gate before any email is sent
        has_consent = await self.consent_svc.validate_consent(
            customer_id=payment.customer_id, channel="email"
        )

        if not has_consent:
            await self.policy_svc.create(
                decision_type="recovery_eligible",
                outcome="denied",
                payment_id=payment.id,
                customer_id=payment.customer_id,
                reason="Customer has not consented to email communication",
                context={"failure_reason": failure_reason, "has_email_consent": False},
                evaluated_by="consent_gate",
            )
            await self.audit_svc.create(
                actor="recovery_pipeline",
                action=AuditAction.POLICY_EVALUATED.value,
                resource_type="payment",
                resource_id=payment.id,
                description="Recovery blocked: no email consent",
                payload={"consent_check": "failed"},
            )
            await self.db.commit()
            logger.info(
                "pipeline_blocked_no_consent",
                extra={"payment_id": str(payment.id), "customer_id": str(payment.customer_id)},
            )
            return RecoveryPipelineResult(
                success=False, reason="Customer has not consented to email", payment_id=payment.id,
            )

        # 3.5 Run AI agent for diagnosis
        agent_result = None
        try:
            from app.services.agents.recovery_agent import RecoveryAgent
            agent = RecoveryAgent(self.db)
            agent_result = await agent.run({
                "payment_id": str(payment.id),
                "customer_id": str(payment.customer_id),
                "email": payment.customer_email,
                "order_id": order_id,
                "failure_reason": failure_reason,
            })
            logger.info(
                "agent_diagnosis_completed",
                extra={
                    "payment_id": str(payment.id),
                    "agent_success": agent_result.get("success", False),
                    "agent_state": agent_result.get("state", "unknown"),
                },
            )
        except Exception as e:
            logger.warning(
                "agent_diagnosis_failed",
                extra={"payment_id": str(payment.id), "error": str(e)},
            )

        # 4. Run deterministic policy engine
        ctx = PolicyContext(
            has_email_consent=has_consent,
            amount_paise=payment.amount,
            is_already_recovered=original_status == PaymentStatus.RECOVERED.value,
            failure_reason=failure_reason,
            attempt_count=len(await self.attempt_svc.list_by_payment(payment.id)),
        )
        result = self.policy_engine.evaluate(ctx)

        # 5. Record policy decision
        if result.verdict == PolicyVerdict.BLOCK:
            await self.policy_svc.create(
                decision_type="recovery_eligible",
                outcome="denied",
                payment_id=payment.id,
                customer_id=payment.customer_id,
                reason=result.reason,
                context={**result.context, "rule": result.rule, "failure_reason": failure_reason},
                evaluated_by="policy_engine",
            )
            await self.audit_svc.create(
                actor="recovery_pipeline",
                action=AuditAction.POLICY_EVALUATED.value,
                resource_type="payment",
                resource_id=payment.id,
                description=f"Recovery blocked: {result.reason}",
                payload={"rule": result.rule, "verdict": result.verdict.value},
            )
            await self.db.commit()
            return RecoveryPipelineResult(
                success=False, reason=result.reason, payment_id=payment.id,
            )

        if result.verdict == PolicyVerdict.HUMAN_REVIEW:
            await self.policy_svc.create(
                decision_type="recovery_eligible",
                outcome="deferred",
                payment_id=payment.id,
                customer_id=payment.customer_id,
                reason=result.reason,
                context={**result.context, "rule": result.rule, "failure_reason": failure_reason},
                evaluated_by="policy_engine",
            )
            await self.audit_svc.create(
                actor="recovery_pipeline",
                action=AuditAction.POLICY_EVALUATED.value,
                resource_type="payment",
                resource_id=payment.id,
                description=f"Recovery deferred to human review: {result.reason}",
                payload={"rule": result.rule, "verdict": result.verdict.value},
            )
            await self.db.commit()
            return RecoveryPipelineResult(
                success=False, reason=f"Human review required: {result.reason}", payment_id=payment.id,
            )

        # RECOVERY_CANDIDATE — proceed
        await self.policy_svc.create(
            decision_type="recovery_eligible",
            outcome="approved",
            payment_id=payment.id,
            customer_id=payment.customer_id,
            reason=result.reason,
            context={**result.context, "rule": result.rule, "failure_reason": failure_reason},
            evaluated_by="policy_engine",
        )

        # 4. Transition payment: failed → recovery_pending
        try:
            payment = await self.transition_svc.transition(
                payment_id=str(payment.id),
                target_status=PaymentStatus.RECOVERY_PENDING.value,
                failure_reason=failure_reason,
                payment_id_razorpay=razorpay_payment_id,
            )
        except (InvalidTransitionError, ValueError) as e:
            logger.warning(
                "pipeline_transition_failed",
                extra={"payment_id": str(payment.id), "error": str(e)},
            )
            await self.audit_svc.create(
                actor="recovery_pipeline",
                action=AuditAction.PAYMENT_PROCESSED.value,
                resource_type="payment",
                resource_id=payment.id,
                description=f"Transition failed: {e}",
                payload={"target_status": "recovery_pending", "error": str(e)},
            )
            await self.db.commit()
            return RecoveryPipelineResult(success=False, reason=str(e), payment_id=payment.id)

        # 5. Create recovery attempt
        attempt = await self.attempt_svc.create(
            customer_id=payment.customer_id,
            payment_id=payment.id,
            channel="email",
            amount=payment.amount,
        )

        # 6. Send recovery email
        try:
            email_msg = await self._send_recovery_email(payment, attempt)
        except Exception as e:
            logger.error(
                "pipeline_email_send_failed",
                extra={"payment_id": str(payment.id), "error": str(e)},
            )
            email_msg = None

        # 7. Audit log
        audit_payload = {
            "recovery_attempt_id": str(attempt.id),
            "email_message_id": str(email_msg.id) if email_msg else None,
            "failure_reason": failure_reason,
            "amount": payment.amount,
        }
        if agent_result and agent_result.get("success"):
            trace = agent_result.get("trace", {})
            stages = trace.get("stages", [])
            if stages:
                last_stage = stages[-1]
                diagnosis_data = last_stage.get("output_data", {})
                audit_payload["agent_diagnosis"] = diagnosis_data.get("diagnosis_summary", {})

        audit = await self.audit_svc.create(
            actor="recovery_pipeline",
            action=AuditAction.RECOVERY_ATTEMPTED.value,
            resource_type="payment",
            resource_id=payment.id,
            description=f"Recovery initiated for ₹{payment.amount // 100} — {failure_reason}",
            payload=audit_payload,
        )

        await self.db.commit()

        logger.info(
            "pipeline_completed",
            extra={
                "payment_id": str(payment.id),
                "attempt_id": str(attempt.id),
                "email_sent": email_msg is not None,
            },
        )

        return RecoveryPipelineResult(
            success=True,
            reason="Recovery initiated",
            payment_id=payment.id,
            recovery_attempt_id=attempt.id,
            email_message_id=email_msg.id if email_msg else None,
            audit_log_id=audit.id,
        )

    async def _send_recovery_email(self, payment: Payment, attempt) -> object | None:
        """Send recovery email via Resend with a real Razorpay payment link."""
        from app.models.email_message import EmailMessage, EmailDirection, EmailStatus
        from app.services.payments.razorpay_service import RazorpayService

        razorpay_svc = RazorpayService(db=self.db)
        retry_link = f"https://pay.recoverflow.in/retry/{attempt.id}"  # fallback

        try:
            pl_result = await razorpay_svc.create_payment_link(
                customer_email=payment.customer_email,
                amount=payment.amount,
                description=f"Recovery attempt for order {payment.razorpay_order_id[:20]}",
            )
            if pl_result.get("short_url"):
                retry_link = pl_result["short_url"]
                attempt.recovery_link = retry_link
                await self.db.flush()
        except Exception as e:
            logger.warning("pipeline_razorpay_link_fallback", extra={"error": str(e), "payment_id": str(payment.id)})

        template_name = "payment_failure"

        rendered = await self.template_svc.render(
            template_name,
            {"payment_link": retry_link},
        )

        if rendered:
            subject, body = rendered
            template_id = (await self.template_svc.get_by_name(template_name)).id
        else:
            logger.warning(
                "pipeline_email_template_fallback",
                extra={"payment_id": str(payment.id), "template_name": template_name},
            )
            subject = f"Payment failed — please retry"
            body = (
                f"<h2>Payment failed.</h2>"
                f"<p>Your payment could not be processed. No amount was deducted.</p>"
                f"<p>You can securely retry your payment here:</p>"
                f'<p><a href="{retry_link}" style="display:inline-block;padding:12px 28px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">Retry Payment</a></p>'
                f'<p style="color:#666;font-size:13px;">— RecoverFlow</p>'
            )
            template_id = None

        result: EmailSendResult = await self.email_svc.send_email(
            to=payment.customer_email,
            subject=subject,
            body=body,
        )

        if result.success:
            email_msg = EmailMessage(
                customer_id=payment.customer_id,
                direction=EmailDirection.OUTBOUND.value,
                status=EmailStatus.SENT.value,
                subject=subject,
                recipient_email=payment.customer_email,
                sender_email=settings.RECOVERY_EMAIL_FROM or DEFAULT_FROM_EMAIL,
                template_id=template_id,
                provider_message_id=result.provider_message_id,
                sent_at=datetime.now(timezone.utc),
            )
            self.db.add(email_msg)
            await self.db.flush()

            attempt.email_message_id = email_msg.id
            attempt.status = "sent"
            attempt.sent_at = datetime.now(timezone.utc)
            attempt.recovery_link = retry_link
            await self.db.flush()

            logger.info(
                "pipeline_recovery_email_sent",
                extra={
                    "payment_id": str(payment.id),
                    "email_message_id": str(email_msg.id),
                    "provider_message_id": result.provider_message_id,
                    "template_name": template_name,
                },
            )
            return email_msg

        # ── Failure path ──
        error_category = result.error_category or EmailSendErrorCategory.UNKNOWN
        error_detail = result.error_message or "Unknown error"

        logger.error(
            "pipeline_recovery_email_failed",
            extra={
                "payment_id": str(payment.id),
                "error_category": error_category.value,
                "error": error_detail,
                "status_code": result.status_code,
            },
        )

        email_msg = EmailMessage(
            customer_id=payment.customer_id,
            direction=EmailDirection.OUTBOUND.value,
            status=EmailStatus.FAILED.value,
            subject=subject,
            recipient_email=payment.customer_email,
            sender_email=settings.RECOVERY_EMAIL_FROM or DEFAULT_FROM_EMAIL,
            template_id=template_id,
            provider_message_id=result.provider_message_id,
            error_message=f"[{error_category.value}] {error_detail}",
            failed_at=datetime.now(timezone.utc),
        )
        self.db.add(email_msg)
        await self.db.flush()

        attempt.email_message_id = email_msg.id
        attempt.status = "failed"
        attempt.error_message = f"[{error_category.value}] {error_detail}"
        attempt.failed_at = datetime.now(timezone.utc)
        await self.db.flush()

        return None
