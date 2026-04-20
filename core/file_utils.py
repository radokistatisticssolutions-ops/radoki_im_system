"""
Utility functions for handling file serving from both local and Cloudinary storage.
"""
import os
import logging
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


def serve_file_response(file_field, force_download=False, filename=None):
    """
    Serve a file from either local storage or Cloudinary.
    
    Args:
        file_field: Django FileField instance
        force_download: If True, set Content-Disposition to attachment for download
        filename: Optional filename for download (defaults to original filename)
    
    Returns:
        HttpResponse or FileResponse with file content
    
    Raises:
        Exception: If file cannot be read
    """
    if not file_field or not file_field.name:
        raise ValueError("File field is empty or invalid")
    
    try:
        # Try to open and read the file
        with file_field.open('rb') as file_obj:
            file_content = file_obj.read()
        
        # Determine content type
        import mimetypes
        file_path = file_field.name
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Create response
        response = HttpResponse(file_content, content_type=content_type)
        
        # Set filename for download
        if force_download:
            dl_filename = filename or os.path.basename(file_path)
            response['Content-Disposition'] = f'attachment; filename="{dl_filename}"'
        
        response['Content-Length'] = len(file_content)
        return response
        
    except Exception as e:
        logger.error(f"Error serving file {file_field.name}: {str(e)}", exc_info=True)
        raise


def get_file_url(file_field):
    """
    Get the URL for a file, handling both local and Cloudinary storage.
    For local files, returns /media/... path.
    For Cloudinary files, returns the Cloudinary URL.
    
    Args:
        file_field: Django FileField instance
    
    Returns:
        URL string or None if file is empty
    """
    if not file_field or not file_field.name:
        return None
    
    try:
        # Try to get the URL from the storage backend
        url = file_field.url
        return url
    except Exception as e:
        logger.warning(f"Could not get URL for file {file_field.name}: {str(e)}")
        # Fallback: construct local media URL
        return f"{settings.MEDIA_URL}{file_field.name}"


def file_exists(file_field):
    """
    Check if a file actually exists (either locally or on Cloudinary).
    
    Args:
        file_field: Django FileField instance
    
    Returns:
        Boolean indicating if file exists
    """
    if not file_field or not file_field.name:
        return False
    
    try:
        # Check if file exists in storage
        return default_storage.exists(file_field.name)
    except Exception as e:
        logger.warning(f"Could not check if file exists {file_field.name}: {str(e)}")
        return False
