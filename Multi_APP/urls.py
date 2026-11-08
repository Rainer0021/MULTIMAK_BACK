from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    generar_url_lectura, login_unificado, resumen_kpis, MaquinariaViewSet, OperadorViewSet,
    ReportViewSet, GastoViewSet, ClienteViewSet, ContratoViewSet,
    HESViewSet, FacturaViewSet, DocMaquinariaViewSet, DocEmpresaViewSet,
    ContratoMaquinariaViewSet, MantenimientoViewSet, contratos_para_operador,
    login_evaluacion, logout_evaluacion, registro_evaluacion, MaquinariaListView, generar_url_presignada, admin_sso
)

router = DefaultRouter()
router.register(r'maquinarias', MaquinariaViewSet)
router.register(r'operadores', OperadorViewSet)
router.register(r'mantenimientos', MantenimientoViewSet)
router.register(r'reports', ReportViewSet)
router.register(r'gastos', GastoViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'contratos', ContratoViewSet)
router.register(r'hes', HESViewSet)
router.register(r'facturas', FacturaViewSet)
router.register(r'doc-maquinaria', DocMaquinariaViewSet)
router.register(r'doc-empresa', DocEmpresaViewSet)
router.register(r'contrato-maquinarias', ContratoMaquinariaViewSet)

urlpatterns = [
    # Tu API para React
    path('', include(router.urls)),
    
    # Endpoints de login (al estar bajo 'api/' en el urls principal, responderán en /api/login/ etc.)
    path('login/', login_unificado, name='login_unificado'),
    path('login', login_unificado),
    path('login-operador/', login_unificado, name='login_operador'),
    path('login-operador', login_unificado),
    
    path('admin-sso/', admin_sso, name='admin_sso'),
    path('resumen-kpis/', resumen_kpis, name='resumen_kpis'),
    path('contratos-operador/', contratos_para_operador, name='contratos_operador'),

    # Vistas de evaluación de Django
    path('panel/login/', login_evaluacion, name='login_evaluacion'),
    path('panel/logout/', logout_evaluacion, name='logout_evaluacion'),
    path('panel/registro/', registro_evaluacion, name='registro_evaluacion'),
    path('panel/maquinarias/', MaquinariaListView.as_view(), name='panel_maquinarias'),
    path('generar-url-s3/', generar_url_presignada, name='generar_url_s3'),
    path('generar-url-lectura/', generar_url_lectura, name='generar_url_lectura'),
]