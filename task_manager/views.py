from django.shortcuts import render
from django.utils.translation import gettext


def index(request):
    task_manager = gettext("Task manager")
    users = gettext("Users")
    statuses = gettext("Statuses")
    labels = gettext("Labels")
    tasks = gettext("Tasks")
    return render(request, 'index.html',
                  context={'task_manager': task_manager,
                           'users': users,
                           'statuses': statuses,
                           'labels': labels,
                           'tasks': tasks
                           })
