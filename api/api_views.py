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

# HEU账号信息
class HEUAccountView(APIView):
    permission_classes = (IsAuthenticated,)

    # 获取当前绑定的HEU账号信息
    def get(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        serializer = HEUAccountSerializer(info)
        info.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 绑定HEU账号
    def post(self, request):
        serializer = HEUAccountSerializer(data=request.data)
        if serializer.is_valid():
            if not verify(serializer.validated_data['heu_username'], serializer.validated_data['heu_password']):
                return Response({'detail': 'HEU账号验证失败'}, status=status.HTTP_400_BAD_REQUEST)

            info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
            info.heu_username = serializer.validated_data['heu_username']
            info.heu_password = serializer.validated_data['heu_password']
            info.account_verify_status = True
            info.fail_last_time = True
            info.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 解绑HEU账号
    def delete(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        info.heu_username = ""
        info.heu_password = ""
        info.account_verify_status = False
        info.fail_last_time = True
        info.save()
        return Response({'detail': '成功解绑HEU账号'}, status=status.HTTP_204_NO_CONTENT)


def heu_account_verify_required(func):
    def wrapper(self, request, *args, **kwargs):
        user_id = request.session["_auth_user_id"]
        flag = True
        try:
            flag = HEUAccountInfo.objects.get(user=User.objects.get(id=user_id)).account_verify_status
        except Exception as e:
            flag = False
        if not flag:
            return Response({'detail': '需要先绑定HEU账号'}, status=status.HTTP_403_FORBIDDEN)
        return func(self, request, *args, **kwargs)
    return wrapper


# 我的课表
class MyTimeTableView(APIView):
    permission_classes = (IsAuthenticated,)

    # 获取最后一次获取的课表结果
    @heu_account_verify_required
    def get(self, request):
        info = HEUAccountInfo.objects.get(user=request.user)
        data, created = TimetableQueryResult.objects.get_or_create(heu_username=info.heu_username)
        print(data.status, created)
        if created:
            data.status = "Never"
            data.save()

        serializer = MyTimeTableSerializer(data)
        res = dict(serializer.data)
        res.update({"created": data.created.timestamp()})
        res.update({"result": json.loads(data.result)})
        return Response(res, status=status.HTTP_200_OK)

    # 请求刷新课表
    @heu_account_verify_required
    def post(self, request):
        info = HEUAccountInfo.objects.get(user=request.user)

        # 检查请求刷新间隔
        last_refresh_time = None
        data, created = TimetableQueryResult.objects.get_or_create(heu_username=info.heu_username)
        if not created:
            last_refresh_time = data.created

        if not(last_refresh_time is None):
            delta = timezone.now() - last_refresh_time
            if delta.total_seconds() <= QUERY_INTERVAL:
                return Response({'detail': '请求过于频繁！'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MyTimeTableRefreshSerializer(data=request.data)

        if serializer.is_valid():
            data.result = ""
            data.created = timezone.now()
            data.status = "Pending"
            data.save()

            query_time_table.delay(info.heu_username, info.heu_password, serializer.validated_data['term'])

            return Response({'detail': '请求刷新课表成功', 'created': data.created.timestamp()}, status=status.HTTP_201_CREATED)

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 我的成绩
class MyScoresView(APIView):
    permission_classes = (IsAuthenticated,)

    # 获取最后一次获取的成绩结果
    @heu_account_verify_required
    def get(self, request):
        info = HEUAccountInfo.objects.get(user=request.user)
        data, created = ScoreQueryResult.objects.get_or_create(heu_username=info.heu_username)
        print(data.status, created)
        if created:
            data.status = "Never"
            data.save()

        serializer = MyScoresSerializer(data)
        res = dict(serializer.data)
        res.update({"created": data.created.timestamp()})
        res.update({"result": json.loads(data.result)})
        return Response(res, status=status.HTTP_200_OK)

    # 请求刷新成绩
    @heu_account_verify_required
    def post(self, request):
        info = HEUAccountInfo.objects.get(user=request.user)

        # 检查请求刷新间隔
        last_refresh_time = None
        data, created = ScoreQueryResult.objects.get_or_create(heu_username=info.heu_username)
        if not created:
            last_refresh_time = data.created

        if not(last_refresh_time is None):
            delta = timezone.now() - last_refresh_time
            if delta.total_seconds() <= QUERY_INTERVAL:
                return Response({'detail': '请求过于频繁！'}, status=status.HTTP_400_BAD_REQUEST)

        data.result = ""
        data.created = timezone.now()
        data.status = "Pending"
        data.save()

        query_scores.delay(info.heu_username, info.heu_password)

        return Response({'detail': '请求刷新成绩成功', 'created': data.created.timestamp()}, status=status.HTTP_201_CREATED)
