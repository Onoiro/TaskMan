import os

from django.core.files.images import get_image_dimensions
from django.utils.translation import gettext_lazy as _

from task_manager.notes.models import NoteFile, NoteImage


def validate_image_upload(uploaded_file):
    """Validate size and extension of an uploaded image.

    Returns an error message or None when the file is valid.
    Content-type check is delegated to Pillow via ImageField.
    """
    max_bytes = NoteImage.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        return _(
            "Image '%(name)s' is too large. "
            "Maximum size is %(max)s MB."
        ) % {'name': uploaded_file.name, 'max': NoteImage.MAX_IMAGE_SIZE_MB}

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in NoteImage.ALLOWED_IMAGE_EXTENSIONS:
        return _(
            "Image '%(name)s' has unsupported format. "
            "Allowed formats: JPEG, PNG, GIF, WebP."
        ) % {'name': uploaded_file.name}

    try:
        width, height = get_image_dimensions(uploaded_file)
    except Exception:
        return _("Image '%(name)s' is corrupted or not a valid image."
                 ) % {'name': uploaded_file.name}
    if width is None or height is None:
        return _("Image '%(name)s' is corrupted or not a valid image."
                 ) % {'name': uploaded_file.name}

    return None


def validate_file_upload(uploaded_file):
    """Validate size and extension of an uploaded file (non-image).

    Returns an error message or None when the file is valid.
    """
    max_bytes = NoteFile.MAX_FILE_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        return _(
            "File '%(name)s' is too large. "
            "Maximum size is %(max)s MB."
        ) % {'name': uploaded_file.name, 'max': NoteFile.MAX_FILE_SIZE_MB}

    ext = os.path.splitext(uploaded_file.name)[1].lstrip('.').lower()
    if ext not in NoteFile.ALLOWED_EXTENSIONS:
        return _(
            "File '%(name)s' has unsupported format. "
            "Allowed formats: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, "
            "ODT, ODS, ODP, RTF, TXT, MD, CSV, ZIP, 7Z, RAR, TAR, GZ, TGZ, "
            "EML, MSG."
        ) % {'name': uploaded_file.name}

    return None
