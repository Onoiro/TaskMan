from django.db.models.signals import pre_delete
from django.dispatch import receiver

from task_manager.notes.models import Note


@receiver(pre_delete, sender=Note)
def cleanup_note_uploads(sender, instance, **kwargs):
    """Remove stored files when a note is deleted.

    CASCADE deletes NoteImage and NoteFile rows without calling their
    model.delete(), so files must be cleaned up before the rows disappear.
    """
    for image in instance.images.all():
        if image.image:
            image.image.delete(save=False)

    for note_file in instance.files.all():
        if note_file.file:
            note_file.file.delete(save=False)
