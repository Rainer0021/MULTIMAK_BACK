from rest_framework import serializers
from .models import Maquinaria, Operador, Report, Usuarios

class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        fields = ['id_maquina', 'patente', 'modelo', 'tipo', 'marca', 'horometro_actual']

class OperadorSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Operador
        fields = ['id_operador', 'id_usuario', 'TipoLicencia', 'nombre_completo']

    def get_nombre_completo(self, obj):
        return f"{obj.id_usuario.nombre} {obj.id_usuario.apellido}"

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'