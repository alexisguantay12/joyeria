from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

# Create your views here.
@login_required
def home_view(request):
    return render(request,'inicio/inicio.html')