from django.db import models

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    rol = models.CharField(max_length=40)

    class Meta:
        db_table = 'Rol'

    def __str__(self):
        return self.rol

class Usuarios(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.RESTRICT, db_column='id_rol')
    rut = models.CharField(max_length=255)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    contraseña = models.CharField(max_length=255)
    estado_login = models.BooleanField(default=False)

    class Meta:
        db_table = 'Usuarios'

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Operador(models.Model):
    id_operador = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column='id_usuario')
    TipoLicencia = models.CharField(max_length=255)
    fecha_vencimiento_licencia = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'Operador'

    def __str__(self):
        return f"Operador: {self.id_usuario.nombre} {self.id_usuario.apellido}"

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=255)
    razon_social = models.CharField(max_length=255)
    giro = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    contacto = models.CharField(max_length=255)

    class Meta:
        db_table = 'Cliente'

    def __str__(self):
        return self.razon_social

class Maquinaria(models.Model):
    id_maquina = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=8)
    modelo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=255)
    marca = models.CharField(max_length=255)
    horometro_actual = models.FloatField(default=0.0)
    estado = models.CharField(max_length=255)

    class Meta:
        db_table = 'Maquinaria'

    def __str__(self):
        return f"{self.tipo} {self.marca} ({self.patente})"

class Contrato(models.Model):
    id_contrato = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, db_column='id_cliente')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    tarifa_hora = models.IntegerField()
    estado_contrato = models.CharField(max_length=255)

    class Meta:
        db_table = 'Contrato'

    def __str__(self):
        return f"Contrato #{self.id_contrato} - {self.id_cliente.razon_social}"

class HES(models.Model):
    id_hes = models.AutoField(primary_key=True)
    id_contrato = models.ForeignKey(Contrato, on_delete=models.RESTRICT, db_column='id_contrato')
    numero_hes = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    total_horas_aprobadas = models.IntegerField()
    estado = models.CharField(max_length=255)

    class Meta:
        db_table = 'HES'

    def __str__(self):
        return f"HES #{self.numero_hes}"

class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True)
    id_hes = models.ForeignKey(HES, on_delete=models.RESTRICT, db_column='id_hes')
    folio = models.IntegerField()
    fecha_emision = models.DateField()
    monto_neto = models.IntegerField()
    iva = models.IntegerField()
    monto_total = models.IntegerField()
    estado_pago = models.CharField(max_length=255)

    class Meta:
        db_table = 'Factura'

    def __str__(self):
        return f"Factura #{self.folio}"

class Mantenimiento(models.Model):
    id_mantenimiento = models.AutoField(primary_key=True)
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, db_column='id_maquina')
    fecha_mantencion = models.DateField()
    tipo_mantencion = models.CharField(max_length=255)
    horometro_mantencion = models.IntegerField()
    estado = models.CharField(max_length=255)
    descripcion_mantenimiento = models.CharField(max_length=255)

    class Meta:
        db_table = 'Mantenimiento'

    def __str__(self):
        return f"Mantenimiento #{self.id_mantenimiento} - Máquina {self.id_maquina.patente}"

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
    horas_trabajadas = models.IntegerField()
    firmado = models.BooleanField(default=False)
    combustible_litros = models.FloatField(default=0.0)

    class Meta:
        db_table = 'Report'

    def __str__(self):
        return f"Reporte #{self.id_report} - {self.id_maquina.patente}"

class Gasto(models.Model):
    id_gasto = models.AutoField(primary_key=True)
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_maquina')
    id_mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_mantenimiento')
    id_contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_contrato')
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.RESTRICT, db_column='id_usuario')
    categoria_gasto = models.CharField(max_length=255)
    monto = models.IntegerField()
    fecha = models.DateField()
    numero_comprobante = models.CharField(max_length=255)
    url_comprobante = models.CharField(max_length=255)

    class Meta:
        db_table = 'Gasto'

    def __str__(self):
        return f"Gasto #{self.id_gasto} - ${self.monto}"

class Doc_Maquinaria(models.Model):
    id_doc_maquina = models.AutoField(primary_key=True)
    id_maquina = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, db_column='id_maquina')
    tipo_documento = models.CharField(max_length=255)
    numero_documento = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    url_archivo = models.CharField(max_length=255)
    estado = models.CharField(max_length=255)

    class Meta:
        db_table = 'Doc_Maquinaria'

class Doc_empresa(models.Model):
    id_doc_empresa = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column='id_usuario')
    nombre_documento = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    url_archivo = models.CharField(max_length=255)

    class Meta:
        db_table = 'Doc_empresa'