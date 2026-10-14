from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Multi_APP.views import (
    ClienteViewSet,
    OperadorViewSet,
    MaquinariaViewSet,
    ContratoViewSet,
    ReportViewSet,
    GastoViewSet,
    LoginView,  # <-- Agregado aquí
)

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'operadores', OperadorViewSet)
router.register(r'maquinarias', MaquinariaViewSet)
router.register(r'contratos', ContratoViewSet)
router.register(r'reports', ReportViewSet)
router.register(r'gastos', GastoViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', LoginView.as_view(), name='login'),  # <-- Ruta del login agregada aquí
    path('api/', include(router.urls)),
]