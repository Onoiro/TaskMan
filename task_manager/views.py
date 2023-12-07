from django.shortcuts import render
from django.utils.translation import gettext as _


def index(request):
    task_manager = _("Task manager")
    users = _("Users")
    statuses = _("Statuses")
    labels = _("Labels")
    tasks = _("Tasks")
    return render(request, 'index.html',
                  context={'task_manager': task_manager,
                           'users': users,
                           'statuses': statuses,
                           'labels': labels,
                           'tasks': tasks
                           })
