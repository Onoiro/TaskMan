from django.db import migrations

# Exact translated names of the default "Completed" and "Cancelled"
# statuses across all supported locales. Matched strictly (no icontains)
# so custom user statuses with similar names are not affected.
FINAL_STATUS_NAMES = [
    'Completed',
    'Cancelled',
    'Завершена',
    'Отменена',
    'Анҷом ёфтааст',
    'Бекор шудааст',
    'Tamamlandı',
    'Ləğv edildi',
    'Аткарылды',
    'Жокко чыгарылды',
]


def backfill_final_statuses(apps, schema_editor):
    Status = apps.get_model('statuses', 'Status')
    Status.objects.filter(
        name__in=FINAL_STATUS_NAMES,
        is_completed=False,
    ).update(is_completed=True)


def unbackfill_final_statuses(apps, schema_editor):
    Status = apps.get_model('statuses', 'Status')
    Status.objects.filter(
        name__in=FINAL_STATUS_NAMES,
        is_completed=True,
    ).update(is_completed=False)


class Migration(migrations.Migration):

    dependencies = [
        ('statuses', '0004_status_is_completed'),
    ]

    operations = [
        migrations.RunPython(
            backfill_final_statuses,
            unbackfill_final_statuses,
        ),
    ]
