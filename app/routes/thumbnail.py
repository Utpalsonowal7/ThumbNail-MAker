from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.redis as redis
from app.core.db import get_session
from app.models.jobs import Job
from app.models.user import User
from app.services.image_kit_service import upload_image_to_imagekit
from app.workers import queue
from fastapi import HTTPException
from sqlalchemy import select
from app.models.thumbnails import Thumbnail

# from app.services.auth import get_current_user

router = APIRouter(
    prefix="/thumbnails",
    tags=["Thumbnails"],
)


@router.post("/generate")
async def generate_thumbnail(
    prompt: str = Form(...),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_session),
#     current_user: User = Depends(get_current_user),
):
    generation_type = "FROM_SCRATCH"
    original_image_url = None

    if image:
        image_data = await image.read()

        original_image_url = await upload_image_to_imagekit(
            image_data=image_data,
            file_name=f"source-{uuid4()}.jpg",
        )

        generation_type = "EDIT_IMAGE"

    job = Job(
        user_id=2,
        prompt=prompt,
        originalImageUrl=original_image_url,
        generationType=generation_type,
        status="QUEUED",
    )

    db.add(job)

    await db.flush()
    await db.commit()

    await queue.redis_pool.enqueue_job(
        "generate_thumbnail",
        job.id,
    )

    return {
        "message": "Thumbnail generation queued",
        "jobId": job.id,
        "generationType": generation_type,
        "status": "QUEUED",
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    result = await db.execute(select(Thumbnail).where(Thumbnail.job_id == job.id))

    thumbnail = result.scalar_one_or_none()

    return {
        "jobId": job.id,
        "status": job.status,
        "generationType": job.generationType,
        "imageUrl": thumbnail.generatedImageUrl if thumbnail else None,
        "error": thumbnail.errorMessage if thumbnail else None,
    }
