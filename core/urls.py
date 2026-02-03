from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('logout_to_home/', views.logout_to_home, name='logout_to_home'),
    path('manifest.json', views.manifest, name='manifest'),
]
