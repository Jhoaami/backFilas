from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    SpecialtyViewSet,
    QueueViewSet,
    AvailableQueuesView,
    CreateTicketView,
    MyTicketsView,
    QueueTicketsView,
)

# Router para los ViewSets de administrador
router = DefaultRouter()
router.register(r'especialidades', SpecialtyViewSet, basename='especialidad')
router.register(r'filas', QueueViewSet, basename='fila')

urlpatterns = [
    # Rutas de Autenticación
    path('registro/', RegisterView.as_view(), name='registro'),
    path('login/', CustomTokenObtainPairView.as_view(), name='inicio-sesion'),

    # Rutas de administrador (usando router)
    path('', include(router.urls)),

    # Rutas para pacientes y doctores
    path('filas-disponibles/', AvailableQueuesView.as_view(), name='filas-disponibles'),
    path('fichas/crear/', CreateTicketView.as_view(), name='crear-ficha'),
    path('mis-fichas/', MyTicketsView.as_view(), name='mis-fichas'),
    path('filas/<fila_id>/fichas/', QueueTicketsView.as_view(), name='fichas-fila'),
]
