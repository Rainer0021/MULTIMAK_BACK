from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    login_unificado, resumen_kpis,
    MaquinariaViewSet, OperadorViewSet, ReportViewSet, GastoViewSet,
    ClienteViewSet, ContratoViewSet, HESViewSet, FacturaViewSet,
    DocMaquinariaViewSet, DocEmpresaViewSet, ContratoMaquinariaViewSet
)

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinaria')
router.register(r'operadores', OperadorViewSet, basename='operador')
router.register(r'gastos', GastoViewSet, basename='gasto')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'contratos', ContratoViewSet, basename='contrato')
router.register(r'hes', HESViewSet, basename='hes')
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'doc-maquinaria', DocMaquinariaViewSet, basename='doc-maquinaria')
router.register(r'doc-empresa', DocEmpresaViewSet, basename='doc-empresa')
router.register(r'contrato-maquinarias', ContratoMaquinariaViewSet, basename='contrato-maquinaria')

urlpatterns = [
    path('login/', login_unificado, name='login-unificado'),
    path('login-operador/', login_unificado, name='login-operador'),
    path('kpis/', resumen_kpis, name='resumen-kpis'),
    path('', include(router.urls)),
]