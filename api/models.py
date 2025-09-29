from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, numero_carnet, fecha_nacimiento, nombre, password=None, **extra_fields):
        if not numero_carnet:
            raise ValueError('El número de carnet es obligatorio')
        
        user = self.model(
            numero_carnet=numero_carnet,
            fecha_nacimiento=fecha_nacimiento,
            nombre=nombre,
            **extra_fields
        )
        user.set_password(password) # Cifra la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, numero_carnet, fecha_nacimiento, nombre, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(numero_carnet, fecha_nacimiento, nombre, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DOCTOR = "DOCTOR", "Doctor"
        PACIENTE = "PACIENTE", "Paciente"

    numero_carnet = models.CharField(max_length=20, unique=True, primary_key=True)
    nombre = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    rol = models.CharField(max_length=50, choices=Role.choices, default=Role.PACIENTE)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'numero_carnet'
    REQUIRED_FIELDS = ['nombre', 'fecha_nacimiento']

    def __str__(self):
        return f"{self.nombre} ({self.get_rol_display()})"


class Specialty(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Queue(models.Model):
    nombre = models.CharField(max_length=100)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name='queues')
    # Relacionamos la fila con un usuario que TENGA el rol de Doctor.
    # Es opcional, para filas generales.
    doctor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True, 
        related_name='queues_assigned',
        limit_choices_to={'rol': User.Role.DOCTOR}
    )
    
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()
    fichas_maximas = models.PositiveIntegerField(null=True, blank=True)
    
    dia_semana = models.IntegerField(choices=[
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
        (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo")
    ])
    
    is_emergency = models.BooleanField(default=False)

    def __str__(self):
        doctor_name = f" (Dr. {self.doctor.nombre})" if self.doctor else ""
        return f"{self.specialty.nombre} - {self.nombre}{doctor_name}"


class Ticket(models.Model):
    # --- AÑADIMOS EL ESTADO DEL TICKET ---
    class Status(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        FINALIZADO = "FINALIZADO", "Finalizado"

    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name='tickets')
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_as_patient')
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_created')
    numero_ficha = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_validez = models.DateField(default=timezone.now)
    
    # Nuevo campo de estado
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVO)

    class Meta:
        unique_together = ('paciente', 'queue', 'fecha_validez')
        ordering = ['numero_ficha']

    def __str__(self):
        return f"Ficha {self.numero_ficha} para {self.paciente.nombre} - {self.status}"