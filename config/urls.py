"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path, re_path

from portfolio.admin import portfolio_admin_site
from portfolio.health import health
from portfolio.views import api_not_found

urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', portfolio_admin_site.urls),
    path('api/v1/', include('portfolio.urls')),
    re_path(r'^api/.*$', api_not_found),
]

handler404 = api_not_found
