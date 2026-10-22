from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Multi_APP.views import (
    ReportViewSet,
    MaquinariaViewSet,
    OperadorViewSet,
    GastoViewSet,
    login_operador
)

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinaria')
router.register(r'operadores', OperadorViewSet, basename='operador')
router.register(r'gastos', GastoViewSet, basename='gasto')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/login-operador/', login_operador, name='login-operador'),
]