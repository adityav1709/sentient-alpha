import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.domain.models import User

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "testuser"))
        user = result.scalars().first()
        
        if user:
            print(f"User: {user.username}")
            print(f"First Name: {user.first_name}")
            print(f"Last Name: {user.last_name}")
            print(f"LinkedIn: {user.linkedin_handle}")
            print(f"Twitter: {user.twitter_handle}")
            print(f"Avatar ID: {user.avatar_id}")
        else:
            print("User 'testuser' not found.")

if __name__ == "__main__":
    asyncio.run(main())
