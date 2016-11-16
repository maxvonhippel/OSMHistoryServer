"""geodjango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from osmhistorynepal.views import views as json_views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^json/', json_views.nepal_statistics_view),
    url(r'^json/(?P<range>([0-9T,-:+])+)/(?P<mn_x>\d+)/(?P<mn_y>\d+)/(?P<mx_x>\d+)/(?P<mx_y>\d+)/(?P<user>\w+)/', json_views.selection_statistics_view),
]
