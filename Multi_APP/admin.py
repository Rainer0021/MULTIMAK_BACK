from django.contrib import admin
from django.conf import settings
from .models import (
    Rol, Usuarios, Operador, Cliente, Maquinaria, 
    Contrato, HES, Factura, Mantenimiento, Report, 
    Gasto, Doc_Maquinaria, Doc_empresa, ContratoMaquinaria
)

admin.site.site_header = 'MULTIMAK 360'
admin.site.site_title = 'MULTIMAK 360'
admin.site.index_title = 'Panel de administración'
admin.site.site_url = settings.FRONTEND_URL  # el enlace "Ver el sitio" lleva a la página React

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'rol')

@admin.register(Usuarios)
class UsuariosAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'rut', 'nombre', 'apellido', 'id_rol', 'estado_login', 'debe_cambiar_clave', 'activo')

@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    list_display = ('id_operador', 'usuario', 'TipoLicencia', 'activo')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'rut', 'razon_social', 'contacto', 'activo')

@admin.register(Maquinaria)
class MaquinariaAdmin(admin.ModelAdmin):
    list_display = ('id_maquina', 'patente', 'tipo', 'marca', 'modelo', 'horometro_actual', 'estado', 'activo')

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('id_contrato', 'id_cliente', 'fecha_inicio', 'fecha_fin', 'estado_contrato', 'activo')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id_report', 'fecha', 'id_operador', 'id_maquina', 'horas_trabajadas', 'firmado', 'activo')

@admin.register(HES)
class HESAdmin(admin.ModelAdmin):
    list_display = ('id_hes', 'numero_hes', 'id_contrato', 'fecha_emision', 'estado', 'activo')

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('id_factura', 'folio', 'fecha_emision', 'monto_total', 'estado_pago', 'activo')

@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('id_mantenimiento', 'id_maquina', 'fecha_mantencion', 'tipo_mantencion', 'estado', 'activo')

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('id_gasto', 'categoria_gasto', 'monto', 'fecha', 'id_usuario', 'activo')

@admin.register(Doc_Maquinaria)
class DocMaquinariaAdmin(admin.ModelAdmin):
    list_display = ('id_doc_maquina', 'id_maquina', 'tipo_documento', 'estado', 'activo')

@admin.register(Doc_empresa)
class DocEmpresaAdmin(admin.ModelAdmin):
    list_display = ('id_doc_empresa', 'nombre_documento', 'fecha_emision', 'activo')

@admin.register(ContratoMaquinaria)
class ContratoMaquinariaAdmin(admin.ModelAdmin):
    list_display = ('id_contrato_maquinaria', 'id_contrato', 'id_maquina', 'tarifa_hora')