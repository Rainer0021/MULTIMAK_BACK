from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from collections import defaultdict
from django.db.models import Sum, Avg, Count, Max, Q
from django.db import transaction
from django.contrib.auth.hashers import make_password, check_password

from .models import (
    Maquinaria, Operador, Report, Usuarios, Gasto,
    Cliente, Contrato, ContratoMaquinaria, HES, Factura, 
    Doc_Maquinaria, Doc_empresa, Mantenimiento
)
from .serializers import (
    MaquinariaSerializer, OperadorSerializer, ReportSerializer, GastoSerializer,
    ClienteSerializer, ContratoSerializer, ContratoMaquinariaSerializer,
    HESSerializer, FacturaSerializer, DocMaquinariaSerializer, DocEmpresaSerializer,
    MantenimientoSerializer, hoy_chile, ESTADOS_CONTRATO_VIGENTES
)

class BaseSoftDeleteViewSet(viewsets.ModelViewSet):
    """
    ViewSet base que filtra los registros activos por defecto
    y ejecuta borrado lógico (activo=False) en lugar de DELETE físico.
    """
    def get_queryset(self):
        return self.queryset.filter(activo=True)

    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        instancia.activo = False
        instancia.save()
        return Response({'mensaje': 'Registro desactivado correctamente.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def login_unificado(request):
    try:
        data = request.data or {}
        
        # 1. Obtener RUT y contraseña manejando múltiples nombres de parámetros
        raw_rut = data.get('rut') or data.get('username') or ''
        raw_password = data.get('contraseña') or data.get('password') or ''

        rut_recibido = str(raw_rut).strip().replace('.', '').replace('-', '').upper()
        contraseña_recibida = str(raw_password).strip()

        if not rut_recibido or not contraseña_recibida:
            return Response({'error': 'Debe ingresar RUT y contraseña'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Buscar usuario comparando RUT limpio
        usuario_encontrado = None
        for u in Usuarios.objects.filter(activo=True):
            if u.rut:
                rut_bd = str(u.rut).strip().replace('.', '').replace('-', '').upper()
                if rut_bd == rut_recibido:
                    usuario_encontrado = u
                    break

        if not usuario_encontrado:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        # 3. Validar contraseña
        clave_bd = str(usuario_encontrado.contraseña).strip()
        es_valida = check_password(contraseña_recibida, clave_bd) or (clave_bd == contraseña_recibida)

        if not es_valida:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        # 4. Obtener datos del rol y operador
        rol_nombre = str(usuario_encontrado.id_rol.rol) if usuario_encontrado.id_rol else ''
        id_operador = None
        tipo_licencia = None

        if 'operador' in rol_nombre.lower():
            try:
                op = Operador.objects.filter(usuario=usuario_encontrado).first()
                if op:
                    id_operador = op.pk
                    tipo_licencia = getattr(op, 'TipoLicencia', None)
            except Exception as op_err:
                print(f"⚠️ Consulta operador: {op_err}")

        # 5. Respuesta exitosa garantizada
        return Response({
            'mensaje': 'Acceso autorizado',
            'id_usuario': usuario_encontrado.pk,
            'rut': usuario_encontrado.rut,
            'nombre': f"{usuario_encontrado.nombre} {usuario_encontrado.apellido}".strip(),
            'rol': rol_nombre,
            'id_operador': id_operador,
            'tipo_licencia': tipo_licencia
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Error en login_unificado: {str(e)}")
        return Response({'error': f'Error en el servidor: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            'estado': m.estado,
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
    queryset = Operador.objects.all().order_by('-id_operador')
    serializer_class = OperadorSerializer

    def destroy(self, request, *args, **kwargs):
        # Usa el delete() del modelo, que también desactiva al usuario del operador.
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
    queryset = Report.objects.all().order_by('-id_report')
    serializer_class = ReportSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        horometro_inicial = serializer.validated_data.get('horometro_inicial', 0.0)
        horometro_final = serializer.validated_data.get('horometro_final', 0.0)
        
        horas_calculadas = max(0, int(horometro_final - horometro_inicial))
        reporte = serializer.save(horas_trabajadas=horas_calculadas)

        maquina = reporte.id_maquina
        if horometro_final > maquina.horometro_actual:
            maquina.horometro_actual = horometro_final

        # Mantención cada 500 h: se marca solo si se cruzó una pauta y no hay
        # una mantención registrada desde entonces (con 50 h de margen).
        ultima = Mantenimiento.objects.filter(
            id_maquina=maquina, activo=True
        ).aggregate(m=Max('horometro_mantencion'))['m'] or 0
        pauta = (horometro_final // 500) * 500
        if pauta > 0 and ultima < pauta - 50:
            maquina.estado = 'REQUIERE MANTENCIÓN'

        maquina.save()


class GastoViewSet(BaseSoftDeleteViewSet):
    queryset = Gasto.objects.all().order_by('-fecha')
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


# Vistas nativas para la evaluación
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


class MaquinariaListView(LoginRequiredMixin, ListView):
    model = Maquinaria
    template_name = 'panel/maquinaria_list.html'
    context_object_name = 'maquinarias'
    login_url = 'login_evaluacion'

    def get_queryset(self):
        return Maquinaria.objects.filter(activo=True)