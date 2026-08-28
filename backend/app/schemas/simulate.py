from __future__ import annotations

import enum

from pydantic import BaseModel, EmailStr, Field


class FailureType(str, enum.Enum):
    UPI_TIMEOUT = "upi_timeout"
    BANK_DECLINED = "bank_declined"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    NETWORK_ERROR = "network_error"
    GATEWAY_ERROR = "gateway_error"
    FRAUD_CHECK = "fraud_check"


FAILURE_DESCRIPTIONS: dict[FailureType, str] = {
    FailureType.UPI_TIMEOUT: "The UPI session timed out. Please try again.",
    FailureType.BANK_DECLINED: "Your card was declined by the issuing bank.",
    FailureType.INSUFFICIENT_FUNDS: "Insufficient funds in your account.",
    FailureType.NETWORK_ERROR: "A network error occurred during the transaction.",
    FailureType.GATEWAY_ERROR: "Payment gateway service unavailable. Please retry.",
    FailureType.FRAUD_CHECK: "Transaction flagged for security review.",
}

FAILURE_CODES: dict[FailureType, str] = {
    FailureType.UPI_TIMEOUT: "UPI_TIMEOUT",
    FailureType.BANK_DECLINED: "BANK_DECLINED",
    FailureType.INSUFFICIENT_FUNDS: "INSUFFICIENT_FUNDS",
    FailureType.NETWORK_ERROR: "NETWORK_ERROR",
    FailureType.GATEWAY_ERROR: "GATEWAY_ERROR",
    FailureType.FRAUD_CHECK: "FRAUD_CHECK",
}


class SimulateFailureRequest(BaseModel):
    customer_email: EmailStr = Field(
        default="test@example.com",
        description="Email for the simulated customer",
    )
    customer_name: str = Field(
        default="Test Customer",
        description="Name for the simulated customer",
    )
    amount: int = Field(
        default=49900,
        gt=0,
        description="Amount in paise (e.g. 49900 = ₹499.00)",
    )
    failure_type: FailureType = Field(
        default=FailureType.UPI_TIMEOUT,
        description="Type of payment failure to simulate",
    )


class SimulateFailureResponse(BaseModel):
    status: str = "failed"
    customer_id: str
    customer_email: str
    payment_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    amount: int
    currency: str
    failure_type: str
    failure_code: str
    failure_reason: str
    email_sent_to: str
    recovery_pipeline: str
    message: str


class SimulateCaptureRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Order ID of the payment to capture")


class SimulateCaptureResponse(BaseModel):
    status: str
    razorpay_order_id: str
    previous_status: str
    new_status: str
    message: str
