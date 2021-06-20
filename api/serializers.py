from rest_framework import serializers
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
