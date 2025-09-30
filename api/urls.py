from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, CustomTokenObtainPairView, UserProfileView,
    SpecialtyViewSet, QueueViewSet,
    AvailableQueuesView, CreateTicketView, MyTicketsAllView, MyTicketsTodayView, QueueTicketsView,
    DoctorQueuesView, UpdateTicketStatusView, UserViewSet, PublicSpecialtyView, PublicQueueList
)

# Router para vistas tipo ViewSet (solo admins)
router = DefaultRouter()
router.register(r'especialidades', SpecialtyViewSet, basename='specialty')
router.register(r'filas', QueueViewSet, basename='queue-admin')
router.register(r'usuarios', UserViewSet, basename='user-admin')

urlpatterns = [
    # ----------------- AUTENTICACIÓN -----------------
    path('auth/registro/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/perfil/', UserProfileView.as_view(), name='user-profile'),

    # ----------------- ADMINISTRACIÓN -----------------
    path('gestion/', include(router.urls)),

    # ----------------- DOCTORES -----------------
    path('doctor/mis-filas/', DoctorQueuesView.as_view(), name='doctor-my-queues'),
    path(
        'doctor/tickets/<int:pk>/actualizar-estado/',
        UpdateTicketStatusView.as_view(),
        name='doctor-update-ticket-status'
    ),

    # ----------------- PACIENTES / PÚBLICO -----------------
    path('filas-disponibles/', AvailableQueuesView.as_view(), name='available-queues'),
    path('filas/<int:queue_id>/tickets/', QueueTicketsView.as_view(), name='queue-tickets'),
    path('tickets/crear/', CreateTicketView.as_view(), name='create-ticket'),

    # Nueva separación de vistas
    path('mis-tickets/', MyTicketsAllView.as_view(), name='my-tickets-all'),
    path('mis-tickets/hoy/', MyTicketsTodayView.as_view(), name='my-tickets-today'),

    path('buscar-especialidades/', PublicSpecialtyView.as_view(), name='public-specialties'),
    path('filas-publicas/', PublicQueueList.as_view(), name='public-queues'),
]
