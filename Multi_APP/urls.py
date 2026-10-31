from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    MaquinariaViewSet,
    OperadorViewSet,
    ReportViewSet,
    GastoViewSet,
    ClienteViewSet,
    ContratoViewSet,
    HESViewSet,
    FacturaViewSet,
    DocMaquinariaViewSet,
    DocEmpresaViewSet,
    login_unificado
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
router.register(r'doc-maquinarias', DocMaquinariaViewSet, basename='doc-maquinaria')
router.register(r'doc-empresas', DocEmpresaViewSet, basename='doc-empresa')

urlpatterns = [
    # Esto incluye todas las rutas del router (ej: /api/maquinarias/, /maquinarias/, etc.)
    *router.urls,
    path('login/', login_unificado, name='login-unificado'),
    path('login-operador/', login_unificado, name='login-operador'),
]