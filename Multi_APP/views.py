from rest_framework import viewsets
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Cliente, Operador, Maquinaria, Contrato, Report, Gasto
from .serializers import (
    ClienteSerializer,
    OperadorSerializer,
    MaquinariaSerializer,
    ContratoSerializer,
    ReportSerializer,
    GastoSerializer,
)

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

class OperadorViewSet(viewsets.ModelViewSet):
    queryset = Operador.objects.all()
    serializer_class = OperadorSerializer

class MaquinariaViewSet(viewsets.ModelViewSet):
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer

class ContratoViewSet(viewsets.ModelViewSet):
    queryset = Contrato.objects.all()
    serializer_class = ContratoSerializer

from rest_framework import viewsets
from .models import Report, Maquinaria
from .serializers import ReportSerializer

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-fecha', '-id')
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        # Guardamos el reporte ingresado por el operador
        reporte = serializer.save()

        # HU02 / RS003: Actualización automática de horómetro y estado de la máquina
        try:
            # Obtenemos la maquinaria vinculada (vía contrato o directa)
            maquina = None
            if hasattr(reporte, 'contrato') and reporte.contrato:
                maquina = reporte.contrato.maquinaria
            elif hasattr(reporte, 'maquinaria') and reporte.maquinaria:
                maquina = reporte.maquinaria

            if maquina:
                # El horómetro acumulado se actualiza al horómetro final del turno
                nuevo_horometro = float(reporte.horometro_final)
                maquina.horometro_acumulado = nuevo_horometro

                # Regla de negocio HU02 / RS003:
                # Si alcanza o supera el ciclo de 500 hrs o 1000 hrs, pasa automáticamente a "Requiere Mantención"
                ciclo_500 = nuevo_horometro % 500
                if ciclo_500 >= 499 or nuevo_horometro >= 500:
                    maquina.estado = "Requiere Mantención"
                else:
                    maquina.estado = "Operativa"

                maquina.save()
        except Exception as e:
            print(f"Error al actualizar horómetro automático: {e}")

class GastoViewSet(viewsets.ModelViewSet):
    queryset = Gasto.objects.all()
    serializer_class = GastoSerializer

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Debe ingresar usuario y contraseña'},
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario = authenticate(username=username, password=password)

        if usuario is not None:
            # Determinamos el rol según los grupos o si es superusuario
            if usuario.is_superuser or usuario.groups.filter(name='Administrador').exists():
                rol = 'admin'
            elif usuario.groups.filter(name='Operador').exists():
                rol = 'operador'
            else:
                rol = 'operador'  # Rol por defecto

            return Response({
                'mensaje': 'Inicio de sesión exitoso',
                'username': usuario.username,
                'nombre_completo': f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username,
                'rol': rol
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )