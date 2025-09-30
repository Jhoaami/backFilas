from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Specialty, Queue, Ticket

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['numero_carnet', 'nombre', 'fecha_nacimiento', 'rol', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['numero_carnet', 'nombre', 'fecha_nacimiento', 'rol', 'is_active']
        read_only_fields = ['numero_carnet', 'rol']

class CustomTokenObtainPairSerializer(serializers.Serializer):
    # ... (sin cambios) ...
    numero_carnet = serializers.CharField()
    fecha_nacimiento = serializers.DateField()

    def validate(self, attrs):
        numero_carnet = attrs.get('numero_carnet')
        fecha_nacimiento = attrs.get('fecha_nacimiento')

        try:
            user = User.objects.get(numero_carnet=numero_carnet)
        except User.DoesNotExist:
            raise serializers.ValidationError("Credenciales incorrectas.")

        if user.fecha_nacimiento != fecha_nacimiento:
            raise serializers.ValidationError("Credenciales incorrectas.")

        if not user.is_active:
            raise serializers.ValidationError("Usuario inactivo.")
        
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = '__all__'

class QueueSerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source='specialty.nombre', read_only=True)
    # Mostramos el nombre del doctor, si existe
    doctor_name = serializers.CharField(source='doctor.nombre', read_only=True, default=None)
    
    class Meta:
        model = Queue
        fields = [
            'id', 'nombre', 'specialty', 'specialty_name', 
            'doctor', 'doctor_name',  # Incluimos el ID y el nombre del doctor
            'hora_apertura', 'hora_cierre', 'fichas_maximas', 
            'dia_semana', 'is_emergency'
        ]

class TicketSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.nombre', read_only=True)
    queue_nombre = serializers.CharField(source='queue.nombre', read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'queue', 'queue_nombre', 'paciente', 'paciente_nombre', 
            'creado_por', 'creado_por_nombre', 'numero_ficha', 'fecha_creacion', 
            'fecha_validez', 'status' 
        ]
        read_only_fields = ['numero_ficha', 'creado_por', 'fecha_validez']

# Un serializer simple para que el doctor solo pueda cambiar el estado.
class TicketStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['status']

#Para administrar usuarios  
class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['numero_carnet', 'nombre', 'fecha_nacimiento', 'rol', 'is_active']
        read_only_fields = ['numero_carnet']  # No se puede cambiar la PK

    def update(self, instance, validated_data):
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.fecha_nacimiento = validated_data.get('fecha_nacimiento', instance.fecha_nacimiento)

        # Validamos rol antes de cambiarlo
        rol = validated_data.get('rol', instance.rol)
        if rol in [choice[0] for choice in User.Role.choices]:
            instance.rol = rol

        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()
        return instance