from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.email_template import EmailTemplate

logger = get_logger(__name__)

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def render_template(template_str: str, variables: dict[str, str]) -> str:
    """Replace {{var}} placeholders with values. Missing vars become empty string."""
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, "")
    return _VAR_PATTERN.sub(_replace, template_str)


class EmailTemplateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_name(self, name: str) -> EmailTemplate | None:
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.name == name)
        )
        return result.scalar_one_or_none()

    async def render(self, name: str, variables: dict[str, str]) -> tuple[str, str] | None:
        """Look up template by name, render subject + body_html. Returns (subject, html) or None."""
        tpl = await self.get_by_name(name)
        if not tpl:
            logger.warning("email_template_not_found", extra={"template_name": name})
            return None

        subject = render_template(tpl.subject, variables)
        body = render_template(tpl.body_html, variables)
        return subject, body
