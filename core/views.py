from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import os
from pathlib import Path

def logout_to_home(request):
    logout(request)
    return redirect('core:index')

@require_http_methods(["GET"])
def manifest(request):
    """Serve the manifest.json file with correct content type"""
    manifest_path = Path(__file__).resolve().parent.parent / 'sales_app' / 'static' / 'manifest.json'
    
    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        return JsonResponse(manifest_data, content_type='application/manifest+json')
    except FileNotFoundError:
        return JsonResponse({'error': 'Manifest not found'}, status=404)

from django.views import View
from django.shortcuts import render


class Index(View):
    def get(self, request):
        context = {} 
        return render(request, 'core/home.html', context)