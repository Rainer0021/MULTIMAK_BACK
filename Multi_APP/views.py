from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.apps import apps
from .models import Maquinaria, Operador, Report, Usuarios
from .serializers import MaquinariaSerializer, OperadorSerializer, ReportSerializer

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        # 1. Guarda el reporte de turno en la base de datos
        reporte = serializer.save()

        # 2. Actualiza automáticamente el horómetro de la maquinaria
        try:
            # Obtiene el ID de la máquina si es ForeignKey o campo numérico
            maquina_id = reporte.id_maquina_id if hasattr(reporte, 'id_maquina_id') else getattr(reporte, 'id_maquina', None)
            
            if hasattr(maquina_id, 'id_maquina'):
                maquina_id = maquina_id.id_maquina

            Maquinaria.objects.filter(id_maquina=maquina_id).update(horometro_actual=reporte.horometro_final)
            print(f">>> Maquinaria #{maquina_id} actualizada con éxito a {reporte.horometro_final} hrs.")
        except Exception as e:
            print(f">>> Error al actualizar horómetro de la maquinaria: {e}")

class MaquinariaViewSet(viewsets.ModelViewSet):
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer

@api_view(['POST'])
def login_operador(request):
    rut = request.data.get('rut')
    contraseña = request.data.get('contraseña')

    try:
        usuario = Usuarios.objects.get(rut=rut, contraseña=contraseña, id_rol__rol__iexact='Operador')
        operador = Operador.objects.get(id_usuario=usuario)
        return Response({
            'mensaje': 'Acceso concedido',
            'id_operador': operador.id_operador,
            'nombre': f"{usuario.nombre} {usuario.apellido}",
            'tipo_licencia': operador.TipoLicencia
        }, status=status.HTTP_200_OK)
    except (Usuarios.DoesNotExist, Operador.DoesNotExist):
        return Response({'error': 'Credenciales invalidas o no es operador'}, status=status.HTTP_401_UNAUTHORIZED)