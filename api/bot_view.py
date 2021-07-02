from api.models import *
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from api.serializers import *
from lib.heu import *
from django.contrib.auth.models import User
from qinglianjie.settings import QUERY_INTERVAL
from api.tasks import *
from datetime import datetime
from rest_framework import permissions
from rest_framework import generics


class NoticeTaskList(generics.ListAPIView):
    queryset = NoticeTask.objects.all()
    serializer_class = NoticeTaskSerializer
    permission_classes = (IsAuthenticated, permissions.IsAdminUser)


class NoticeTaskRetrieveDestroy(generics.RetrieveDestroyAPIView):
    queryset = NoticeTask.objects.all()
    serializer_class = NoticeTaskSerializer
    permission_classes = (IsAuthenticated, permissions.IsAdminUser)


class GroupInfoListCreate(generics.ListCreateAPIView):
    queryset = GroupInfo.objects.all()
    serializer_class = GroupInfoSerialize
    permission_classes = (IsAuthenticated, permissions.IsAdminUser)


class GroupInfoRetrieveUpdate(generics.RetrieveUpdateAPIView):
    lookup_field = 'group_id'
    queryset = GroupInfo.objects.all()
    serializer_class = GroupInfoSerialize
    permission_classes = (IsAuthenticated, permissions.IsAdminUser)