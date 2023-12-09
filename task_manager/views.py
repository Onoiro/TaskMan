from django.shortcuts import render
from django.utils.translation import gettext as _


def index(request):
    task_manager = _("Task manager")
    users = _("Users")
    statuses = _("Statuses")
    labels = _("Labels")
    tasks = _("Tasks")
    exit = _("Exit")
    hello_from_hexlet = _("Hello from Hexlet!")
    coding_courses = _('Practical programming courses')
    read_more = _("Read more")
    return render(request, 'index.html',
                  context={'task_manager': task_manager,
                           'users': users,
                           'statuses': statuses,
                           'labels': labels,
                           'tasks': tasks,
                           'exit': exit,
                           'hello_from_hexlet': hello_from_hexlet,
                           'coding_courses': coding_courses,
                           'read_more': read_more,
                           })
