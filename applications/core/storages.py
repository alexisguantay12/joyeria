# applications/core/storages.py
from django.core.files.storage import FileSystemStorage
from django.conf import settings

class MediaLocalStorage(FileSystemStorage):
    """
    Storage para guardar archivos en MEDIA_ROOT (local),
    y servirlos siempre desde '/media/' independientemente
    de lo que diga settings.MEDIA_URL.
    """
    def __init__(self, *args, **kwargs):
        # ubicación en disco
        kwargs.setdefault('location', settings.MEDIA_ROOT)
        # URL pública fija para archivos locales
        kwargs.setdefault('base_url', '/media/')
        super().__init__(*args, **kwargs)