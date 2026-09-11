from app.core.db import sessionLocal
from app.services.thumbnail_service import process_thumbnail_job


async def generate_thumbnail(ctx, job_id: int):
    async with sessionLocal() as db:
        await process_thumbnail_job(db, job_id)
