from django.db import models

class Cliente(models.Model):
    rut = models.CharField(max_length=12, primary_key=True)
    razon_social = models.CharField(max_length=150)
    giro = models.CharField(max_length=150)
    direccion = models.CharField(max_length=200)
    contacto = models.CharField(max_length=100)

    def __str__(self):
        return self.razon_social


class Operador(models.Model):
    rut = models.CharField(max_length=12, primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    tipo_licencia = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Maquinaria(models.Model):
    patente = models.CharField(max_length=10, primary_key=True)
    tipo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    horometro_acumulado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    estado = models.CharField(max_length=50, default="Operativa")
    
    # Campo No Estructurado (JSONB nativo en PostgreSQL) - Criterio 2.1.4.9
    datos_tecnicos_extra = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.patente} - {self.tipo}"


class Contrato(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos")
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, related_name="contratos")
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True)
    tarifa_hora = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default="Activo")

    def __str__(self):
        return f"Contrato {self.id} - {self.cliente.razon_social} ({self.maquinaria.patente})"


class Report(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="reportes")
    operador = models.ForeignKey(Operador, on_delete=models.CASCADE, related_name="reportes")
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    horometro_inicio = models.DecimalField(max_digits=10, decimal_places=2)
    horometro_final = models.DecimalField(max_digits=10, decimal_places=2)
    horas_trabajadas = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    combustible_litros = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    firmado = models.BooleanField(default=False)
    
    # Metadatos de auditoría No Estructurados - Criterio 2.1.4.9 y RS011
    metadata_auditoria = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        # Calcula automáticamente las horas trabajadas
        if self.horometro_final and self.horometro_inicio:
            self.horas_trabajadas = self.horometro_final - self.horometro_inicio
        super().save(*args, **kwargs)
        
        # Actualiza el horómetro acumulado de la máquina asignada al contrato
        if self.contrato and self.contrato.maquinaria:
            self.contrato.maquinaria.horometro_acumulado = self.horometro_final
            self.contrato.maquinaria.save()

    def __str__(self):
        return f"Report {self.id} - {self.fecha} ({self.operador})"


class Gasto(models.Model):
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, related_name="gastos")
    tipo_gasto = models.CharField(max_length=50) # Ej: Combustible, Repuesto, Viático
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()

    def __str__(self):
        return f"Gasto {self.tipo_gasto} - ${self.monto} ({self.maquinaria.patente})"