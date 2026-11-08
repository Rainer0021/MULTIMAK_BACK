from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt


def admin_login_al_login(request):
    """/admin/login/ ya no se usa: se manda al login normal de la página."""
    return redirect(settings.FRONTEND_URL)


@csrf_exempt
def admin_logout_al_login(request):
    """Cierra la sesión de Django y vuelve al login normal de la página."""
    logout(request)
    return redirect(settings.FRONTEND_URL)


urlpatterns = [
    path('admin/login/', admin_login_al_login),
    path('admin/logout/', admin_logout_al_login),
    path('admin/', admin.site.urls),
    path('api/', include('Multi_APP.urls')),
]

# Archivos subidos (comprobantes, licencias). En producción conviene servirlos con nginx desde MEDIA_ROOT.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)