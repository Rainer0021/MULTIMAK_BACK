import re
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import transaction
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


def normalizar_rut(texto):
    """Deja solo dígitos y K en mayúscula (sin puntos ni guion)."""
    return re.sub(r'[^0-9kK]', '', str(texto or '')).upper()


def formatear_rut(texto):
    """12345678K -> 12.345.678-K"""
    limpio = normalizar_rut(texto)
    if len(limpio) < 2:
        return limpio
    cuerpo, dv = limpio[:-1], limpio[-1]
    return f"{int(cuerpo):,}".replace(',', '.') + f"-{dv}"


def rut_valido(texto):
    limpio = normalizar_rut(texto)
    if len(limpio) < 8 or not limpio[:-1].isdigit():
        return False
    suma, mult = 0, 2
    for ch in reversed(limpio[:-1]):
        suma += int(ch) * mult
        mult = mult + 1 if mult < 7 else 2
    esperado = 11 - (suma % 11)
    dv = '0' if esperado == 11 else 'K' if esperado == 10 else str(esperado)
    return limpio[-1] == dv


ESTADOS_MAQUINA = {
    'DISPONIBLE': 'OPERATIVA',
    'OPERATIVA': 'OPERATIVA',
    'EN FAENA': 'EN FAENA',
    'EN TALLER': 'EN TALLER',
    'REQUIERE MANTENCIÓN': 'REQUIERE MANTENCIÓN',
    'REQUIERE MANTENCION': 'REQUIERE MANTENCIÓN',
}


def normalizar_estado_maquina(valor):
    """Unifica los estados (antes el front guardaba 'En Taller' y el back 'EN TALLER')."""
    clave = str(valor or '').strip().upper()
    return ESTADOS_MAQUINA.get(clave, clave or 'OPERATIVA')


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
        hes = attrs.get('id_hes', getattr(self.instance, 'id_hes', None))
        if not hes:
            raise serializers.ValidationError({"id_hes": "Debe vincular una HES aprobada."})

        neto = attrs.get('monto_neto', getattr(self.instance, 'monto_neto', None))
        iva = attrs.get('iva', getattr(self.instance, 'iva', None))
        total = attrs.get('monto_total', getattr(self.instance, 'monto_total', None))
        if None not in (neto, iva, total):
            if neto <= 0:
                raise serializers.ValidationError({"monto_neto": "El monto neto debe ser mayor a 0."})
            if neto + iva != total:
                raise serializers.ValidationError({"monto_total": "El total debe ser igual al neto más el IVA."})
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

    def validate_estado(self, value):
        return normalizar_estado_maquina(value)

    def validate_horometro_actual(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('El horómetro no puede ser negativo.')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['estado'] = normalizar_estado_maquina(data.get('estado'))
        return data

class OperadorSerializer(serializers.ModelSerializer):
    # 'id_usuario' se mantiene como campo de solo lectura para no romper el front.
    id_usuario = serializers.PrimaryKeyRelatedField(source='usuario', read_only=True)
    nombre = serializers.CharField(source='usuario.nombre', read_only=True)
    apellido = serializers.CharField(source='usuario.apellido', read_only=True)
    rut = serializers.CharField(source='usuario.rut', read_only=True)
    licencia_url = serializers.SerializerMethodField()

    class Meta:
        model = Operador
        fields = [
            'id_operador', 'usuario', 'id_usuario', 'TipoLicencia',
            'fecha_vencimiento_licencia', 'archivo_licencia', 'licencia_url',
            'nombre', 'apellido', 'rut',
        ]
        extra_kwargs = {
            'usuario': {'required': False},
            'archivo_licencia': {'write_only': True, 'required': False},
        }

    def get_licencia_url(self, obj):
        return obj.archivo_licencia.url if obj.archivo_licencia else ''

    # --- datos de la cuenta de acceso (llegan como nombre / apellido / rut / password) ---
    def _datos(self):
        d = self.initial_data
        return {
            'nombre': str(d.get('nombre') or '').strip(),
            'apellido': str(d.get('apellido') or '').strip(),
            'rut': str(d.get('rut') or '').strip(),
            'password': str(d.get('password') or '').strip(),
        }

    @staticmethod
    def _usuario_por_rut(rut, excluir_pk=None):
        buscado = normalizar_rut(rut)
        for u in Usuarios.objects.select_related('id_rol').all():
            if u.pk != excluir_pk and normalizar_rut(u.rut) == buscado:
                return u
        return None

    def validate_fecha_vencimiento_licencia(self, value):
        if value is None:
            return value
        anterior = getattr(self.instance, 'fecha_vencimiento_licencia', None)
        if value < hoy_chile() and value != anterior:
            raise serializers.ValidationError('La licencia debe vencer a partir de hoy.')
        return value

    def validate(self, attrs):
        datos = self._datos()
        creando = self.instance is None
        errores = {}

        if creando or 'rut' in self.initial_data:
            if not datos['rut']:
                errores['rut'] = 'Ingrese el RUT del operador.'
            elif not rut_valido(datos['rut']):
                errores['rut'] = 'RUT inválido (verifique los dígitos).'
            else:
                excluir = self.instance.usuario_id if self.instance else None
                existente = self._usuario_por_rut(datos['rut'], excluir_pk=excluir)
                if existente:
                    op = Operador.objects.filter(usuario=existente).first()
                    if op and op.activo and existente.activo:
                        errores['rut'] = 'Ya existe un operador activo con este RUT.'
                    elif not op and 'operador' not in str(existente.id_rol.rol).lower():
                        errores['rut'] = f'Este RUT ya pertenece a un usuario con rol {existente.id_rol.rol}.'

        if creando:
            if not datos['nombre']:
                errores['nombre'] = 'Ingrese el nombre del operador.'
            if not datos['apellido']:
                errores['apellido'] = 'Ingrese el apellido del operador.'
            if len(datos['password']) < 6:
                errores['password'] = 'La contraseña debe tener al menos 6 caracteres.'
        elif datos['password'] and len(datos['password']) < 6:
            errores['password'] = 'La contraseña debe tener al menos 6 caracteres.'

        if errores:
            raise serializers.ValidationError(errores)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        datos = self._datos()
        validated_data.pop('usuario', None)
        rol_op, _ = Rol.objects.get_or_create(rol='Operador')

        usuario = self._usuario_por_rut(datos['rut'])
        if usuario is None:
            usuario = Usuarios(id_rol=rol_op, rut=formatear_rut(datos['rut']))
        usuario.nombre = datos['nombre']
        usuario.apellido = datos['apellido']
        usuario.activo = True
        usuario.set_password(datos['password'])
        usuario.save()
        
        validated_data['url_licencia'] = ''

        # Si el RUT pertenecía a un operador dado de baja, se reactiva en vez de duplicarlo.
        operador = Operador.objects.filter(usuario=usuario).first()
        if operador:
            for campo, valor in validated_data.items():
                setattr(operador, campo, valor)
            operador.activo = True
            operador.save()
            return operador

        validated_data['usuario'] = usuario
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        datos = self._datos()
        validated_data.pop('usuario', None)
        usuario = instance.usuario
        if usuario:
            if datos['nombre']:
                usuario.nombre = datos['nombre']
            if datos['apellido']:
                usuario.apellido = datos['apellido']
            if datos['rut']:
                usuario.rut = formatear_rut(datos['rut'])
            if datos['password']:
                usuario.set_password(datos['password'])
            usuario.save()
        return super().update(instance, validated_data)

class MantenimientoSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)
    class Meta:
        model = Mantenimiento
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)
    contrato_nombre = serializers.SerializerMethodField()
    cliente_nombre = serializers.SerializerMethodField()
    operador_nombre = serializers.SerializerMethodField()
    tarifa_hora = serializers.SerializerMethodField()
    ingreso_estimado = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = '__all__'
        # Las horas siempre se calculan en el servidor a partir del horómetro.
        read_only_fields = ('horas_trabajadas',)

    # --- datos derivados para las tablas (el front ya no inventa tarifas) ---
    def _tarifa(self, obj):
        if not obj.id_contrato_id:
            return None
        mapa = getattr(self, '_mapa_tarifas', None)
        if mapa is None:
            mapa = {
                (r.id_contrato_id, r.id_maquina_id): r.tarifa_hora
                for r in ContratoMaquinaria.objects.all()
            }
            self._mapa_tarifas = mapa
        return mapa.get((obj.id_contrato_id, obj.id_maquina_id))

    def get_contrato_nombre(self, obj):
        c = obj.id_contrato
        return (c.nombre_contrato or f'Contrato #{c.pk}') if c else None

    def get_cliente_nombre(self, obj):
        c = obj.id_contrato
        return c.id_cliente.razon_social if c and c.id_cliente else None

    def get_operador_nombre(self, obj):
        return str(obj.id_operador) if obj.id_operador_id else None

    def get_tarifa_hora(self, obj):
        return self._tarifa(obj)

    def get_ingreso_estimado(self, obj):
        tarifa = self._tarifa(obj)
        return round((obj.horas_trabajadas or 0) * tarifa) if tarifa else 0

    def validate_combustible_litros(self, value):
        if value is None:
            return 0.0
        if value < 0:
            raise serializers.ValidationError('Los litros de combustible no pueden ser negativos.')
        if value > 2000:
            raise serializers.ValidationError('Los litros de combustible parecen excesivos. Revise el valor.')
        return value

    def validate_fecha(self, value):
        if value > hoy_chile():
            raise serializers.ValidationError('La fecha del parte no puede ser posterior a hoy.')
        return value

    def validate(self, attrs):
        inst = self.instance
        ini = attrs.get('horometro_inicial', getattr(inst, 'horometro_inicial', 0.0))
        fin = attrs.get('horometro_final', getattr(inst, 'horometro_final', 0.0))
        firmado = attrs.get('firmado', getattr(inst, 'firmado', False))
        contrato = attrs.get('id_contrato', getattr(inst, 'id_contrato', None))
        maquina = attrs.get('id_maquina', getattr(inst, 'id_maquina', None))
        fecha = attrs.get('fecha', getattr(inst, 'fecha', None))

        # El parte diario siempre corresponde a un contrato y a una máquina de ese contrato.
        if inst is None and contrato is None:
            raise serializers.ValidationError({'id_contrato': 'Debe indicar el contrato al que corresponde el parte diario.'})

        if contrato is not None and (inst is None or 'id_contrato' in attrs or 'id_maquina' in attrs or 'fecha' in attrs):
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
        if inst is None and maquina is not None and abs(ini - maquina.horometro_actual) > 0.05:
            raise serializers.ValidationError({
                'horometro_inicial': (
                    f'El horómetro inicial debe ser {maquina.horometro_actual:g} h (último registro de la máquina). '
                    'Recargue la página e intente nuevamente.'
                )
            })

        if fin <= ini:
            raise serializers.ValidationError({"horometro_final": "El horómetro final debe ser estrictamente mayor al inicial."})
        if (fin - ini) > 24:
            raise serializers.ValidationError({"horometro_final": "La jornada no puede superar las 24 horas continuas."})
        if not firmado:
            raise serializers.ValidationError({"firmado": "Es obligatorio contar con el V°B° / firma del supervisor en terreno."})
        return attrs

class GastoSerializer(serializers.ModelSerializer):
    maquina_patente = serializers.CharField(source='id_maquina.patente', read_only=True)
    contrato_nombre = serializers.SerializerMethodField()
    comprobante_url = serializers.SerializerMethodField()

    class Meta:
        model = Gasto
        fields = '__all__'
        extra_kwargs = {
            'id_usuario': {'required': False},
            'numero_comprobante': {'required': False},
            'url_comprobante': {'required': False},
            'archivo_comprobante': {'write_only': True, 'required': False},
        }

    def get_contrato_nombre(self, obj):
        c = obj.id_contrato
        return (c.nombre_contrato or f'Contrato #{c.pk}') if c else None

    def get_comprobante_url(self, obj):
        if obj.archivo_comprobante:
            return obj.archivo_comprobante.url
        return obj.url_comprobante or ''

    def validate_monto(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('El monto debe ser mayor a 0.')
        return value

    def validate_fecha(self, value):
        if value > hoy_chile():
            raise serializers.ValidationError('La fecha del gasto no puede ser posterior a hoy.')
        return value

    def create(self, validated_data):
        if not validated_data.get('id_usuario'):
            # Respaldo: el primer usuario administrador activo (antes tomaba "el primero" sin importar el rol).
            admin_user = (
                Usuarios.objects.filter(activo=True, id_rol__rol__icontains='admin').first()
                or Usuarios.objects.filter(activo=True).first()
            )
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