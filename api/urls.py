from django.urls import path
from . import views

urlpatterns = [
    path('route/', views.RouteFuelView.as_view(), name='route-fuel'),
    path('route', views.RouteFuelView.as_view(), name='route-fuel-no-slash'),
]
