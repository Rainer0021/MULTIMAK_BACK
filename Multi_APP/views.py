from rest_framework import status, viewsets
from django.contrib.auth.hashers import check_password
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count

from .models import (
    Maquinaria, Operador, Report, Usuarios, Gasto,
    Cliente, Contrato, ContratoMaquinaria, HES, Factura, 
    Doc_Maquinaria, Doc_empresa
)
from .serializers import (
    MaquinariaSerializer, OperadorSerializer, ReportSerializer, GastoSerializer,
    ClienteSerializer, ContratoSerializer, ContratoMaquinariaSerializer,
    HESSerializer, FacturaSerializer, DocMaquinariaSerializer, DocEmpresaSerializer
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
    rut_recibido = request.data.get('rut', '').strip().replace('.', '').replace('-', '').upper()
    contraseña_recibida = request.data.get('contraseña', '').strip()

    try:
        usuario = None
        for u in Usuarios.objects.filter(activo=True):
            rut_bd = u.rut.replace('.', '').replace('-', '').upper().strip()
            if rut_bd == rut_recibido:
                usuario = u
                break

        if not usuario:
            return Response({'error': 'RUT no registrado en el sistema'}, status=status.HTTP_404_NOT_FOUND)

        clave_bd = usuario.contraseña.strip()
        es_valida = (clave_bd == contraseña_recibida) or check_password(contraseña_recibida, clave_bd)

        if not es_valida:
            return Response({'error': 'Contraseña incorrecta'}, status=status.HTTP_401_UNAUTHORIZED)

        rol_str = usuario.id_rol.rol if usuario.id_rol else ''
        id_operador = None
        tipo_licencia = None

        if 'operador' in rol_str.lower():
            op = Operador.objects.filter(id_usuario=usuario, activo=True).first()
            if op:
                id_operador = op.id_operador
                tipo_licencia = op.TipoLicencia

        return Response({
            'mensaje': 'Acceso autorizado',
            'id_usuario': usuario.id_usuario,
            'nombre': f"{usuario.nombre} {usuario.apellido}",
            'rol': rol_str,
            'id_operador': id_operador,
            'tipo_licencia': tipo_licencia
        }, status=status.HTTP_200_OK)

    except Exception as e:
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


class MaquinariaViewSet(BaseSoftDeleteViewSet):
    queryset = Maquinaria.objects.all().order_by('id_maquina')
    serializer_class = MaquinariaSerializer


class OperadorViewSet(BaseSoftDeleteViewSet):
    queryset = Operador.objects.all().order_by('-id_operador')
    serializer_class = OperadorSerializer


class ReportViewSet(BaseSoftDeleteViewSet):
    queryset = Report.objects.all().order_by('-id_report')
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        reporte = serializer.save()
        maquina = reporte.id_maquina
        maquina.horometro_actual = reporte.horometro_final

        ciclo = reporte.horometro_final % 1000
        if (ciclo >= 500 and ciclo < 550) or ciclo >= 990 or ciclo < 15:
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