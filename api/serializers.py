from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Specialty, Queue, Ticket

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['numero_carnet', 'nombre', 'fecha_nacimiento', 'rol', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'rol': {'read_only': True} 
        }

    def create(self, validated_data):
        validated_data['rol'] = User.Role.PACIENTE  
        user = User.objects.create_user(**validated_data)
        return user
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['numero_carnet', 'nombre', 'fecha_nacimiento', 'rol']
        read_only_fields = ['numero_carnet', 'rol']

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
    doctor_name = serializers.CharField(source='doctor.nombre', read_only=True, default=None)
    
    # Campo calculado
    disponibles_hoy = serializers.SerializerMethodField()

    dias_semana = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False, allow_empty=True
    )
    dia_semana = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Queue
        fields = [
            'id', 'nombre', 'specialty', 'specialty_name',
            'doctor', 'doctor_name',
            'hora_apertura', 'hora_cierre', 'fichas_maximas',
            'disponibles_hoy', 
            'dia_semana', 'dias_semana', 'is_emergency'
        ]

    def get_disponibles_hoy(self, obj):
        # 1. Manejo de filas ilimitadas (fichas_maximas es None)
        if obj.fichas_maximas is None:
            return 999 # Retornamos un número alto para indicar disponibilidad

        # Importamos aquí para asegurar que no falte
        from django.utils import timezone
        hoy = timezone.now().date()

        # Usamos 'obj.tickets' 
        try:
            tickets_emitidos = obj.tickets.filter(fecha_creacion__date=hoy).count()
            disponibles = obj.fichas_maximas - tickets_emitidos
            return max(disponibles, 0)
        except Exception as e:
            print(f"Error calculando disponibilidad en fila {obj.id}: {e}")
            return 0

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Normalizamos: si dias_semana está vacío y dia_semana existe, convertir a lista legible
        dias = instance.dias_semana if instance.dias_semana else ([instance.dia_semana] if instance.dia_semana is not None else [])
        data['dias_semana'] = dias
        # también opcionalmente mantener dia_semana para compatibilidad
        data['dia_semana'] = instance.dia_semana
        return data

    def create(self, validated_data):
        # Extraer dias_semana y dia_semana sin que confundan
        dias = validated_data.pop('dias_semana', [])
        dia = validated_data.pop('dia_semana', None)
        queue = super().create(validated_data)
        # Guardar dias_semana si viene; si no viene pero dia tiene valor, lo ponemos como lista simple
        if dias:
            queue.dias_semana = dias
        elif dia is not None:
            queue.dias_semana = [dia]
        queue.save(update_fields=['dias_semana'])
        return queue

    def update(self, instance, validated_data):
        dias = validated_data.pop('dias_semana', None)
        dia = validated_data.pop('dia_semana', None)
        instance = super().update(instance, validated_data)
        if dias is not None:
            instance.dias_semana = dias
            instance.save(update_fields=['dias_semana'])
        elif dia is not None:
            instance.dias_semana = [dia]
            instance.save(update_fields=['dias_semana'])
        return instance
class TicketSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.nombre', read_only=True)
    queue_nombre = serializers.CharField(source='queue.nombre', read_only=True)
    specialty_nombre = serializers.CharField(source='queue.specialty.nombre', read_only=True, default="General")
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'queue', 'queue_nombre', 
            'specialty_nombre', 
            'paciente', 'paciente_nombre', 
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
        read_only_fields = ['numero_carnet']

    def update(self, instance, validated_data):
        # Campos que permitimos actualizar a través de este serializador
        allowed_fields = ['nombre', 'fecha_nacimiento', 'rol', 'is_active']
        fields_to_update = []

        # Iteramos sobre los datos validados que llegaron en la petición PATCH
        for field, value in validated_data.items():
            if field in allowed_fields:
                # Usamos setattr para actualizar el atributo en la instancia del modelo
                setattr(instance, field, value)
                fields_to_update.append(field)


        # Guardamos la instancia, pero le decimos a Django que SOLO actualice
        # los campos que hemos modificado. Esto evita activar efectos
        # secundarios en el método .save() del modelo relacionados con otros
        # campos (como el password).
        if fields_to_update:
            instance.save(update_fields=fields_to_update)

        return instance