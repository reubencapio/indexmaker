"""Team invitations: sending the link, and accepting it."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import organizations
from app.models.organization import OrganizationInvitation, OrganizationMembership
from app.models.user import User

ORG = "/api/v1/organizations"


@pytest.fixture
def mailbox(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    sent: list[dict] = []

    def capture(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
        sent.append({"to": to_email, "subject": subject, "text": text_body or ""})
        return True

    monkeypatch.setattr(organizations, "send_email", capture)
    return sent


async def invite(client: AsyncClient, headers: dict, email: str) -> dict:
    created = await client.post(
        f"{ORG}/", headers=headers, json={"name": "Acme Capital", "slug": "acme-capital"}
    )
    assert created.status_code == 201, created.text
    slug = created.json()["slug"]
    response = await client.post(
        f"{ORG}/{slug}/invitations", headers=headers, json={"email": email, "role": "member"}
    )
    assert response.status_code == 200, response.text
    return response.json() | {"slug": slug}


class TestInvitations:
    async def test_invite_emails_a_link_and_returns_it(
        self, client: AsyncClient, auth_headers, admin_user: User, mailbox
    ):
        invitation = await invite(client, auth_headers, admin_user.email)
        assert mailbox[0]["to"] == admin_user.email
        assert "Acme Capital" in mailbox[0]["subject"]
        assert invitation["invite_url"] in mailbox[0]["text"]
        assert "/invite/" in invitation["invite_url"]

    async def test_link_shows_the_invitation_without_signing_in(
        self, client: AsyncClient, auth_headers, admin_user: User, mailbox
    ):
        invitation = await invite(client, auth_headers, admin_user.email)
        token = invitation["invite_url"].rsplit("/", 1)[1]
        response = await client.get(f"{ORG}/invitations/by-token/{token}")
        assert response.status_code == 200
        assert response.json()["organization_name"] == "Acme Capital"
        assert response.json()["status"] == "pending"

    async def test_invitee_accepts_and_becomes_a_member_once(
        self,
        client: AsyncClient,
        auth_headers,
        admin_auth_headers,
        admin_user: User,
        db_session: AsyncSession,
        mailbox,
    ):
        invitation = await invite(client, auth_headers, admin_user.email.upper())
        token = invitation["invite_url"].rsplit("/", 1)[1]

        accepted = await client.post(
            f"{ORG}/invitations/by-token/{token}/accept", headers=admin_auth_headers
        )
        assert accepted.status_code == 200
        assert accepted.json()["organization_slug"] == invitation["slug"]

        members = (
            (
                await db_session.execute(
                    select(OrganizationMembership).where(
                        OrganizationMembership.user_id == admin_user.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert [m.role for m in members] == ["member"]

        # The new member can now see the organisation.
        listed = await client.get(f"{ORG}/", headers=admin_auth_headers)
        assert [o["slug"] for o in listed.json()] == [invitation["slug"]]

        again = await client.post(
            f"{ORG}/invitations/by-token/{token}/accept", headers=admin_auth_headers
        )
        assert again.status_code == 409

    async def test_a_forwarded_link_does_not_admit_someone_else(
        self, client: AsyncClient, auth_headers, admin_auth_headers, mailbox
    ):
        invitation = await invite(client, auth_headers, "someone.else@example.com")
        token = invitation["invite_url"].rsplit("/", 1)[1]
        response = await client.post(
            f"{ORG}/invitations/by-token/{token}/accept", headers=admin_auth_headers
        )
        assert response.status_code == 403

    async def test_expired_invitation_is_refused(
        self,
        client: AsyncClient,
        auth_headers,
        admin_auth_headers,
        admin_user: User,
        db_session: AsyncSession,
        mailbox,
    ):
        invitation = await invite(client, auth_headers, admin_user.email)
        token = invitation["invite_url"].rsplit("/", 1)[1]
        row = (await db_session.execute(select(OrganizationInvitation))).scalar_one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await db_session.commit()

        shown = await client.get(f"{ORG}/invitations/by-token/{token}")
        assert shown.json()["status"] == "expired"
        response = await client.post(
            f"{ORG}/invitations/by-token/{token}/accept", headers=admin_auth_headers
        )
        assert response.status_code == 409

    async def test_unknown_token_is_404(self, client: AsyncClient):
        assert (await client.get(f"{ORG}/invitations/by-token/nope")).status_code == 404
