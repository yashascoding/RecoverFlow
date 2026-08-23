import sys
sys.path.insert(0, "/home/yashas-bhagwat/RecoverFlow/backend")

from dotenv import load_dotenv
load_dotenv("/home/yashas-bhagwat/RecoverFlow/.env")

from app.services.email.resend_service import send_recovery_email

response = send_recovery_email(
    to_email="bhagwatyashas5@gmail.com",
    customer_name="Yashas",
    payment_id="pay_test_123"
)

print(response)
