from django.db.models.signals import pre_delete
from django.dispatch import receiver

from task_manager.notes.models import Note


@receiver(pre_delete, sender=Note)
def cleanup_note_images(sender, instance, **kwargs):
    """Remove image files from storage when a note is deleted.

    CASCADE deletes NoteImage rows without calling model.delete(),
    so files must be cleaned up before the rows disappear.
    """
    for image in instance.images.all():
        if image.image:
            image.image.delete(save=False)
