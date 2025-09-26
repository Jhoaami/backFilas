from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Specialty, Queue, Ticket

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['numero_carnet', 'nombre', 'fecha_nacimiento', 'rol', 'password']
        extra_kwargs = {
            'password': {'write_only': True} # La contraseña no se debe enviar de vuelta
        }

    def create(self, validated_data):
        # Usamos el gestor personalizado para crear el usuario y cifrar la contraseña
        user = User.objects.create_user(**validated_data)
        return user

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = '__all__'

class QueueSerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source='specialty.nombre', read_only=True)
    
    class Meta:
        model = Queue
        fields = ['id', 'nombre', 'nombre_doctor', 'specialty', 'specialty_name', 'hora_apertura', 'hora_cierre', 'fichas_maximas', 'dia_semana', 'is_emergency']

class TicketSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.nombre', read_only=True)
    queue_nombre = serializers.CharField(source='queue.nombre', read_only=True)
    
    class Meta:
        model = Ticket
        fields = ['id', 'queue', 'queue_nombre', 'paciente', 'paciente_nombre', 'creado_por', 'creado_por_nombre', 'numero_ficha', 'fecha_creacion', 'fecha_validez']
        read_only_fields = ['numero_ficha', 'creado_por', 'fecha_validez'] # Estos se asignan en la lógica de la vista

# Serializer para el login personalizado
class CustomTokenObtainPairSerializer(serializers.Serializer):
    numero_carnet = serializers.CharField()
    fecha_nacimiento = serializers.DateField()

    def validate(self, attrs):
        numero_carnet = attrs.get('numero_carnet')
        fecha_nacimiento = attrs.get('fecha_nacimiento')

        try:
            user = User.objects.get(numero_carnet=numero_carnet)
        except User.DoesNotExist:
            raise serializers.ValidationError("Credenciales incorrectas.")

        # Comparamos la fecha de nacimiento
        if user.fecha_nacimiento != fecha_nacimiento:
            raise serializers.ValidationError("Credenciales incorrectas.")

        if not user.is_active:
            raise serializers.ValidationError("Usuario inactivo.")
        
        # Si todo es correcto, generamos el token manualmente
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data # Enviamos también los datos del usuario
        }