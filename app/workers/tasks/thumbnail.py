from app.core.db import sessionLocal
from app.models.user import User
from app.services.thumbnail_service import process_thumbnail_job


async def generate_thumbnail(ctx, job_id: int):
    print(f"✅ ARQ COMPLETED thumbnail job: {job_id}")

    async with sessionLocal() as db:
        await process_thumbnail_job(db, job_id)

    print(f"✅ ARQ COMPLETED thumbnail job: {job_id}")
