from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import (
    Maquinaria, Operador, Report, Usuarios, Gasto,
    Cliente, Contrato, HES, Factura, Doc_Maquinaria, Doc_empresa
)
from .serializers import (
    MaquinariaSerializer, OperadorSerializer, ReportSerializer, GastoSerializer,
    ClienteSerializer, ContratoSerializer, HESSerializer, FacturaSerializer,
    DocMaquinariaSerializer, DocEmpresaSerializer
)

@api_view(['POST'])
def login_unificado(request):
    rut_recibido = request.data.get('rut', '').strip().replace('.', '').replace('-', '').upper()
    contraseña_recibida = request.data.get('contraseña', '').strip()

    try:
        # 1. Búsqueda flexible de RUT en la base de datos
        usuario = None
        for u in Usuarios.objects.all():
            rut_bd = u.rut.replace('.', '').replace('-', '').upper().strip()
            if rut_bd == rut_recibido:
                usuario = u
                break

        if not usuario:
            return Response({'error': 'RUT no registrado en el sistema'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Validación compatible con texto plano y con hash seguro PBKDF2 / SHA256
        clave_bd = usuario.contraseña.strip()
        es_valida = (clave_bd == contraseña_recibida) or check_password(contraseña_recibida, clave_bd)

        if not es_valida:
            return Response({'error': 'Contraseña incorrecta'}, status=status.HTTP_401_UNAUTHORIZED)

        # 3. Retornar rol y datos del usuario
        rol_str = usuario.id_rol.rol if usuario.id_rol else ''
        id_operador = None
        tipo_licencia = None

        if 'operador' in rol_str.lower():
            op = Operador.objects.filter(id_usuario=usuario).first()
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

class MaquinariaViewSet(viewsets.ModelViewSet):
    queryset = Maquinaria.objects.all().order_by('id_maquina')
    serializer_class = MaquinariaSerializer


class OperadorViewSet(viewsets.ModelViewSet):
    queryset = Operador.objects.all().order_by('-id_operador')
    serializer_class = OperadorSerializer


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-id_report')
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        reporte = serializer.save()
        # Actualización de horómetro y cambio automático de estado a mantención (HU02 / RS003)
        maquina = reporte.id_maquina
        maquina.horometro_actual = reporte.horometro_final
        
        ciclo = reporte.horometro_final % 1000
        if ciclo >= 500 and ciclo < 550 or ciclo >= 990 or ciclo < 15:
            maquina.estado = 'REQUIERE MANTENCIÓN'
        
        maquina.save()


class GastoViewSet(viewsets.ModelViewSet):
    queryset = Gasto.objects.all().order_by('-fecha')
    serializer_class = GastoSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by('razon_social')
    serializer_class = ClienteSerializer


class ContratoViewSet(viewsets.ModelViewSet):
    queryset = Contrato.objects.all().order_by('-id_contrato')
    serializer_class = ContratoSerializer


class HESViewSet(viewsets.ModelViewSet):
    queryset = HES.objects.all().order_by('-id_hes')
    serializer_class = HESSerializer


class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all().order_by('-folio')
    serializer_class = FacturaSerializer


class DocMaquinariaViewSet(viewsets.ModelViewSet):
    queryset = Doc_Maquinaria.objects.all().order_by('fecha_vencimiento')
    serializer_class = DocMaquinariaSerializer


class DocEmpresaViewSet(viewsets.ModelViewSet):
    queryset = Doc_empresa.objects.all().order_by('-fecha_emision')
    serializer_class = DocEmpresaSerializer