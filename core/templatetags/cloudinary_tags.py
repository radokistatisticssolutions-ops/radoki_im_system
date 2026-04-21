"""
Template filters and tags for proper Cloudinary URL handling.
"""
from django import template
from django.conf import settings
import os

register = template.Library()


@register.filter
def cloudinary_file_url(file_field):
    """
    Generate a correct Cloudinary URL for any file type (images, PDFs, documents, etc.).
    
    Handles:
    - Images: uses /image/upload/ delivery
    - PDFs and Documents: uses /raw/upload/ delivery for proper content-type serving
    - Other files: uses standard Cloudinary URL
    
    Falls back to .url property if something goes wrong.
    """
    if not file_field or not file_field.name:
        return ''
    
    try:
        # Try to use the file field's URL first (handles all storage backends)
        url = file_field.url
        
        # If it's a Cloudinary URL and it's a document, adjust it to use proper delivery
        if url and 'res.cloudinary.com' in url:
            cloud_name = settings.CLOUDINARY_CLOUD_NAME
            file_name = file_field.name
            
            # Determine file type
            _, ext = os.path.splitext(file_name)
            ext = ext.lower()
            
            # For PDFs and other documents, ensure we use the correct delivery endpoint
            if ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.txt', '.rtf']:
                # The cloudinary_storage should already give us the right URL
                # But if it doesn't, we can construct it manually
                public_id = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
                
                # Check if URL already has /raw/ or if it needs it
                if '/image/upload/' in url:
                    # Replace /image/upload/ with /raw/upload/ for documents
                    url = url.replace('/image/upload/', '/raw/upload/')
                elif '/upload/' in url and '/raw/upload/' not in url:
                    # Replace /upload/ with /raw/upload/ for documents
                    url = url.replace('/upload/', '/raw/upload/')
        
        return url
        
    except Exception as e:
        import logging
        logging.warning(f"Could not generate Cloudinary URL for {file_field.name}: {str(e)}")
        return ''


@register.filter
def file_exists(file_field):
    """Check if a file exists in storage."""
    if not file_field or not file_field.name:
        return False
    
    try:
        from django.core.files.storage import default_storage
        return default_storage.exists(file_field.name)
    except Exception:
        return False


@register.filter
def file_size_display(file_field):
    """Display file size in human-readable format."""
    if not file_field or not file_field.name:
        return '0 B'
    
    try:
        size = file_field.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
    except Exception:
        return '? B'
