from sqlalchemy import select

from app.core.db import sessionLocal
from app.models.jobs import Job
from app.models.thumbnails import Thumbnail
from app.services.gemini import generate_from_prompt
from app.services.image_kit_service import upload_image_to_imagekit

async def generate_thumbnail(ctx, job_id: int):
    async with sessionLocal() as db:

        # Get the job
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            return

        # Mark job as processing
        job.status = "PROCESSING"
        await db.commit()

        try:
            # Generate image with Gemini
            generated_image = await generate_from_prompt(job.prompt)

            # Upload generated image to ImageKit
            image_url = await upload_image_to_imagekit(
                generated_image,
                f"thumbnail-{job.id}.png",
            )

            # Create thumbnail result
            thumbnail = Thumbnail(
                user_id=job.user_id,
                job_id=job.id,
                generatedImageUrl=image_url,
            )

            db.add(thumbnail)

            # Mark job completed
            job.status = "COMPLETED"

            await db.commit()

        except Exception as error:

            # Save failed result
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
