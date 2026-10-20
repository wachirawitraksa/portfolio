"""Create the single admin user: python -m scripts.create_user EMAIL [--totp]

Prompts for the password. With --totp it prints the secret to add to an
authenticator app. Run again to reset the password and the TOTP secret,
which also ends every existing session.
"""
import argparse
import asyncio
import getpass
from datetime import datetime, timezone

import pyotp
from sqlalchemy import select, update

from app.db import SessionLocal
from app.models import AuthSession, User
from app.security import hash_password


async def main(email: str, with_totp: bool) -> None:
    password = getpass.getpass("Password: ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters.")
    secret = pyotp.random_base32() if with_totp else None
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if user is None:
            user = User(email=email.lower(), password_hash=hash_password(password), totp_secret=secret)
            db.add(user)
        else:
            user.password_hash = hash_password(password)
            user.totp_secret = secret
            await db.flush()
            await db.execute(
                update(AuthSession)
                .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(timezone.utc))
            )
        await db.commit()
    if secret:
        print("TOTP secret:", secret)
        print("URI:", pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Portfolio admin"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("--totp", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.totp))
