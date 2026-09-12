import base64

from app.core.gemini import client

MODEL = "gemini-2.5-flash-image"


async def generate_from_prompt(prompt: str) -> bytes:
    
    response = await client.aio.interactions.create(
        model=MODEL,
        input=prompt,
        response_format={
            "type": "image",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )

    return base64.b64decode(response.output_image.data)


async def edit_image(
    prompt: str,
    image_data: bytes,
    mime_type: str,
) -> bytes:

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    response = await client.aio.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "text",
                "text": prompt,
            },
            {
                "type": "image",
                "data": image_base64,
                "mime_type": mime_type,
            },
        ],
        response_format={
            "type": "image",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )

    return base64.b64decode(response.output_image.data)
