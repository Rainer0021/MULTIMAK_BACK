from rest_framework import serializers
from .models import (
    Rol, Usuarios, Operador, Cliente, Maquinaria,
    Contrato, HES, Factura, Mantenimiento, Report,
    Gasto, Doc_Maquinaria, Doc_empresa
)

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class ContratoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='id_cliente.razon_social', read_only=True)
    class Meta:
        model = Contrato
        fields = '__all__'

class HESSerializer(serializers.ModelSerializer):
    contrato_detalle = serializers.CharField(source='id_contrato.__str__', read_only=True)
    class Meta:
        model = HES
        fields = '__all__'

class FacturaSerializer(serializers.ModelSerializer):
    hes_numero = serializers.CharField(source='id_hes.numero_hes', read_only=True)
    
    class Meta:
        model = Factura
        fields = '__all__'

    def validate(self, attrs):
        hes = attrs.get('id_hes')
        if not hes:
            raise serializers.ValidationError({"id_hes": "Debe vincular una HES aprobada."})
        if hes.estado.upper() != 'APROBADA':
            raise serializers.ValidationError({
                "id_hes": f"Facturación bloqueada: La HES #{hes.numero_hes} está en estado '{hes.estado}'. Requiere estar 'APROBADA'."
            })
        if hasattr(hes, 'factura') and (self.instance is None or self.instance.id_hes != hes):
            raise serializers.ValidationError({"id_hes": f"La HES #{hes.numero_hes} ya posee una factura emitida."})
        return attrs

class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        fields = '__all__'

class OperadorSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='id_usuario.nombre', read_only=True)
    apellido = serializers.CharField(source='id_usuario.apellido', read_only=True)
    rut = serializers.CharField(source='id_usuario.rut', read_only=True)

    nombre_input = serializers.CharField(write_only=True, required=False)
    apellido_input = serializers.CharField(write_only=True, required=False)
    rut_input = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Operador
        fields = [
            'id_operador', 'id_usuario', 'TipoLicencia',
            'fecha_vencimiento_licencia', 'nombre', 'apellido', 'rut',
            'nombre_input', 'apellido_input', 'rut_input'
        ]
        extra_kwargs = {'id_usuario': {'required': False}}

    def create(self, validated_data):
        nombre = validated_data.pop('nombre_input', self.initial_data.get('nombre', 'Operador'))
        apellido = validated_data.pop('apellido_input', self.initial_data.get('apellido', ''))
        rut = validated_data.pop('rut_input', self.initial_data.get('rut', ''))

        rol_op, _ = Rol.objects.get_or_create(rol='Operador')
        usuario, _ = Usuarios.objects.get_or_create(
            rut=rut,
            defaults={
                'nombre': nombre,
                'apellido': apellido,
                'id_rol': rol_op,
                'contraseña': 'operador123',
                'estado_login': False
            }
        )
        validated_data['id_usuario'] = usuario
        return super().create(validated_data)

class ReportSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)

    class Meta:
        model = Report
        fields = '__all__'

    def validate(self, attrs):
        ini = attrs.get('horometro_inicial', 0.0)
        fin = attrs.get('horometro_final', 0.0)
        horas = attrs.get('horas_trabajadas', 0)
        firmado = attrs.get('firmado', False)

        if fin <= ini:
            raise serializers.ValidationError({"horometro_final": "El horómetro final debe ser estrictamente mayor al inicial."})
        if (fin - ini) > 24:
            raise serializers.ValidationError({"horas_trabajadas": "La jornada no puede superar las 24 horas continuas."})
        if not firmado:
            raise serializers.ValidationError({"firmado": "Es obligatorio contar con el V°B° / firma del supervisor en terreno."})
        return attrs

class GastoSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)

    class Meta:
        model = Gasto
        fields = '__all__'
        extra_kwargs = {
            'id_usuario': {'required': False},
            'numero_comprobante': {'required': False},
            'url_comprobante': {'required': False}
        }

    def create(self, validated_data):
        if 'id_usuario' not in validated_data or not validated_data['id_usuario']:
            admin_user = Usuarios.objects.first()
            validated_data['id_usuario'] = admin_user
        return super().create(validated_data)

class DocMaquinariaSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)
    class Meta:
        model = Doc_Maquinaria
        fields = '__all__'

class DocEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_empresa
        fields = '__all__'