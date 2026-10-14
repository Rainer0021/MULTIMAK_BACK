from django.contrib import admin
from .models import Cliente, Operador, Maquinaria, Contrato, Report, Gasto

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'razon_social', 'giro', 'contacto')
    search_fields = ('rut', 'razon_social')

@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'apellido', 'tipo_licencia')
    search_fields = ('rut', 'nombre', 'apellido')

@admin.register(Maquinaria)
class MaquinariaAdmin(admin.ModelAdmin):
    list_display = ('patente', 'tipo', 'marca', 'modelo', 'horometro_acumulado', 'estado')
    list_filter = ('tipo', 'estado')
    search_fields = ('patente', 'modelo')

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'maquinaria', 'fecha_inicio', 'tarifa_hora', 'estado')
    list_filter = ('estado',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'contrato', 'operador', 'horometro_inicio', 'horometro_final', 'horas_trabajadas', 'firmado')
    list_filter = ('firmado', 'fecha')

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('id', 'maquinaria', 'tipo_gasto', 'monto', 'fecha')
    list_filter = ('tipo_gasto',)