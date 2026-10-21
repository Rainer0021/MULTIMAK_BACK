from rest_framework import serializers
from .models import (
    Rol, Usuarios, Operador, Cliente, Maquinaria,
    Contrato, HES, Factura, Mantenimiento, Report,
    Gasto, Doc_Maquinaria, Doc_empresa
)

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

class UsuariosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuarios
        fields = '__all__'

class OperadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operador
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        fields = '__all__'

class ContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrato
        fields = '__all__'

class HESSerializer(serializers.ModelSerializer):
    class Meta:
        model = HES
        fields = '__all__'

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class MantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mantenimiento
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class GastoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gasto
        fields = '__all__'

class DocMaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_Maquinaria
        fields = '__all__'

class DocEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_empresa
        fields = '__all__'