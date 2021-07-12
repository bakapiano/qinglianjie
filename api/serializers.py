from rest_framework import serializers
from django.contrib.auth.models import User
from api.models import *


class HEUAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = HEUAccountInfo
        fields = [
            'heu_username',
            'heu_password'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not (data.get('heu_password') is None):
            del data['heu_password']
        return data


class MyTimeTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableQueryResult
        fields = ['heu_username', 'result', 'created', 'status']


class MyTimeTableRefreshSerializer(serializers.Serializer):
    term = serializers.CharField(required=True, allow_blank=False, max_length=20)


class MyScoresSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableQueryResult
        fields = ['heu_username', 'result', 'created', 'status']


class NoticeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticeTask
        fields = ["pk", "qq_id", "content", "type"]


class QQBindInfoSerialize(serializers.ModelSerializer):
    class Meta:
        model = QQBindInfo
        fields = ['qq_id',]


class GroupInfoSerialize(serializers.ModelSerializer):
    class Meta:
        model = GroupInfo
        fields = ['group_id', "notice_when_xk"]


class UserInfoSerialize(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['pk', 'username']


class CourseCommentSerialize(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    course_id = serializers.CharField(source='course.course_id')
    course_name = serializers.CharField(source='course.name')

    class Meta:
        model = CourseComment
        fields = ['username', 'course_name', 'course_id', 'content', 'created', 'anonymous']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('anonymous'):
            data['username'] = "匿名"
        return data
