from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# --- GESTOR DE USUARIO PERSONALIZADO ---
# Esto nos permite cambiar el comportamiento por defecto de Django para que el login
# sea con `numero_carnet` en lugar de `username`.
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

# --- MODELO DE USUARIO PERSONALIZADO ---
# Aquí definimos los roles y los campos para el registro y login.
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
    is_staff = models.BooleanField(default=False) # Necesario para el admin de Django

    objects = CustomUserManager()

    USERNAME_FIELD = 'numero_carnet' # Campo para el login
    REQUIRED_FIELDS = ['nombre', 'fecha_nacimiento'] # Campos requeridos al crear un superuser

    def __str__(self):
        return f"{self.nombre} ({self.get_rol_display()})"

# --- MODELO DE ESPECIALIDADES ---
class Specialty(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

# --- MODELO DE FILAS VIRTUALES ---
class Queue(models.Model):
    nombre = models.CharField(max_length=100)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name='queues')

    # Nombre del doctor responsable de la fila (campo requerido)
    nombre_doctor = models.CharField(max_length=100)
    
    # Horarios en que se pueden sacar fichas
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()
    
    # Número máximo de fichas
    fichas_maximas = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Dejar en blanco para fichas ilimitadas (ej. Emergencias)"
    )
    
    # Día de la semana
    dia_semana = models.IntegerField(choices=[
        (1, "Lunes"), (2, "Martes"), (3, "Miércoles"),
        (4, "Jueves"), (5, "Viernes"), (6, "Sábado"), (7, "Domingo")
    ])
    
    is_emergency = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.specialty.nombre} - {self.nombre} ({self.get_dia_semana_display()}) - Dr. {self.nombre_doctor}"
# --- MODELO DE FICHAS (TICKETS) ---
# Aquí se guarda cada ficha que un paciente o doctor saca.
class Ticket(models.Model):
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name='tickets')
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_paciente')
    # Para la transparencia: guardamos quién sacó la ficha.
    # Puede ser el mismo paciente o un doctor.
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_creados')
    numero_ficha = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Fecha para la cual es válida la ficha
    fecha_validez = models.DateField(default=timezone.now)
    class Meta:
        # Un paciente solo puede tener una ficha por fila y por día de validez.
        unique_together = ('paciente', 'queue', 'fecha_validez')
        ordering = ['numero_ficha']

    def __str__(self):
        return f"Ficha {self.numero_ficha} para {self.paciente.nombre} en {self.queue.nombre}"