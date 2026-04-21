"""
Utility functions for handling file serving from both local and Cloudinary storage.
"""
import os
import logging
import mimetypes
import urllib.request
import ssl
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


def _is_using_cloudinary():
    """Check if the project is configured to use Cloudinary storage."""
    return (
        getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') and
        getattr(settings, 'CLOUDINARY_API_KEY', '') and
        getattr(settings, 'CLOUDINARY_API_SECRET', '')
    )


def _fetch_file_from_cloudinary_url(file_url):
    """
    Fetch file content from a Cloudinary URL.
    
    Args:
        file_url: The Cloudinary URL
    
    Returns:
        File content as bytes
    
    Raises:
        Exception: If file cannot be fetched
    """
    try:
        # Create an SSL context that properly validates certificates
        ssl_context = ssl.create_default_context()
        
        # Create a request with proper headers
        request = urllib.request.Request(
            file_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        # Use urllib to fetch the file from Cloudinary URL
        with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
            file_content = response.read()
            
        if not file_content:
            raise ValueError(f"Received empty response from {file_url}")
            
        return file_content
        
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP Error {e.code} when fetching from Cloudinary URL {file_url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)
    except urllib.error.URLError as e:
        error_msg = f"URL Error when fetching from Cloudinary URL {file_url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Error fetching file from Cloudinary URL {file_url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)


def serve_file_response(file_field, force_download=False, filename=None):
    """
    Serve a file from either local storage or Cloudinary.
    
    Args:
        file_field: Django FileField instance
        force_download: If True, set Content-Disposition to attachment for download
        filename: Optional filename for download (defaults to original filename)
    
    Returns:
        HttpResponse with file content
    
    Raises:
        Exception: If file cannot be read
    """
    if not file_field or not file_field.name:
        raise ValueError("File field is empty or invalid")
    
    try:
        file_path = file_field.name
        file_content = None
        file_url = None
        
        # Check if using Cloudinary storage
        if _is_using_cloudinary():
            try:
                # For Cloudinary, get the URL and fetch the content from it
                file_url = file_field.url
                
                logger.debug(f"Original file URL from cloudinary_storage: {file_url}")
                
                # Ensure it's an absolute URL
                if file_url and (file_url.startswith('http://') or file_url.startswith('https://')):
                    # For documents (PDFs, etc.), transform the URL if needed
                    # Check file extension
                    _, ext = os.path.splitext(file_path)
                    ext = ext.lower()
                    
                    # If it's a document and the URL has /image/upload/, change to /raw/upload/
                    if ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.txt', '.rtf', '.csv']:
                        if '/image/upload/' in file_url:
                            file_url = file_url.replace('/image/upload/', '/raw/upload/')
                            logger.debug(f"Transformed document URL to raw delivery: {file_url}")
                    
                    file_content = _fetch_file_from_cloudinary_url(file_url)
                else:
                    # Fallback: try to open the file directly
                    logger.debug(f"File URL is not absolute, attempting direct file read")
                    with file_field.open('rb') as file_obj:
                        file_content = file_obj.read()
            except Exception as e:
                logger.warning(f"Could not fetch from Cloudinary URL, trying local read: {str(e)}")
                # Fallback to local file reading
                try:
                    with file_field.open('rb') as file_obj:
                        file_content = file_obj.read()
                except Exception as e2:
                    logger.error(f"Fallback local read also failed: {str(e2)}", exc_info=True)
                    raise
        else:
            # For local storage, use the standard approach
            logger.debug(f"Using local storage for file: {file_path}")
            with file_field.open('rb') as file_obj:
                file_content = file_obj.read()
        
        # If still no content, raise error
        if file_content is None:
            raise ValueError(f"Could not read file content from {file_path}")
        
        logger.debug(f"Successfully read {len(file_content)} bytes from {file_path}")
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        logger.debug(f"Content-Type determined as: {content_type}")
        
        # Create response
        response = HttpResponse(file_content, content_type=content_type)
        
        # Set filename for download
        if force_download:
            dl_filename = filename or os.path.basename(file_path)
            response['Content-Disposition'] = f'attachment; filename="{dl_filename}"'
        else:
            # For inline viewing (like PDF preview), use inline disposition
            dl_filename = filename or os.path.basename(file_path)
            response['Content-Disposition'] = f'inline; filename="{dl_filename}"'
        
        response['Content-Length'] = len(file_content)
        
        # Add caching headers for better performance
        if not force_download:  # Don't cache downloads
            response['Cache-Control'] = 'public, max-age=2592000, immutable'  # 30 days
        
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
