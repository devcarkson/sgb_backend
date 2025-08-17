from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import etag
from django.utils.cache import get_conditional_response
import os
import mimetypes
from django.conf import settings


def generate_etag(request, path):
    """Generate ETag based on file modification time and size"""
    try:
        full_path = os.path.join(settings.MEDIA_ROOT, path)
        if os.path.exists(full_path):
            stat = os.stat(full_path)
            return f'"{stat.st_mtime}-{stat.st_size}"'
    except (OSError, ValueError):
        pass
    return None


@cache_control(max_age=60*60*24*30, public=True)  # Cache for 30 days
@etag(generate_etag)
def optimized_media_serve(request, path):
    """Serve media files with optimized caching headers"""
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if not os.path.exists(full_path):
        return HttpResponse(status=404)
    
    # Check if client has cached version
    response = get_conditional_response(request)
    if response is not None:
        return response
    
    # Serve the file
    content_type, encoding = mimetypes.guess_type(full_path)
    content_type = content_type or 'application/octet-stream'
    
    with open(full_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=content_type)
    
    # Add additional headers for better caching
    response['Cache-Control'] = 'public, max-age=2592000'  # 30 days
    response['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
    
    return response


def compress_image_on_upload(image_field, max_size=(800, 800), quality=85):
    """Compress image on upload to reduce file size"""
    from PIL import Image
    import io
    from django.core.files.uploadedfile import InMemoryUploadedFile
    
    if not image_field:
        return image_field
    
    # Open the image
    img = Image.open(image_field)
    
    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    # Resize if larger than max_size
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save to BytesIO
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    
    # Create new InMemoryUploadedFile
    return InMemoryUploadedFile(
        output,
        'ImageField',
        f"{image_field.name.split('.')[0]}.jpg",
        'image/jpeg',
        output.getbuffer().nbytes,
        None
    )