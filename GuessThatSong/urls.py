"""
URL configuration for GuessThatSong project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from GTS.views import pub_list, join_pub, login_view, get_pub, create_pub, create_user, get_records,get_time_records, remove_pub
from django.urls import include
from GuessThatSong import routing

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/pubs', pub_list, name='pub-list'),
    path('api/pubs/get/<int:pubId>/', get_pub, name='get-pub'),
    path('api/pubs/createpub', create_pub, name='create-pub'),
    path('api/pubs/delete', remove_pub, name='delete-pub'),
    path('api/users/create', create_user, name='create-user'),
    path('api/pubs/join', join_pub, name='join-pub'),
    path('api/users/login', login_view, name='login-view'),
    path('api/tracks/records/get', get_records, name='get-records'),
    path('api/tracks/records/time/get', get_time_records, name='get-time-records'),
    path('ws/chat/', include(routing.websocket_urlpatterns)),  # WebSocket URLs

]
