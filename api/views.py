from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import filters
from django.utils import timezone
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Specialty, Queue, Ticket
from .serializers import (
    UserSerializer, UserProfileSerializer, SpecialtySerializer, QueueSerializer, TicketSerializer,
    CustomTokenObtainPairSerializer, TicketStatusUpdateSerializer, AdminUserSerializer
)
from .permissions import IsAdmin, IsDoctor # Importamos nuestros permisos

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserProfileView(generics.RetrieveAPIView):
    """
    Devuelve el perfil del usuario autenticado.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# --- VISTAS PARA ADMINISTRADORES ---
class SpecialtyViewSet(viewsets.ModelViewSet):
    """
    API para Crear, Ver, Editar y Eliminar Especialidades.
    Solo para Administradores.
    """
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [IsAdmin]

class QueueViewSet(viewsets.ModelViewSet):
    """
    API para Crear, Ver, Editar y Eliminar Filas.
    Solo para Administradores.
    """
    queryset = Queue.objects.all()
    serializer_class = QueueSerializer
    permission_classes = [IsAdmin]

class UserViewSet(viewsets.ModelViewSet):
    """
    Para que los admins gestionen usuarios:
    - Listar
    - Buscar
    - Cambiar rol
    - Activar/desactivar
    """
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['numero_carnet', 'nombre']
    
# --- VISTAS PARA DOCTORES ---
class DoctorQueuesView(generics.ListAPIView):
    """
    Devuelve las filas asignadas al doctor que hace la petición.
    """
    serializer_class = QueueSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Queue.objects.filter(doctor=self.request.user)

class UpdateTicketStatusView(generics.UpdateAPIView):
    """
    Permite a un doctor finalizar un ticket.
    """
    queryset = Ticket.objects.all()
    serializer_class = TicketStatusUpdateSerializer
    permission_classes = [IsDoctor]

    def update(self, request, *args, **kwargs):
        ticket = self.get_object()
        # Verificación de seguridad: el doctor solo puede modificar tickets de sus propias filas.
        if ticket.queue.doctor != request.user:
            return Response(
                {"error": "No tiene permiso para modificar este ticket."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

class DoctorDailyReportView(APIView):
    """
    Genera un reporte de los pacientes atendidos HOY por el doctor autenticado.
    """
    permission_classes = [IsDoctor] 

    def get(self, request):
        # 1. Obtener fecha de hoy
        hoy = timezone.now().date()
        
        # 2. Filtrar tickets:
        tickets = Ticket.objects.filter(
            queue__doctor=request.user,
            
            # Usamos fecha_validez para asegurar que son tickets de hoy
            fecha_validez=hoy,
            
            status='FINALIZADO' 
        ).order_by('fecha_creacion')

        # 3. Calcular estadísticas
        total_atendidos = tickets.count()
        
        # 4. Serializar
        serializer = TicketSerializer(tickets, many=True)
        
        return Response({
            "doctor_nombre": request.user.nombre,
            "fecha": str(hoy), # Convertimos a string para evitar problemas de formato
            "total_atendidos": total_atendidos,
            "tickets": serializer.data
        }, status=status.HTTP_200_OK)
        
# --- VISTAS PARA PACIENTES Y PÚBLICAS ---

class AvailableQueuesView(generics.ListAPIView):
    serializer_class = QueueSerializer
    permission_classes = [permissions.IsAuthenticated] # paciente o doctor

    def get_queryset(self):
        today = timezone.localtime(timezone.now())
        current_day = today.weekday()  # Lunes=0 ... Domingo=6

        # Filas de emergencia siempre incluidas
        qs = Queue.objects.filter(is_emergency=True)

        # Filas regulares: aquellas que tengan current_day en dias_semana (si existe),
        # o coincidan con dia_semana como fallback
        regular_qs = Queue.objects.exclude(is_emergency=True)
        # Filtrar mediante Python por la presencia en el array/valor.
        # Hacemos esto en Python porque dias_semana es JSONField y la consulta puede variar según DB.
        result_ids = []
        for q in regular_qs:
            dias = q.dias_semana if q.dias_semana else ([q.dia_semana] if q.dia_semana is not None else [])
            if current_day in dias:
                result_ids.append(q.id)

        return qs | Queue.objects.filter(id__in=result_ids)

class CreateTicketView(APIView):
    """
    Permite a un usuario autenticado sacar una ficha.
    Aquí está la lógica más importante.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic # Asegura que todas las operaciones de DB se completen o ninguna lo haga
    def post(self, request, *args, **kwargs):
        user = request.user
        queue_id = request.data.get('queue_id')
        paciente_id = request.data.get('paciente_id', user.numero_carnet) # El doctor puede especificar un paciente

        try:
            queue = Queue.objects.get(id=queue_id)
        except Queue.DoesNotExist:
            return Response({"error": "La fila no existe."}, status=status.HTTP_404_NOT_FOUND)

        # Validaciones de negocio
        now = timezone.localtime(timezone.now())
        today = now.date()

        # 1. ¿La fila está abierta? (No aplica para emergencias)
        if not queue.is_emergency and not (queue.hora_apertura <= now.time() <= queue.hora_cierre):
             return Response({"error": "Esta fila no está aceptando fichas en este momento."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. ¿El paciente ya sacó una ficha para esta fila hoy?
        if Ticket.objects.filter(queue=queue, paciente_id=paciente_id, fecha_validez=today).exists():
             return Response({"error": "El paciente ya tiene una ficha para esta fila hoy."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Si el usuario es un paciente, no puede sacar para otro paciente y solo una ficha al día (no emergencia)
        if user.rol == User.Role.PACIENTE:
            if paciente_id != user.numero_carnet:
                return Response({"error": "No tienes permiso para sacar una ficha para otro paciente."}, status=status.HTTP_403_FORBIDDEN)
            if not queue.is_emergency and Ticket.objects.filter(paciente=user, fecha_validez=today, queue__is_emergency=False).exists():
                return Response({"error": "Ya has sacado tu ficha para una fila general hoy."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. ¿La fila tiene fichas disponibles? (No aplica si es ilimitada)
        if queue.fichas_maximas is not None:
            current_tickets = Ticket.objects.filter(queue=queue, fecha_validez=today).count()
            if current_tickets >= queue.fichas_maximas:
                return Response({"error": "No hay más fichas disponibles en esta fila."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Todo en orden, creamos la ficha
        # Obtenemos el último número de ficha para esta cola en este día y sumamos 1
        last_ticket = Ticket.objects.filter(queue=queue, fecha_validez=today).order_by('-numero_ficha').first()
        new_ticket_number = (last_ticket.numero_ficha + 1) if last_ticket else 1

        ticket = Ticket.objects.create(
            queue=queue,
            paciente_id=paciente_id,
            creado_por=user,
            numero_ficha=new_ticket_number,
            fecha_validez=today
        )

        serializer = TicketSerializer(ticket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MyTicketsAllView(generics.ListAPIView):
    """ Devuelve todas las fichas que tiene el paciente (sin filtrar por fecha). """
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Ticket.objects.filter(paciente=user).order_by('-fecha_creacion')


class MyTicketsTodayView(generics.ListAPIView):
    """ Devuelve las fichas que un paciente tiene para hoy. """
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = timezone.localtime(timezone.now()).date()
        return Ticket.objects.filter(paciente=user, fecha_validez=today)


class QueueTicketsView(generics.ListAPIView):
    """ Vista para la transparencia: devuelve las fichas de una fila para hoy. """
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated] # Cualquiera autenticado puede verlas

    def get_queryset(self):
        queue_id = self.kwargs['queue_id']
        today = timezone.localtime(timezone.now()).date()
        return Ticket.objects.filter(queue_id=queue_id, fecha_validez=today)
    

class PublicSpecialtyView(generics.ListAPIView):
    """
    Permite que cualquier usuario busque especialidades por nombre.
    """
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']


class PublicQueueList(generics.ListAPIView):
    serializer_class = QueueSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Queue.objects.all()