from django.db import connection
from django.utils.deprecation import MiddlewareMixin

class SetDatabaseRoleMiddleware(MiddlewareMixin):
    """
    Middleware que cambia dinámicamente el rol de PostgreSQL según el rol del usuario en la app.
    Compatible con DRF y JWT/session auth.
    """

    ROLE_MAP = {
        'ADMIN': 'rol_admin_db',
        'DOCTOR': 'rol_doctor_db',
        'PACIENTE': 'rol_paciente_db',
    }

    DEFAULT_ROLE = 'rol_lector_db'

    def process_request(self, request):
        # Rutas que no necesitan cambio de rol
        if request.path.startswith("/api/auth/registro") or request.path.startswith("/admin"):
            return

        # Determinar el rol de BD a usar
        db_role = self.DEFAULT_ROLE
        user_role_str = None

        if hasattr(request, 'user') and request.user.is_authenticated:
            user_role_str = str(request.user.rol).upper()
            db_role = self.ROLE_MAP.get(user_role_str, self.DEFAULT_ROLE)

        # Guardamos el rol en request para debugging/logs
        request.db_role = db_role

        # Activar rol en PostgreSQL
        cursor = connection.cursor()
        try:
            cursor.execute(f"SET ROLE {db_role}")
            # Opcional: loggear el rol actual de la sesión
            try:
                cursor.execute("SELECT current_user;")
                current_user = cursor.fetchone()[0]
                print(f"🟢 Rol de BD activado: {db_role} (current_user={current_user})")
            except Exception:
                print(f"🟢 Rol de BD activado: {db_role} (no se pudo obtener current_user)")
        except Exception as e:
            print("⚠️ Error activando rol de BD:", e)
            raise
        finally:
            cursor.close()

    def process_response(self, request, response):
        # Resetear rol después de la respuesta
        cursor = connection.cursor()
        try:
            cursor.execute("RESET ROLE")
            print("🔄 Rol de BD reseteado.")
        except Exception as e:
            print("⚠️ Error reseteando rol de BD:", e)
        finally:
            cursor.close()
        return response
