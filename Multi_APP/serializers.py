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
    # Campos de lectura para que el Frontend muestre nombre, apellido y rut
    nombre = serializers.CharField(source='id_usuario.nombre', read_only=True)
    apellido = serializers.CharField(source='id_usuario.apellido', read_only=True)
    rut = serializers.CharField(source='id_usuario.rut', read_only=True)

    # Campos de escritura para cuando el Frontend envíe el formulario del modal
    nombre_input = serializers.CharField(write_only=True, required=False)
    apellido_input = serializers.CharField(write_only=True, required=False)
    rut_input = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Operador
        fields = [
            'id_operador',
            'id_usuario',
            'TipoLicencia',
            'fecha_vencimiento_licencia',
            'nombre',
            'apellido',
            'rut',
            'nombre_input',
            'apellido_input',
            'rut_input'
        ]
        extra_kwargs = {
            'id_usuario': {'required': False}
        }

    def create(self, validated_data):
        nombre = validated_data.pop('nombre_input', self.initial_data.get('nombre', 'Operador'))
        apellido = validated_data.pop('apellido_input', self.initial_data.get('apellido', ''))
        rut = validated_data.pop('rut_input', self.initial_data.get('rut', '11.111.111-1'))
        
        # Buscar o crear rol de Operador
        rol_op, _ = Rol.objects.get_or_create(rol='Operador')

        # Buscar o crear el usuario asociado
        usuario, _ = Usuarios.objects.get_or_create(
            rut=rut,
            defaults={
                'nombre': nombre,
                'apellido': apellido,
                'id_rol': rol_op,
                'contraseña': 'changeme123',
                'estado_login': False
            }
        )

        validated_data['id_usuario'] = usuario
        return super().create(validated_data)


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
        extra_kwargs = {
            'id_usuario': {'required': False},
            'numero_comprobante': {'required': False, 'allow_blank': True},
            'url_comprobante': {'required': False, 'allow_blank': True}
        }

    def create(self, validated_data):
        # Si no viene un usuario asignado en el gasto, asigna el primer usuario existente
        if 'id_usuario' not in validated_data or not validated_data['id_usuario']:
            primer_usuario = Usuarios.objects.first()
            if not primer_usuario:
                rol_admin, _ = Rol.objects.get_or_create(rol='Administrador')
                primer_usuario = Usuarios.objects.create(
                    rut='1-9', nombre='Admin', apellido='General',
                    id_rol=rol_admin, contraseña='admin'
                )
            validated_data['id_usuario'] = primer_usuario

        if 'numero_comprobante' not in validated_data:
            validated_data['numero_comprobante'] = 'S/N'
        if 'url_archivo' not in validated_data and 'url_comprobante' not in validated_data:
            validated_data['url_comprobante'] = ''

        return super().create(validated_data)


class DocMaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_Maquinaria
        fields = '__all__'


class DocEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_empresa
        fields = '__all__'