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
from rest_framework import mixins


class HEUAccountVerified(permissions.BasePermission):
    message = "需要先绑定HEU账号"
    def has_permission(self, request, view):
        flag = True
        try:
            flag = HEUAccountInfo.objects.get(user=request.user).account_verify_status
        except Exception as e:
            flag = False
        print("fuck", flag)
        return flag


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


# 我的课表
class MyTimeTableView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified)

    # 获取最后一次获取的课表结果
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
    permission_classes = (IsAuthenticated, HEUAccountVerified)

    # 获取最后一次获取的成绩结果
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

        data.result = "{}"
        data.created = timezone.now()
        data.status = "Pending"
        data.save()

        query_scores.delay(info.heu_username, info.heu_password)

        return Response({'detail': '请求刷新成绩成功', 'created': data.created.timestamp()}, status=status.HTTP_201_CREATED)


# 绑定qq
class BindQQView(APIView):
    permission_classes = (IsAuthenticated, )

    # 获取当前绑定的QQ账号信息
    def get(self, request):
        info = QQBindInfo.objects.get_or_create(user=request.user)[0]
        serializer = QQBindInfoSerialize(info)
        info.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 绑定QQ账号
    def post(self, request):
        serializer = QQBindInfoSerialize(data=request.data)
        if serializer.is_valid():
            info = QQBindInfo.objects.get_or_create(user=request.user)[0]
            if 'qq_id' in serializer.validated_data.keys():
                info.qq_id = serializer.validated_data['qq_id']
            info.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 解绑QQ账号
    def delete(self, request):
        info = QQBindInfo.objects.get_or_create(user=request.user)[0]
        info.qq_id = 0
        info.save()
        return Response({'detail': '成功解绑QQ账号'}, status=status.HTTP_204_NO_CONTENT)


# 用户信息
class UserInfoView(generics.RetrieveAPIView):
    permission_classes = ()
    queryset = User.objects.all()
    serializer_class = UserInfoSerialize
    lookup_field = "username"

    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserInfoSerialize(user)
        res = dict(serializer.data)

        url = None
        try:
            image = UserProfilePhoto.objects.get_or_create(user=user)[0].image
            url = image.url
        except ValueError as e:
            pass
        res.update({"image": url,})

        if request.user.is_authenticated and username == request.user.username:
            res.update({
                "heu_username": HEUAccountInfo.objects.get_or_create(user=user)[0].heu_username,
                "email": user.email,
            })
        return Response(res, status=status.HTTP_200_OK)


# 课程评论
class RecentCommentView(generics.ListAPIView):
    permission_classes = ()
    queryset = CourseComment.objects.all()[:10]
    serializer_class = CourseCommentSerialize

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


# 最近出分
class RecentGradeCourseView(generics.ListAPIView):
    permission_classes = ()
    serializer_class = RecentGradeCourseSerialize
    queryset = RecentGradeCourse.objects.filter(created__gt=datetime(
        datetime.now().year,
        datetime.now().month,
        datetime.now().day,
    ))


# 头像上传
class UserProfilePhotoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        info = UserProfilePhoto.objects.get_or_create(user=request.user)[0]
        serializer = UserProfilePhotoSerialize(info)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 上传头像
    def post(self, request):
        serializer = UserProfilePhotoSerialize(data=request.data)
        if serializer.is_valid():
            info, created = UserProfilePhoto.objects.get_or_create(user=request.user)
            if not created:
                info.image.delete()
            print(dict(serializer.validated_data))
            print(serializer.validated_data)
            info.image = serializer.validated_data['image']
            info.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 删除头像
    def delete(self, request):
        info = UserProfilePhoto.objects.get_or_create(user=request.user)[0]
        info.image.delete()
        info.save()
        return Response({'detail': '头像已经删除'}, status=status.HTTP_204_NO_CONTENT)

