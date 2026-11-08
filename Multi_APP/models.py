from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    rol = models.CharField(max_length=40)  # 'Operador', 'Administrador', 'Contador'

    class Meta:
        db_table = 'Rol'

    def __str__(self):
        return self.rol


class Usuarios(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.RESTRICT, db_column='id_rol')
    rut = models.CharField(max_length=255, unique=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    contraseña = models.CharField(max_length=255)
    estado_login = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Usuarios'

    def set_password(self, raw_password):
        self.contraseña = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.contraseña)

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.id_rol.rol})"


class Operador(models.Model):
    id_operador = models.AutoField(primary_key=True, db_column='id_operador')
    usuario = models.OneToOneField('Usuarios', on_delete=models.CASCADE, db_column='id_usuario', null=True, blank=True)
    TipoLicencia = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento_licencia = models.DateField(blank=True, null=True)
    archivo_licencia = models.URLField(max_length=500, null=True, blank=True) # URL directa de S3
    url_licencia = models.URLField(max_length=500, blank=True, default='')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Operador'

    def __str__(self):
        if self.usuario:
            return f"{self.usuario.nombre} {self.usuario.apellido}"
        return f"Operador #{self.id_operador}"

    def delete(self, *args, **kwargs):
        # Borrado lógico: desactiva al operador y también a su usuario (para que no pueda entrar).
        self.activo = False
        if self.usuario:
            self.usuario.activo = False
            self.usuario.save()
        self.save()


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=255, unique=True)
    razon_social = models.CharField(max_length=255)
    giro = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    contacto = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Cliente'

    def __str__(self):
        return self.razon_social


class Maquinaria(models.Model):
    id_maquina = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=8, unique=True)
    modelo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=255)
    marca = models.CharField(max_length=255)
    horometro_actual = models.FloatField(default=0.0)
    estado = models.CharField(max_length=255, default='OPERATIVA')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Maquinaria'

    def __str__(self):
        return f"[{self.patente}] {self.tipo} {self.marca}"


class Contrato(models.Model):
    id_contrato = models.AutoField(primary_key=True, db_column='id_contrato')
    nombre_contrato = models.CharField(max_length=150, blank=True, null=True)
    id_cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, db_column='id_cliente')
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    estado_contrato = models.CharField(max_length=50, default='ACTIVO')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Contrato'

    def __str__(self):
        cliente_nombre = self.id_cliente.razon_social if self.id_cliente else "Sin Cliente"
        nombre = self.nombre_contrato or f"Contrato #{self.id_contrato}"
        return f"{nombre} - {cliente_nombre}"


class HES(models.Model):
    id_hes = models.AutoField(primary_key=True)
    id_contrato = models.ForeignKey(Contrato, on_delete=models.RESTRICT, db_column='id_contrato')
    numero_hes = models.CharField(max_length=255, unique=True)
    fecha_emision = models.DateField()
    total_horas_aprobadas = models.IntegerField()
    estado = models.CharField(max_length=50, default='PENDIENTE')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'HES'

    def __str__(self):
        return f"HES #{self.numero_hes} ({self.estado})"


class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True)
    id_hes = models.OneToOneField(HES, on_delete=models.RESTRICT, db_column='id_hes')
    folio = models.IntegerField(unique=True)
    fecha_emision = models.DateField()
    monto_neto = models.IntegerField()
    iva = models.IntegerField()
    monto_total = models.IntegerField()
    estado_pago = models.CharField(max_length=255, default='EMITIDA')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Factura'

    def __str__(self):
        return f"Factura #{self.folio} - HES #{self.id_hes.numero_hes}"


class Mantenimiento(models.Model):
    id_mantenimiento = models.AutoField(primary_key=True)
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, db_column='id_maquina')
    fecha_mantencion = models.DateField()
    tipo_mantencion = models.CharField(max_length=255)
    horometro_mantencion = models.IntegerField()
    estado = models.CharField(max_length=255, default='COMPLETADA')
    descripcion_mantenimiento = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Mantenimiento'

    def __str__(self):
        return f"{self.tipo_mantencion} - {self.id_maquina.patente} ({self.fecha_mantencion})"


class Report(models.Model):
    id_report = models.AutoField(primary_key=True)
    id_contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_contrato')
    id_operador = models.ForeignKey(Operador, on_delete=models.RESTRICT, db_column='id_operador')
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.RESTRICT, db_column='id_maquina')
    id_hes = models.ForeignKey(HES, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_hes')
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    horometro_inicial = models.FloatField()
    horometro_final = models.FloatField()
    horas_trabajadas = models.FloatField(default=0.0)
    firmado = models.BooleanField(default=False)
    combustible_litros = models.FloatField(default=0.0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Report'


class Gasto(models.Model):
    id_gasto = models.AutoField(primary_key=True)
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_maquina')
    id_mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_mantenimiento')
    id_contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_contrato')
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.RESTRICT, db_column='id_usuario')
    categoria_gasto = models.CharField(max_length=255)
    monto = models.IntegerField()
    fecha = models.DateField()
    numero_comprobante = models.CharField(max_length=255, default='S/N')
    url_comprobante = models.CharField(max_length=255, blank=True, default='')
    archivo_comprobante = models.FileField(upload_to='comprobantes/', null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Gasto'


class Doc_Maquinaria(models.Model):
    id_doc_maquina = models.AutoField(primary_key=True)
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, db_column='id_maquina')
    tipo_documento = models.CharField(max_length=255)
    numero_documento = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    archivo = models.FileField(upload_to='documentos_maquinaria/', null=True, blank=True)
    url_archivo = models.CharField(max_length=255, blank=True, default='')
    estado = models.CharField(max_length=255, default='VIGENTE')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Doc_Maquinaria'


class Doc_empresa(models.Model):
    id_doc_empresa = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column='id_usuario')
    nombre_documento = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    url_archivo = models.CharField(max_length=255, blank=True, default='')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Doc_empresa'


class ContratoMaquinaria(models.Model):
    id_contrato_maquinaria = models.AutoField(primary_key=True)
    id_contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, db_column='id_contrato', related_name='maquinas_contrato')
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, db_column='id_maquina')
    tarifa_hora = models.IntegerField()

    class Meta:
        db_table = 'Contrato_Maquinaria'

    def __str__(self):
        return f"Contrato #{self.id_contrato.id_contrato} - Maquina #{self.id_maquina.id_maquina}"