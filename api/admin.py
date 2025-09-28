# api/admin.py
from django.contrib import admin
from .models import User, Specialty, Queue, Ticket


# ----------------- Custom User -----------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('numero_carnet', 'nombre', 'rol', 'is_active', 'is_staff')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('numero_carnet', 'nombre')
    ordering = ('nombre',)


# ----------------- Specialty -----------------
@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


# ----------------- Queue -----------------
@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'specialty', 'doctor', 
        'hora_apertura', 'hora_cierre', 
        'dia_semana', 'is_emergency'
    )
    list_filter = ('specialty', 'dia_semana', 'is_emergency')
    search_fields = ('nombre', 'specialty__nombre', 'doctor__nombre')


# ----------------- Ticket -----------------
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'numero_ficha', 'queue', 'paciente', 
        'status', 'fecha_creacion', 'fecha_validez'
    )
    list_filter = ('status', 'fecha_validez', 'queue__specialty')
    search_fields = ('paciente__nombre', 'creado_por__nombre', 'queue__nombre')
    ordering = ('-fecha_creacion',)
