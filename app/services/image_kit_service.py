from app.core.imageKit import imagekit


def upload_image_to_imagekit(file: bytes, file_name: str, folder: str, content_type: str = "image/jpeg") -> str:
     result = imagekit.upload_file(
          file=(file, file_name,content_type),
          filename=file_name,
          folder=folder,
          is_private_file=False,
          use_unique_file_name=True
     )

     return result.url


def get_variants_from_imagekit(image_url: str) -> dict:
    return {
        "youtube": f"{image_url}?tr=w-1280,h-720,c-maintain_ratio,fo-auto",
        "shorts": f"{image_url}?tr=w-1080,h-1920,c-maintain_ratio,fo-auto",
        "square": f"{image_url}?tr=w-1080,h-1080,c-maintain_ratio,fo-auto",
    }
