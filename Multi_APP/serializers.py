import re
from datetime import datetime
from zoneinfo import ZoneInfo

from rest_framework import serializers
from .models import (
    Rol, Usuarios, Operador, Cliente, Maquinaria,
    Contrato, ContratoMaquinaria, HES, Factura, Mantenimiento, 
    Report, Gasto, Doc_Maquinaria, Doc_empresa
)

ESTADOS_CONTRATO_VIGENTES = ('ACTIVO', 'PRORROGADO')


def hoy_chile():
    """Fecha de hoy en hora de Chile (Magallanes), no en UTC."""
    return datetime.now(ZoneInfo('America/Punta_Arenas')).date()


def _fmt(fecha):
    return fecha.strftime('%d-%m-%Y') if fecha else 'sin término'


def telefono_cl_valido(texto):
    """Móvil: 9 dígitos que empiezan con 9. Fijo: 9 dígitos que empiezan con 2 a 7. Acepta +56."""
    d = re.sub(r'\D', '', texto or '')
    if len(d) == 11 and d.startswith('56'):
        d = d[2:]
    if len(d) != 9 or len(set(d)) == 1:
        return False
    return bool(re.fullmatch(r'9\d{8}', d) or re.fullmatch(r'[2-7]\d{8}', d))


def buscar_choque_maquina(id_maquina, inicio, fin, excluir_contrato=None):
    """Devuelve el contrato vigente que ya usa esa máquina en el período indicado (o None)."""
    relaciones = ContratoMaquinaria.objects.filter(
        id_maquina=id_maquina,
        id_contrato__activo=True,
        id_contrato__estado_contrato__in=ESTADOS_CONTRATO_VIGENTES,
    ).select_related('id_contrato')
    if excluir_contrato is not None:
        relaciones = relaciones.exclude(id_contrato=excluir_contrato)
    for rel in relaciones:
        c = rel.id_contrato
        empieza_antes = c.fecha_inicio is None or fin is None or c.fecha_inicio <= fin
        termina_despues = c.fecha_fin is None or inicio is None or inicio <= c.fecha_fin
        if empieza_antes and termina_despues:
            return c
    return None


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

    def validate_contacto(self, value):
        m = re.search(r'Tel:\s*([^|]+)', value or '')
        telefono = m.group(1).strip() if m else (value or '')
        if not telefono_cl_valido(telefono):
            raise serializers.ValidationError('Ingrese un teléfono chileno válido. Ej: +56 9 8765 4321.')
        return value

class ContratoMaquinariaSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)
    maquina_tipo = serializers.CharField(source='id_maquina.tipo', read_only=True)

    class Meta:
        model = ContratoMaquinaria
        fields = '__all__'

    def validate(self, attrs):
        contrato = attrs.get('id_contrato', getattr(self.instance, 'id_contrato', None))
        maquina = attrs.get('id_maquina', getattr(self.instance, 'id_maquina', None))
        tarifa = attrs.get('tarifa_hora', getattr(self.instance, 'tarifa_hora', None))

        if tarifa is not None and tarifa <= 0:
            raise serializers.ValidationError({'tarifa_hora': 'La tarifa por hora debe ser mayor a 0.'})

        if contrato and maquina:
            repetida = ContratoMaquinaria.objects.filter(id_contrato=contrato, id_maquina=maquina)
            if self.instance:
                repetida = repetida.exclude(pk=self.instance.pk)
            if repetida.exists():
                raise serializers.ValidationError(
                    {'id_maquina': f'La máquina {maquina.patente} ya está asignada a este contrato.'}
                )

            choque = buscar_choque_maquina(
                maquina.pk, contrato.fecha_inicio, contrato.fecha_fin, excluir_contrato=contrato.pk
            )
            if choque:
                nombre = choque.nombre_contrato or f'#{choque.pk}'
                raise serializers.ValidationError({
                    'id_maquina': (
                        f'La máquina {maquina.patente} ya está asignada al contrato «{nombre}» '
                        f'entre el {_fmt(choque.fecha_inicio)} y el {_fmt(choque.fecha_fin)}.'
                    )
                })
        return attrs

class ContratoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='id_cliente.razon_social', read_only=True)
    maquinas_contrato = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = '__all__'

    def get_maquinas_contrato(self, obj):
        relaciones = ContratoMaquinaria.objects.filter(id_contrato=obj)
        return ContratoMaquinariaSerializer(relaciones, many=True).data

    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))

        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({'fecha_fin': 'La fecha de término no puede ser anterior a la de inicio.'})

        if self.instance is None and inicio and inicio < hoy_chile():
            raise serializers.ValidationError({'fecha_inicio': 'La fecha de inicio no puede ser anterior a hoy.'})

        # Al prorrogar o cambiar fechas: ninguna máquina del contrato puede chocar con otro contrato.
        if self.instance is not None and ('fecha_inicio' in attrs or 'fecha_fin' in attrs):
            estado = attrs.get('estado_contrato', self.instance.estado_contrato)
            if estado in ESTADOS_CONTRATO_VIGENTES:
                relaciones = ContratoMaquinaria.objects.filter(id_contrato=self.instance).select_related('id_maquina')
                for rel in relaciones:
                    choque = buscar_choque_maquina(
                        rel.id_maquina_id, inicio, fin, excluir_contrato=self.instance.pk
                    )
                    if choque:
                        nombre = choque.nombre_contrato or f'#{choque.pk}'
                        raise serializers.ValidationError({
                            'fecha_fin': (
                                f'No se puede cambiar el período: la máquina {rel.id_maquina.patente} '
                                f'ya está asignada al contrato «{nombre}» en esas fechas.'
                            )
                        })
        return attrs

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
    # 'id_usuario' se mantiene como campo de solo lectura para no romper el front.
    id_usuario = serializers.PrimaryKeyRelatedField(source='usuario', read_only=True)
    nombre = serializers.CharField(source='usuario.nombre', read_only=True)
    apellido = serializers.CharField(source='usuario.apellido', read_only=True)
    rut = serializers.CharField(source='usuario.rut', read_only=True)

    nombre_input = serializers.CharField(write_only=True, required=False)
    apellido_input = serializers.CharField(write_only=True, required=False)
    rut_input = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Operador
        fields = [
            'id_operador', 'usuario', 'id_usuario', 'TipoLicencia',
            'fecha_vencimiento_licencia', 'nombre', 'apellido', 'rut',
            'nombre_input', 'apellido_input', 'rut_input'
        ]
        extra_kwargs = {'usuario': {'required': False}}

    def validate_fecha_vencimiento_licencia(self, value):
        if value is None:
            return value
        anterior = getattr(self.instance, 'fecha_vencimiento_licencia', None)
        if value < hoy_chile() and value != anterior:
            raise serializers.ValidationError('La licencia debe vencer a partir de hoy.')
        return value

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
        validated_data['usuario'] = usuario
        return super().create(validated_data)

class MantenimientoSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)
    class Meta:
        model = Mantenimiento
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)

    class Meta:
        model = Report
        fields = '__all__'

    def validate(self, attrs):
        ini = attrs.get('horometro_inicial', 0.0)
        fin = attrs.get('horometro_final', 0.0)
        firmado = attrs.get('firmado', False)
        contrato = attrs.get('id_contrato')
        maquina = attrs.get('id_maquina')
        fecha = attrs.get('fecha')

        # El parte diario siempre corresponde a un contrato y a una máquina de ese contrato.
        if self.instance is None and contrato is None:
            raise serializers.ValidationError({'id_contrato': 'Debe indicar el contrato al que corresponde el parte diario.'})

        if contrato is not None:
            nombre = contrato.nombre_contrato or f'#{contrato.pk}'
            if maquina is not None and not ContratoMaquinaria.objects.filter(id_contrato=contrato, id_maquina=maquina).exists():
                raise serializers.ValidationError({
                    'id_maquina': f'La máquina {maquina.patente} no está asignada al contrato «{nombre}».'
                })
            if fecha is not None and (
                contrato.estado_contrato not in ESTADOS_CONTRATO_VIGENTES
                or (contrato.fecha_inicio and fecha < contrato.fecha_inicio)
                or (contrato.fecha_fin and fecha > contrato.fecha_fin)
            ):
                raise serializers.ValidationError({'id_contrato': f'El contrato «{nombre}» no está vigente en la fecha del parte.'})

        # Continuidad del horómetro: el inicial debe ser el último registrado de la máquina.
        if self.instance is None and maquina is not None and abs(ini - maquina.horometro_actual) > 0.05:
            raise serializers.ValidationError({
                'horometro_inicial': (
                    f'El horómetro inicial debe ser {maquina.horometro_actual:g} h (último registro de la máquina). '
                    'Recargue la página e intente nuevamente.'
                )
            })

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

    def validate_fecha(self, value):
        if value > hoy_chile():
            raise serializers.ValidationError('La fecha del gasto no puede ser posterior a hoy.')
        return value

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

    def validate_fecha_vencimiento(self, value):
        if self.instance is None and value < hoy_chile():
            # Se acepta si es la misma fecha de un documento ya guardado de esa máquina
            # (el formulario de edición vuelve a enviarla).
            try:
                id_maq = int(self.initial_data.get('id_maquina'))
            except (TypeError, ValueError):
                id_maq = None
            ya_guardada = id_maq is not None and Doc_Maquinaria.objects.filter(
                id_maquina=id_maq, fecha_vencimiento=value, activo=True
            ).exists()
            if not ya_guardada:
                raise serializers.ValidationError('La fecha de vencimiento no puede ser anterior a hoy.')
        return value

class DocEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc_empresa
        fields = '__all__'