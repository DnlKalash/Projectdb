from django.http import HttpResponse

def dummy_view(request):
    return HttpResponse("Temporary dummy view for tags")
