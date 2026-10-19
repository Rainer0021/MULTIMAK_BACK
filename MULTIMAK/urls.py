from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Multi_APP.views import ReportViewSet, MaquinariaViewSet, login_operador

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinaria')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/login-operador/', login_operador, name='login-operador'),
]