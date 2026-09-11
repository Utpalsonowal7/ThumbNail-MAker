from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import Job
from app.models.thumbnails import Thumbnail
from app.services.gemini_service import generate_from_prompt
from app.services.image_kit_service import upload_image_to_imagekit


async def process_thumbnail_job(db: AsyncSession, job_id: int) -> None:
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        return

    job.status = "PROCESSING"
    await db.commit()

    try:
        generated_image = await generate_from_prompt(job.prompt)

        image_url = await upload_image_to_imagekit(
            generated_image,
            f"thumbnail-{job.id}.png",
        )

        thumbnail = Thumbnail(
            user_id=job.user_id,
            job_id=job.id,
            generatedImageUrl=image_url,
        )
        db.add(thumbnail)

        job.status = "COMPLETED"
        await db.commit()

    except Exception as error:
        thumbnail = Thumbnail(
            user_id=job.user_id,
            job_id=job.id,
            generatedImageUrl=None,
            errorMessage=str(error),
        )
        db.add(thumbnail)

        job.status = "FAILED"
        await db.commit()

        raise
