# api/middleware.py
from django.db import connection

class SetDatabaseRoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        if request.path.startswith("/api/auth/registro") or request.path.startswith("/admin"):
            return self.get_response(request)
        
        # Mapeamos los roles de Django a los roles de la base de datos
        # Nota: Los nombres deben coincidir con los que creaste en PostgreSQL
        role_map = {
            'ADMIN': 'rol_admin_db',
            'DOCTOR': 'rol_doctor_db',
            'PACIENTE': 'rol_paciente_db',
        }

        # Por defecto, usamos un rol de solo lectura si el usuario no está autenticado
        # o no tiene un rol específico.
        db_role = 'rol_lector_db'

        # Si el usuario está autenticado y tiene un rol en nuestra app...
        if hasattr(request, 'user') and request.user.is_authenticated:
            # ...obtenemos el rol correspondiente de la base de datos
            db_role = role_map.get(request.user.rol, 'rol_lector_db')

        cursor = connection.cursor()
        try:
            # Establecemos el rol para la duración de esta petición
            cursor.execute(f"SET ROLE {db_role}")
            
            # Procesamos la vista
            response = self.get_response(request)
            
        finally:
            # MUY IMPORTANTE: Reseteamos el rol al final de la petición
            
            # para que la conexión vuelva a su estado original para la siguiente petición.
            cursor.execute("RESET ROLE")
            cursor.close()

        return response