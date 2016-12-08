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

    for jsonselection, it looks like this
    jsonselection/YYYY-MM-DDTHH:MM:SS,YYYY-MM-DDTHH:MM:SS/West/South/East/North/username
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from osmhistorynepal import views as json_views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^usernames/', json_views.user_names_view),
    # request, range, mn_x, mn_y, mx_x, mx_y, first, second, third, fourth, fifth
    url(r'^topnodes/(?P<timerange>([0-9T,-:+])+)/(?P<mn_x>([0-9]+.[0-9]+))/(?P<mn_y>([0-9]+.[0-9]+))/(?P<mx_x>([0-9]+.[0-9]+))/(?P<mx_y>([0-9]+.[0-9]+))/(?P<first>\w*)/(?P<second>\w*)/(?P<third>\w*)/(?P<fourth>\w*)/(?P<fifth>\w*)/', json_views.top_five_nodes_poi),
    url(r'^jsoncountry/', json_views.nepal_statistics_view),
    url(r'^jsonselection/(?P<timerange>([0-9T,-:+])+)/(?P<mn_x>([0-9]+.[0-9]+))/(?P<mn_y>([0-9]+.[0-9]+))/(?P<mx_x>([0-9]+.[0-9]+))/(?P<mx_y>([0-9]+.[0-9]+))/(?P<user>\w*)/', json_views.selection_statistics_view),
    # url(r'^nodes/(?P<date>([0-9T,-:+])+)/(?P<mn_x>\d+)/(?P<mn_y>\d+)/(?P<mx_x>\d+)/(?P<mx_y>\d+)/(?P<user>\w*)/', json_views.nodes_view),

]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
