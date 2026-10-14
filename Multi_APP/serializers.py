from rest_framework import serializers
from .models import Cliente, Operador, Maquinaria, Contrato, Report, Gasto

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class OperadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operador
        fields = '__all__'

class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        fields = '__all__'

class ContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrato
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    # Trae los nombres directamente cruzando las relaciones foráneas
    maquinaria_patente = serializers.CharField(source='contrato.maquinaria.patente', read_only=True)
    maquinaria_tipo = serializers.CharField(source='contrato.maquinaria.tipo', read_only=True)
    operador_nombre = serializers.CharField(source='operador.nombre', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id',
            'contrato',
            'operador',
            'maquinaria_patente',
            'maquinaria_tipo',
            'operador_nombre',
            'fecha',
            'hora_entrada',
            'hora_salida',
            'horometro_inicio',
            'horometro_final',
            'horas_trabajadas',
            'combustible_litros',
            'firmado',
        ]

class GastoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gasto
        fields = '__all__'