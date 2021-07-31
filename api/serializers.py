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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        url = None
        try:
            image = UserProfilePhoto.objects.get_or_create(user=instance)[0].image
            url = image.url
        except ValueError as e:
            pass
        data['image'] = url
        return data


class CourseInfoSerialize(serializers.ModelSerializer):
    class Meta:
        model = CourseInfo
        fields = '__all__'


class CourseCommentSerialize(serializers.ModelSerializer):
    user = UserInfoSerialize()
    course = CourseInfoSerialize()

    class Meta:
        model = CourseComment
        fields = ['id', 'content', 'created', 'anonymous', "course", "user", "show", "score"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('anonymous'):
            data['user'] = {'username': '匿名',}
        return data


class RecentGradeCourseSerialize(serializers.ModelSerializer):
    course = CourseInfoSerialize()

    class Meta:
        model = RecentGradeCourse
        fields = ['course', 'created']


class UserProfilePhotoSerialize(serializers.ModelSerializer):
    class Meta:
        model = UserProfilePhoto
        fields = ['image']


class TaskInfoSerialize(serializers.ModelSerializer):
    class Meta:
        model = TaskInfo
        fields = ['user', 'title', 'description', 'status', "additional_info", "created"]
