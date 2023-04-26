from django.shortcuts import render,HttpResponse

# Create your views here.

def index(request):
    print(f"http request: {request}")
    return render(request, "index.html")

def api(request):
    if request.method != "GET":
        return HttpResponse()
    Gets = request.GET.dict()
    return HttpResponse(f"bob {Gets} ")
