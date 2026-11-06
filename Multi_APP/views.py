import hmac
import logging
import boto3
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from botocore.exceptions import NoCredentialsError
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from collections import defaultdict
from django.db.models import Sum, Avg, Count, Max, Q
from django.db import transaction
from django.contrib.auth.hashers import make_password, check_password
import uuid

from .models import (
    Maquinaria, Operador, Report, Usuarios, Gasto,
    Cliente, Contrato, ContratoMaquinaria, HES, Factura, 
    Doc_Maquinaria, Doc_empresa, Mantenimiento
)
from .serializers import (
    MaquinariaSerializer, OperadorSerializer, ReportSerializer, GastoSerializer,
    ClienteSerializer, ContratoSerializer, ContratoMaquinariaSerializer,
    HESSerializer, FacturaSerializer, DocMaquinariaSerializer, DocEmpresaSerializer,
    MantenimientoSerializer, hoy_chile, ESTADOS_CONTRATO_VIGENTES, normalizar_estado_maquina
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class BaseSoftDeleteViewSet(viewsets.ModelViewSet):
    """
    ViewSet base que filtra los registros activos por defecto
    y ejecuta borrado lógico (activo=False) en lugar de DELETE físico.
    Exento de verificación CSRF para peticiones AJAX.
    """
    def get_queryset(self):
        return self.queryset.filter(activo=True)

    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        instancia.activo = False
        instancia.save()
        return Response({'mensaje': 'Registro desactivado correctamente.'}, status=status.HTTP_200_OK)


def _limpiar_rut(valor):
    """'12.345.678-k' -> '12345678K' (para comparar sin importar el formato)."""
    return str(valor or '').strip().replace('.', '').replace('-', '').replace(' ', '').upper()


def _sincronizar_usuario_django(request, usuario_db, contraseña_plana):
    """
    Sincroniza el usuario de la tabla propia 'Usuarios' con la tabla nativa de Django 'auth_user'.
    Asigna automáticamente los grupos nativos (auth_group) según su Rol en el negocio.
    """
    username_rut = _limpiar_rut(usuario_db.rut)
    
    # 1. Obtener o crear el usuario nativo de Django
    user_django, _ = User.objects.get_or_create(username=username_rut)
    user_django.first_name = usuario_db.nombre or ''
    user_django.last_name = usuario_db.apellido or ''
    user_django.set_password(contraseña_plana)
    
    # 2. Determinar el rol y asignar Grupo nativo de Django
    rol_nombre = str(usuario_db.id_rol.rol).strip() if usuario_db.id_rol else ''
    
    if 'admin' in rol_nombre.lower():
        grupo, _ = Group.objects.get_or_create(name='Administrador')
        user_django.groups.add(grupo)
        user_django.is_staff = True  # Otorga acceso al panel /admin/
    elif 'operador' in rol_nombre.lower():
        grupo, _ = Group.objects.get_or_create(name='Operador')
        user_django.groups.add(grupo)
        user_django.is_staff = False
    elif 'contador' in rol_nombre.lower():
        grupo, _ = Group.objects.get_or_create(name='Contador')
        user_django.groups.add(grupo)
        user_django.is_staff = False

    user_django.save()
    
    # 3. Iniciar sesión nativa de Django
    login(request, user_django)
    return user_django


@api_view(['POST'])
@csrf_exempt
@authentication_classes([])
@permission_classes([])
def login_unificado(request):
    try:
        data = request.data or {}

        rut_recibido = _limpiar_rut(data.get('rut') or data.get('username'))
        contraseña_recibida = str(data.get('contraseña') or data.get('password') or '').strip()

        if not rut_recibido or not contraseña_recibida:
            return Response({'error': 'Debe ingresar RUT y contraseña.'}, status=status.HTTP_400_BAD_REQUEST)

        usuario_encontrado = None
        for u in Usuarios.objects.filter(activo=True).select_related('id_rol'):
            if _limpiar_rut(u.rut) == rut_recibido:
                usuario_encontrado = u
                break

        if not usuario_encontrado:
            return Response({'error': 'RUT o contraseña incorrectos.'}, status=status.HTTP_401_UNAUTHORIZED)

        clave_bd = str(usuario_encontrado.contraseña or '').strip()
        es_hash_valido = check_password(contraseña_recibida, clave_bd)
        es_texto_plano = hmac.compare_digest(clave_bd.encode('utf-8'), contraseña_recibida.encode('utf-8'))

        if not (es_hash_valido or es_texto_plano):
            return Response({'error': 'RUT o contraseña incorrectos.'}, status=status.HTTP_401_UNAUTHORIZED)

        if es_texto_plano and not es_hash_valido:
            usuario_encontrado.set_password(contraseña_recibida)
            usuario_encontrado.save(update_fields=['contraseña'])

        user_django = _sincronizar_usuario_django(request._request, usuario_encontrado, contraseña_recibida)

        # GENERACIÓN DEL TOKEN JWT
        refresh = RefreshToken.for_user(user_django)

        rol_nombre = str(usuario_encontrado.id_rol.rol) if usuario_encontrado.id_rol else ''
        id_operador = None
        tipo_licencia = None

        if 'operador' in rol_nombre.lower():
            op = Operador.objects.filter(usuario=usuario_encontrado, activo=True).first()
            if op:
                id_operador = op.pk
                tipo_licencia = op.TipoLicencia

        return Response({
            'mensaje': 'Acceso autorizado',
            'access': str(refresh.access_token),  # Token de acceso
            'refresh': str(refresh),              # Token de refresco
            'id_usuario': usuario_encontrado.pk,
            'rut': usuario_encontrado.rut,
            'nombre': f"{usuario_encontrado.nombre} {usuario_encontrado.apellido}".strip(),
            'rol': rol_nombre,
            'id_operador': id_operador,
            'tipo_licencia': tipo_licencia,
        }, status=status.HTTP_200_OK)

    except Exception:
        logger.exception('Error en login_unificado')
        return Response(
            {'error': 'Error interno del servidor. Intenta nuevamente en unos minutos.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def resumen_kpis(request):
    total_horas = Report.objects.filter(activo=True).aggregate(total=Sum('horas_trabajadas'))['total'] or 0
    promedio_horas_turno = Report.objects.filter(activo=True).aggregate(promedio=Avg('horas_trabajadas'))['promedio'] or 0
    total_gastos = Gasto.objects.filter(activo=True).aggregate(total=Sum('monto'))['total'] or 0
    total_maquinas = Maquinaria.objects.filter(activo=True).count()

    distribucion_flota = list(
        Maquinaria.objects.filter(activo=True).values('estado').annotate(cantidad=Count('id_maquina'))
    )

    return Response({
        'total_horas_trabajadas': total_horas,
        'promedio_horas_por_turno': round(promedio_horas_turno, 1),
        'total_gastos_acumulados': total_gastos,
        'total_maquinarias': total_maquinas,
        'distribucion_flota': distribucion_flota
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def contratos_para_operador(request):
    """
    Contratos vigentes hoy con sus máquinas (sin tarifas).
    El operador elige primero el contrato y luego la máquina de ese contrato.
    """
    hoy = hoy_chile()
    contratos = (
        Contrato.objects.filter(activo=True, estado_contrato__in=ESTADOS_CONTRATO_VIGENTES)
        .filter(Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=hoy))
        .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy))
        .select_related('id_cliente')
        .order_by('nombre_contrato', 'id_contrato')
    )

    maquinas_por_contrato = defaultdict(list)
    relaciones = (
        ContratoMaquinaria.objects.filter(id_contrato__in=contratos, id_maquina__activo=True)
        .select_related('id_maquina')
        .order_by('id_maquina__patente')
    )
    for rel in relaciones:
        m = rel.id_maquina
        maquinas_por_contrato[rel.id_contrato_id].append({
            'id_maquina': m.id_maquina,
            'patente': m.patente,
            'marca': m.marca,
            'modelo': m.modelo,
            'tipo': m.tipo,
            'estado': normalizar_estado_maquina(m.estado),
            'horometro_actual': m.horometro_actual,
        })

    data = [
        {
            'id_contrato': c.id_contrato,
            'nombre': c.nombre_contrato or f'Contrato #{c.id_contrato}',
            'cliente': c.id_cliente.razon_social if c.id_cliente else '',
            'fecha_fin': c.fecha_fin,
            'maquinas': maquinas_por_contrato[c.id_contrato],
        }
        for c in contratos
        if maquinas_por_contrato.get(c.id_contrato)
    ]
    return Response(data, status=status.HTTP_200_OK)


class MaquinariaViewSet(BaseSoftDeleteViewSet):
    queryset = Maquinaria.objects.all().order_by('id_maquina')
    serializer_class = MaquinariaSerializer


class OperadorViewSet(BaseSoftDeleteViewSet):
    queryset = Operador.objects.select_related('usuario').order_by('-id_operador')
    serializer_class = OperadorSerializer

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({'mensaje': 'Operador desactivado correctamente.'}, status=status.HTTP_200_OK)


class MantenimientoViewSet(BaseSoftDeleteViewSet):
    queryset = Mantenimiento.objects.all().order_by('-fecha_mantencion')
    serializer_class = MantenimientoSerializer

    def perform_create(self, serializer):
        mantenimiento = serializer.save()
        maquina = mantenimiento.id_maquina
        maquina.estado = 'OPERATIVA'
        maquina.save()


class ReportViewSet(BaseSoftDeleteViewSet):
    queryset = Report.objects.select_related(
        'id_contrato', 'id_contrato__id_cliente', 'id_operador', 'id_operador__usuario', 'id_maquina'
    ).order_by('-id_report')
    serializer_class = ReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        id_operador = self.request.query_params.get('id_operador')
        if id_operador and id_operador.isdigit():
            qs = qs.filter(id_operador_id=int(id_operador))
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        horometro_inicial = serializer.validated_data.get('horometro_inicial', 0.0)
        horometro_final = serializer.validated_data.get('horometro_final', 0.0)

        horas_calculadas = max(0.0, round(horometro_final - horometro_inicial, 1))
        reporte = serializer.save(horas_trabajadas=horas_calculadas)

        maquina = reporte.id_maquina
        if horometro_final > maquina.horometro_actual:
            maquina.horometro_actual = horometro_final

        ultima = Mantenimiento.objects.filter(
            id_maquina=maquina, activo=True
        ).aggregate(m=Max('horometro_mantencion'))['m'] or 0
        pauta = (horometro_final // 500) * 500
        if pauta > 0 and ultima < pauta - 50:
            maquina.estado = 'REQUIERE MANTENCIÓN'

        maquina.save()


class GastoViewSet(BaseSoftDeleteViewSet):
    queryset = Gasto.objects.select_related('id_maquina', 'id_contrato').order_by('-fecha')
    serializer_class = GastoSerializer


class ClienteViewSet(BaseSoftDeleteViewSet):
    queryset = Cliente.objects.all().order_by('razon_social')
    serializer_class = ClienteSerializer


class ContratoViewSet(BaseSoftDeleteViewSet):
    queryset = Contrato.objects.all().order_by('-id_contrato')
    serializer_class = ContratoSerializer


class HESViewSet(BaseSoftDeleteViewSet):
    queryset = HES.objects.all().order_by('-id_hes')
    serializer_class = HESSerializer


class FacturaViewSet(BaseSoftDeleteViewSet):
    queryset = Factura.objects.all().order_by('-folio')
    serializer_class = FacturaSerializer


class DocMaquinariaViewSet(BaseSoftDeleteViewSet):
    queryset = Doc_Maquinaria.objects.all().order_by('fecha_vencimiento')
    serializer_class = DocMaquinariaSerializer


class DocEmpresaViewSet(BaseSoftDeleteViewSet):
    queryset = Doc_empresa.objects.all().order_by('-fecha_emision')
    serializer_class = DocEmpresaSerializer


class ContratoMaquinariaViewSet(viewsets.ModelViewSet):
    queryset = ContratoMaquinaria.objects.all()
    serializer_class = ContratoMaquinariaSerializer


def login_evaluacion(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('panel_maquinarias')
    else:
        form = AuthenticationForm()
    return render(request, 'panel/login.html', {'form': form})


@login_required(login_url='login_evaluacion')
def logout_evaluacion(request):
    logout(request)
    return redirect('login_evaluacion')


def registro_evaluacion(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('panel_maquinarias')
    else:
        form = UserCreationForm()
    return render(request, 'panel/registro.html', {'form': form})


# Vista basada en clases (CBV) protegida con LoginRequiredMixin
class MaquinariaListView(LoginRequiredMixin, ListView):
    model = Maquinaria
    template_name = 'panel/maquinaria_list.html'
    context_object_name = 'maquinarias'
    login_url = 'login_evaluacion'  # Redirige al login si no se ha iniciado sesión

    def get_queryset(self):
        return Maquinaria.objects.filter(activo=True)

@api_view(['POST'])
def generar_url_presignada(request):
    """
    Genera una URL presignada de S3 para que el cliente suba el archivo directamente.
    """
    nombre_archivo = request.data.get('nombre_archivo')
    tipo_archivo = request.data.get('tipo_archivo', 'application/octet-stream')

    if not nombre_archivo:
        return Response({'error': 'Se requiere el nombre del archivo.'}, status=status.HTTP_400_BAD_REQUEST)

    # Limpiar y hacer único el nombre del archivo para evitar colisiones
    extension = nombre_archivo.split('.')[-1]
    nombre_unico = f"uploads/{uuid.uuid4()}.{extension}"

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    try:
        # Generar la URL con validez de 300 segundos (5 minutos)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': nombre_unico,
                'ContentType': tipo_archivo
            },
            ExpiresIn=300
        )
        
        # URL final pública o interna con la que se accederá al archivo después de subirlo
        url_archivo_final = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{nombre_unico}"

        return Response({
            'upload_url': presigned_url,
            'file_url': url_archivo_final
        }, status=status.HTTP_200_OK)

    except NoCredentialsError:
        return Response({'error': 'Credenciales de AWS no configuradas correctamente.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)