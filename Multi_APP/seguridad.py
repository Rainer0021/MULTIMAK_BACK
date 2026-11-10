from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from .models import Usuarios, Operador

ADMIN, CONTADOR, OPERADOR = 'administrador', 'contador', 'operador'


def limpiar_rut(valor):
    """'12.345.678-k' -> '12345678K'"""
    return str(valor or '').strip().replace('.', '').replace('-', '').replace(' ', '').upper()


def _control_activo():
    return getattr(settings, 'PERMISOS_POR_ROL', True)


def roles_del_usuario(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {ADMIN}
    cache = getattr(request, '_roles_cache', None)
    if cache is None:
        nombres = {n.lower() for n in user.groups.values_list('name', flat=True)}
        cache = {r for r in (ADMIN, CONTADOR, OPERADOR) if r in nombres}
        request._roles_cache = cache
    return cache


def es_solo_operador(request):
    if not _control_activo():
        return False
    roles = roles_del_usuario(request)
    return OPERADOR in roles and not ({ADMIN, CONTADOR} & roles)


def usuario_negocio(request):
    """Fila de la tabla Usuarios del usuario autenticado (su username es el RUT sin puntos ni guion)."""
    if hasattr(request, '_usuario_negocio'):
        return request._usuario_negocio
    rut = limpiar_rut(request.user.username)
    encontrado = None
    for u in Usuarios.objects.filter(activo=True):
        if limpiar_rut(u.rut) == rut:
            encontrado = u
            break
    request._usuario_negocio = encontrado
    return encontrado


def operador_de(request):
    u = usuario_negocio(request)
    return Operador.objects.filter(usuario=u, activo=True).first() if u else None


class PermisoPorRol(BasePermission):
    """
    Cada ViewSet declara:
        roles_lectura   = ('contador', ...)   # quién puede GET
        roles_escritura = ('contador', ...)   # quién puede POST / PUT / PATCH / DELETE
    El Administrador siempre pasa. Lo que no se declara queda solo para el Administrador.
    """
    message = 'No tienes permiso para realizar esta acción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not _control_activo():
            return True
        roles = roles_del_usuario(request)
        if ADMIN in roles:
            return True
        if request.method in SAFE_METHODS:
            permitidos = getattr(view, 'roles_lectura', ())
        else:
            permitidos = getattr(view, 'roles_escritura', ())
        return bool(roles & set(permitidos))


def solo_roles(*permitidos):
    """Para vistas de función: solo_roles() = solo Administrador; solo_roles('operador') = Operador y Administrador."""
    class _Permiso(BasePermission):
        message = 'No tienes permiso para realizar esta acción.'

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            if not _control_activo():
                return True
            roles = roles_del_usuario(request)
            return ADMIN in roles or bool(roles & set(permitidos))
    return _Permiso


# ---------- Límite de intentos  ----------
class _PorRut(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        rut = limpiar_rut(request.data.get('rut') or request.data.get('username'))
        if not rut:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': rut}


class LoginIPThrottle(AnonRateThrottle):
    scope = 'login_ip'
    rate = '20/min'


class LoginRutThrottle(_PorRut):
    scope = 'login_rut'
    rate = '5/min'


class CambioClaveIPThrottle(AnonRateThrottle):
    scope = 'cambio_clave_ip'
    rate = '20/min'


class CambioClaveRutThrottle(_PorRut):
    scope = 'cambio_clave_rut'
    rate = '5/min'