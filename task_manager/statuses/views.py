from django.shortcuts import render

def index(request):
    return render(request, 'statuses/statuses.html', context={
        'status': 'START',
    })
