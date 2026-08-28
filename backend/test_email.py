import sys
import asyncio

sys.path.insert(0, "/home/yashas-bhagwat/RecoverFlow/backend")

from dotenv import load_dotenv
load_dotenv("/home/yashas-bhagwat/RecoverFlow/.env")

from app.services.email.resend_service import ResendEmailService


async def main():
    svc = ResendEmailService()
    result = await svc.send_email(
        to="bhagwatyashas5@gmail.com",
        subject="Test — RecoverFlow",
        body="<h2>Hi Yashas</h2><p>This is a test email from RecoverFlow.</p>",
    )
    print(f"success={result.success}")
    print(f"provider_message_id={result.provider_message_id}")
    print(f"error_category={result.error_category}")
    print(f"error_message={result.error_message}")


asyncio.run(main())
