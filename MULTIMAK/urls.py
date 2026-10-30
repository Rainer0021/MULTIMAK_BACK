from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Multi_APP.views import (
    MaquinariaViewSet,
    OperadorViewSet,
    ReportViewSet,
    GastoViewSet,
    login_unificado
)

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinaria')
router.register(r'operadores', OperadorViewSet, basename='operador')
router.register(r'gastos', GastoViewSet, basename='gasto')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Con prefijo /api/
    path('api/', include(router.urls)),
    path('api/login/', login_unificado, name='login-unificado'),
    path('api/login-operador/', login_unificado, name='login-operador'),

    # Sin prefijo (lo que está pidiendo la web de tu compañero)
    path('', include(router.urls)),
    path('login/', login_unificado, name='login-directo'),
    path('login-operador/', login_unificado, name='login-operador-directo'),
]