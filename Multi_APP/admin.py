from django.contrib import admin
from .models import (
    Rol, Usuarios, Operador, Cliente, Maquinaria, 
    Contrato, HES, Factura, Mantenimiento, Report, 
    Gasto, Doc_Maquinaria, Doc_empresa
)

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'rol')

@admin.register(Usuarios)
class UsuariosAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'rut', 'nombre', 'apellido', 'id_rol', 'estado_login')

@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    list_display = ('id_operador', 'id_usuario', 'TipoLicencia')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'rut', 'razon_social', 'contacto')

@admin.register(Maquinaria)
class MaquinariaAdmin(admin.ModelAdmin):
    list_display = ('id_maquina', 'patente', 'tipo', 'marca', 'modelo', 'horometro_actual', 'estado')

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('id_contrato', 'id_cliente', 'fecha_inicio', 'fecha_fin', 'tarifa_hora', 'estado_contrato')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id_report', 'fecha', 'id_operador', 'id_maquina', 'horas_trabajadas', 'firmado')

@admin.register(HES)
class HESAdmin(admin.ModelAdmin):
    list_display = ('id_hes', 'numero_hes', 'id_contrato', 'fecha_emision', 'estado')

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('id_factura', 'folio', 'fehca_emision', 'monto_total', 'estado_pago')

@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('id_mantenimiento', 'id_maquina', 'fecha_mantencion', 'tipo_mantencion', 'estado')

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('id_gasto', 'categoria_gasto', 'monto', 'fecha', 'id_usuario')

@admin.register(Doc_Maquinaria)
class DocMaquinariaAdmin(admin.ModelAdmin):
    list_display = ('id_doc_maquina', 'id_maquina', 'tipo_documento', 'estado')

@admin.register(Doc_empresa)
class DocEmpresaAdmin(admin.ModelAdmin):
    list_display = ('id_doc_empresa', 'nombre_documento', 'fecha_emision')