from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, CustomTokenObtainPairView,
    SpecialtyViewSet, QueueViewSet,
    AvailableQueuesView, CreateTicketView, MyTicketsView, QueueTicketsView,
    DoctorQueuesView, UpdateTicketStatusView
)

router = DefaultRouter()
# Rutas para Admins 
router.register(r'especialidades', SpecialtyViewSet, basename='specialty')
router.register(r'filas', QueueViewSet, basename='queue-admin')

urlpatterns = [
    # Autenticación
    path('auth/registro/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # Rutas para la gestión de Administradores
    path('gestion/', include(router.urls)),
    
    # Rutas para Doctores
    path('doctor/mis-filas/', DoctorQueuesView.as_view(), name='doctor-my-queues'),
    path('doctor/tickets/<int:pk>/actualizar-estado/', UpdateTicketStatusView.as_view(), name='doctor-update-ticket-status'),
    
    # Rutas para Pacientes y Generales
    path('filas-disponibles/', AvailableQueuesView.as_view(), name='available-queues'),
    path('filas/<int:queue_id>/tickets/', QueueTicketsView.as_view(), name='queue-tickets'),
    path('tickets/crear/', CreateTicketView.as_view(), name='create-ticket'),
    path('mis-tickets/', MyTicketsView.as_view(), name='my-tickets'),
]