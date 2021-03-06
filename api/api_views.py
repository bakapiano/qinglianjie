from django.views.decorators.cache import cache_page
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from api.models import *
from django.http import Http404, JsonResponse
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
from rest_framework import filters, pagination
from django_filters.rest_framework import DjangoFilterBackend
from ratelimit.decorators import ratelimit, ALL

from django.shortcuts import reverse


class HEUAccountVerified(permissions.BasePermission):
    message = "需要先绑定HEU账号"

    def has_permission(self, request, view):
        flag = True
        try:
            flag = HEUAccountInfo.objects.get(user=request.user).account_verify_status
        except Exception as e:
            flag = False
        # print("fuck", flag)
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
        print(request.data)
        serializer = HEUAccountSerializer(data=request.data)
        if serializer.is_valid():
            if HEUAccountInfo.objects.filter(heu_username=serializer.validated_data['heu_username']).count() != 0:
                return Response({'detail': '该HEU账号已被绑定！'}, status=status.HTTP_400_BAD_REQUEST)

            if not verify(serializer.validated_data['heu_username'], serializer.validated_data['heu_password']):
                return Response({'detail': 'HEU账号验证失败'}, status=status.HTTP_400_BAD_REQUEST)

            info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
            info.heu_username = serializer.validated_data['heu_username']
            info.heu_password = serializer.validated_data['heu_password']
            info.account_verify_status = True
            info.fail_last_time = True
            info.save()

            from api.tasks import do_collect_scores
            do_collect_scores.delay(info.id, True)

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
        try:
            res.update({"result": json.loads(data.result)})
        except Exception as e:
            res.update({"result": {}})

        return Response(res, status=status.HTTP_200_OK)

    # 请求刷新课表
    def post(self, request):
        info = HEUAccountInfo.objects.get(user=request.user)

        # 检查请求刷新间隔
        last_refresh_time = None
        data, created = TimetableQueryResult.objects.get_or_create(heu_username=info.heu_username)
        if not created:
            last_refresh_time = data.created

        if not (last_refresh_time is None):
            delta = timezone.now() - last_refresh_time
            if delta.total_seconds() <= QUERY_INTERVAL:
                return Response({'detail': '请求过于频繁！'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MyTimeTableRefreshSerializer(data=request.data)

        if serializer.is_valid():
            data.result = ""
            data.created = timezone.now()
            data.status = "Pending"
            data.save()

            task_info = TaskInfo.objects.create(
                title="刷新我的课表",
                description="%s 学期" % serializer.validated_data['term'],
                status="Pending",
                user=info.user,
            )
            task_info.save()
            print(info, id)

            import api
            api.tasks.query_time_table.delay(info.id, serializer.validated_data['term'], task_info.id)

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
        try:
            res.update({"result": json.loads(data.result)})
        except Exception as e:
            res.update({"result": {}})
        return Response(res, status=status.HTTP_200_OK)

    # 请求刷新成绩
    def post(self, request):
        info = HEUAccountInfo.objects.get(user=request.user)

        # 检查请求刷新间隔
        last_refresh_time = None
        data, created = ScoreQueryResult.objects.get_or_create(heu_username=info.heu_username)
        if not created:
            last_refresh_time = data.created

        if not (last_refresh_time is None):
            delta = timezone.now() - last_refresh_time
            if delta.total_seconds() <= QUERY_INTERVAL:
                return Response({'detail': '请求过于频繁！'}, status=status.HTTP_400_BAD_REQUEST)

        # data.result = "{}"
        data.created = timezone.now()
        data.status = "Pending"
        data.save()

        task_info = TaskInfo.objects.create(
            title="刷新我的成绩",
            status="Pending",
            user=info.user,
        )
        task_info.save()

        import api
        api.tasks.query_scores.delay(info.id, task_info.id)

        return Response({'detail': '请求刷新成绩成功', 'created': data.created.timestamp()}, status=status.HTTP_201_CREATED)


# 绑定qq
class BindQQView(APIView):
    permission_classes = (IsAuthenticated,)

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


# 用户信息 Profile
class UserInfoView(generics.RetrieveAPIView):
    permission_classes = ()
    queryset = User.objects.all()
    serializer_class = UserInfoSerialize
    lookup_field = "username"

    def get(self, request, username, show_comment=True):
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
        res.update({"image": url, })

        if request.user.is_authenticated and username == request.user.username:
            res.update({
                "self": True,
                "heu_username": HEUAccountInfo.objects.get_or_create(user=user)[0].heu_username,
                "email": user.email,
                "comments": [
                    CourseCommentSerialize(comment).data for comment in CourseComment.objects.filter(user=user)
                ] if show_comment else [],
            })
            if show_comment:
                for comment in res["comments"]:
                    comment["self"] = True
        else:
            res.update({
                "self": False,
                "comments": [
                    CourseCommentSerialize(comment).data for comment in CourseComment.objects.filter(
                        user=user,
                        anonymous=False
                    )
                ] if show_comment else [],
            })

        if not show_comment:
            del res['comments']

        return Response(res, status=status.HTTP_200_OK)


# 个人信息
class CurrentUserInfoView(UserInfoView):
    permission_classes = (IsAuthenticated,)
    lookup_field = ""

    def get(self, request):
        return super().get(request, username=self.request.user.username, show_comment=False)


# 课程评论
class RecentCommentView(APIView):
    permission_classes = ()

    def get(self, request):
        comments = [{
            **CourseCommentSerialize(comment).data,
            **({'self': request.user == comment.user} if request.user.is_authenticated else {}), }
            for comment in CourseComment.objects.all()[:10]]
        return Response(comments, status=status.HTTP_200_OK)


# 最近出分
class RecentGradeCourseView(APIView):
    permission_classes = ()

    def get(self, request):
        res = [RecentGradeCourseSerialize(record).data for
               record in RecentGradeCourse.objects.filter(created__gt=datetime(
                datetime.now().year,
                datetime.now().month,
                datetime.now().day,
            ))]
        return Response(res, status=status.HTTP_200_OK)


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


# 课程详细
class CourseInfoView(generics.RetrieveAPIView):
    permission_classes = ()
    queryset = CourseInfo.objects.all()
    serializer_class = CourseInfoSerialize
    lookup_field = "course_id"

    def get(self, request, course_id):
        try:
            course = CourseInfo.objects.get(course_id=course_id)
        except CourseInfo.DoesNotExist as e:
            return Response({'detail': '未找到。'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseInfoSerialize(course)
        res = dict(serializer.data)
        comments = [{
                **CourseCommentSerialize(comment).data,
                **({'self': request.user == comment.user} if request.user.is_authenticated else {}),}
            for comment in CourseComment.objects.filter(course__course_id=course_id)]
        for comment in comments:
            del comment['course']
        res.update({
            "comments": comments,
            "more_comments": reverse("api_course_comment", kwargs={"course_id": course_id}),
            "statistics": get_statistics_result_from_database(course_id)
        })

        if request.user.is_authenticated:
            info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
            print(info.heu_username)
            scores = [record.score for record in CourseScore.objects.filter(
                heu_username=info.heu_username,
                course__course_id=course_id
            )]
            if len(scores) == 0:
                scores = None
            res.update({"my_scores": scores})
        else:
            res.update({"my_scores": None})

        return Response(res, status=status.HTTP_200_OK)


def get_statistics_result_from_database(course_id: str):
    result = {}
    try:
        course = CourseInfo.objects.get(course_id=course_id)
        result = json.loads(CourseStatisticsResult.objects.get_or_create(course=course, is_fubaijie_data=False)[0].result)
        fubaijie_result = CourseStatisticsResult.objects.get_or_create(course=course, is_fubaijie_data=True)[0].result
        try:
            result.update(json.loads(fubaijie_result))
        except Exception as e:
            print(e)
            pass
    except Exception as e:
        pass
    return result


def get_statistics_result(course_id: str):
    result = {}
    terms = [obj['term'] for obj in CourseScore.objects.values("term").order_by("term").distinct()]
    terms.insert(0, 'all')

    for term in terms:
        result_exam = {}
        for i in range(0, 101):
            count = 0
            if term == "all":
                count = CourseScore.objects.filter(
                    course__course_id=course_id,
                    score=str(i),
                ).count()
            else:
                count = CourseScore.objects.filter(
                    course__course_id=course_id,
                    score=str(i),
                    term=term,
                ).count()
            if count != 0:
                result_exam.update({i: count})

        result_test = {}
        for i in ("不及格", "及格", "中等", "良好", "优秀"):
            count = 0
            if term == "all":
                count = CourseScore.objects.filter(
                    course__course_id=course_id,
                    score=str(i),
                ).count()
            else:
                count = CourseScore.objects.filter(
                    course__course_id=course_id,
                    score=str(i),
                    term=term,
                ).count()
            if count != 0:
                result_test.update({i: count})

        total = 0
        for value in result_exam.values():
            total += value
        for value in result_test.values():
            total += value

        if total != 0 or term == "all":
            result.update({
                term: {
                    "total": total,
                    "exam": result_exam,
                    "test": result_test,
                }
            })
    return result


# 课程评论
class CourseCommentView(generics.ListAPIView):
    permission_classes = ()
    lookup_field = "course_id"
    serializer_class = CourseCommentSerialize

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        queryset = CourseComment.objects.filter(course__course_id=course_id)
        return queryset

    class CreateCourseSerialize(serializers.ModelSerializer):
        class Meta:
            model = CourseComment
            fields = ['content', 'anonymous', "show", "score"]

    def get(self, request, course_id):
        comments = [{
                **CourseCommentSerialize(comment).data,
                **({'self': request.user == comment.user} if request.user.is_authenticated else {}),}
            for comment in CourseComment.objects.filter(course__course_id=course_id)]
        return Response(comments, status=status.HTTP_200_OK)

    def post(self, request, course_id):
        if not request.user.is_authenticated:
            return Response({'detail': '身份认证信息未提供。'}, status=status.HTTP_403_FORBIDDEN)

        from qinglianjie.settings import COURSE_COMMENT_INTERVAL
        if CourseComment.objects.filter(user=request.user).count() > 0 and \
                (timezone.now() - CourseComment.objects.filter(user=request.user).first().created).total_seconds() <= COURSE_COMMENT_INTERVAL:
            return Response({'detail': '评论间隔限制为 %s 秒' % str(COURSE_COMMENT_INTERVAL)}, status=status.HTTP_400_BAD_REQUEST)

        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        if request.data.get('show') == True and CourseScore.objects.filter(
                course__course_id=course_id,
                heu_username=info.heu_username,
                score=request.data.get('score'),
        ).count() == 0:
            return Response({'detail': '没查到该分数记录。'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.CreateCourseSerialize(data=request.data)
        if serializer.is_valid():
            CourseComment.objects.create(
                user=request.user,
                course=CourseInfo.objects.get(course_id=course_id),
                content=serializer.validated_data['content'],
                created=timezone.now(),
                anonymous=serializer.validated_data['anonymous'],
                show=serializer.validated_data['show'],
                score=serializer.validated_data['score'] if serializer.validated_data['show'] else "",
            ).save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 课程统计数据
class CourseStatisticsView(APIView):
    permission_classes = ()
    lookup_field = "course_id"

    def get(self, request, course_id):
        return Response(get_statistics_result_from_database(course_id), status=status.HTTP_200_OK)


class CoursePagination(pagination.PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = 'num'


class LearnedCoursesFilterBackend(filters.BaseFilterBackend):
    """
    筛选学过课程
    """

    def filter_queryset(self, request, queryset, view):
        if (not request.user.is_authenticated) or (request.GET.get("learned") != "true"):
            return queryset

        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        if not info.account_verify_status:
            return queryset

        heu_username = info.heu_username
        learned = CourseScore.objects.values_list("course__course_id").filter(heu_username=heu_username)

        return queryset.filter(course_id__in=learned)


# 课程筛选页面
class CoursesView(generics.ListAPIView):
    permission_classes = ()
    queryset = CourseInfo.objects.all().order_by("-count")
    serializer_class = CourseInfoSerialize
    pagination_class = CoursePagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, LearnedCoursesFilterBackend]
    filterset_fields = ('kind', 'credit', 'total_time', 'assessment_method', 'attributes')
    search_fields = ("course_id", "name")


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.user == request.user


class CourseCommentDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = (IsOwnerOrReadOnly, )
    queryset = CourseComment.objects.all()
    serializer_class = CourseCommentSerialize


class PingjiaoView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified)

    def get(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        try:
            crawler = Crawler()
            crawler.login_pingjiao(info.heu_username, info.heu_password)
            res = crawler.pingjiao(True)
        except Exception as e:
            return Response({'detail': '获取未评教课程时出现错误，可能是HEU账号密码错误或者学校评教服务器故障！'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'todo': res
        }, status=status.HTTP_200_OK)

    def post(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        try:
            crawler = Crawler()
            crawler.login_pingjiao(info.heu_username, info.heu_password)
            res = crawler.pingjiao(False)
        except Exception as e:
            TaskInfo.objects.create(
                title="一键评教",
                status="Fail",
                user=info.user,
                additional_info='一键评教时出现错误，可能是HEU账号密码错误或者学校评教服务器故障！',
                exception=str(e),
            ).save()
            return Response({'detail': '一键评教时出现错误，可能是HEU账号密码错误或者学校评教服务器故障！'},
                            status=status.HTTP_400_BAD_REQUEST)

        TaskInfo.objects.create(
            title="一键评教",
            description=",".join(res)+"已评教完成！",
            status="Success",
            user=info.user,
        ).save()
        return Response({
            'detail': '一键评教成功！',
            'done': res,
        }, status=status.HTTP_200_OK)


class TaskInfoView(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        tasks = [TaskInfoSerialize(task).data for task in TaskInfo.objects.filter(user=request.user)]
        return Response(tasks, status=status.HTTP_200_OK)


class ReportTasksView(generics.ListAPIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified)

    class ReportTaskPostSerialize(serializers.ModelSerializer):
        class Meta:
            model = ReportTask
            fields = ['time']

    serializer_class = ReportTaskPostSerialize
    queryset = []

    def get(self, request):
        tasks = [ReportTaskSerialize(task).data for task in ReportTask.objects.filter(user=request.user)]
        return Response(tasks, status=status.HTTP_200_OK)

    def post(self, request):
        from qinglianjie.settings import MAX_REPORT_TASKS_NUM
        if ReportTask.objects.filter(user=request.user, status="Waiting").count() >= MAX_REPORT_TASKS_NUM:
            return Response({"detail": "报备任务个数上限为：%d" % MAX_REPORT_TASKS_NUM}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReportTasksView.ReportTaskPostSerialize(data=request.data)
        if serializer.is_valid():
            time = serializer.validated_data["time"]
            now = timezone.now()

            invalid_time = False
            if time.year < now.year:
                invalid_time = True
            elif time.month < now.month:
                invalid_time = True
            elif time.day <= now.day:
                invalid_time = True
            if invalid_time:
                return Response({"detail": "无效时间！"}, status=status.HTTP_400_BAD_REQUEST)

            if ReportTask.objects.filter(
                    user=request.user,
                    time__year=time.year,
                    time__month=time.month,
                    time__day=time.day,
            ).count() != 0 :
                return Response({"detail": "已经存在同样的任务！"}, status=status.HTTP_400_BAD_REQUEST)

            ReportTask.objects.create(
                user=request.user,
                time=time,
                status="Waiting"
            ).save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class ReportTaskDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified, IsOwner, )
    queryset = ReportTask.objects.all()
    serializer_class = ReportTaskSerialize


class ReportPinganUserRateThrottle(UserRateThrottle):
    THROTTLE_RATES = {"user": "2/min"}


class ReportNowView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified, )
    throttle_classes = [ReportPinganUserRateThrottle]

    def post(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        try:
            crawler = Crawler()
            crawler.login_one(info.heu_username, info.heu_password)
            crawler.report()
            TaskInfo.objects.create(
                title="立即报备",
                status="Success",
                user=info.user,
            ).save()
            return Response({'detail': '立即报备成功！',}, status=status.HTTP_200_OK)

        except Exception as e:
            TaskInfo.objects.create(
                title="立即报备",
                status="Fail",
                user=info.user,
            ).save()
            return Response({"立即报备失败！"}, status=status.HTTP_400_BAD_REQUEST)


class ReportDailyView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified,)

    def get(self, request):
        return Response({"report_daily": HEUAccountInfo.objects.get_or_create(user=request.user)[0].report_daily},
                        status=status.HTTP_200_OK)

    def post(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        info.report_daily = not info.report_daily
        info.save()
        return Response({"report_daily": info.report_daily}, status=status.HTTP_201_CREATED)

# @ratelimit(key="user_or_ip", rate="30/m", method=ALL)
@cache_page(60*5)
def test_connect(request, name):
    site_dict = {
        "one": "https://cas.hrbeu.edu.cn/cas/login#/",
        "pingjiao": "https://cas.hrbeu.edu.cn/cas/login?service=http://pjcs.hrbeu.edu.cn/login/return?type=mobile#/",
        "cas-443": "https://cas-443.wvpn.hrbeu.edu.cn/cas/login#/",
        "edusys": "https://edusys.wvpn.hrbeu.edu.cn/jsxsd/kscj/cjcx_list",
    }
    if name == "list":
        return JsonResponse(site_dict)
    elif name == "result":
        result = {}
        for key,value in site_dict.items():
            result[key] = requests.get(url=value).ok
        return JsonResponse({"result": result})
    else:
        raise Http404("No such site")


class ArticleView(generics.ListAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerialize


class PinganView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified,)

    def get(self, request):
        return Response({"pingan_daily": HEUAccountInfo.objects.get_or_create(user=request.user)[0].pingan_daily},
                        status=status.HTTP_200_OK)

    def post(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        info.pingan_daily = not info.pingan_daily
        info.save()
        return Response({"pingan_daily": info.pingan_daily}, status=status.HTTP_201_CREATED)


class PinganTasksView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified,)

    def get(self, request):
        return Response([ TaskInfoSerialize(task).data for task in
                          TaskInfo.objects.filter(user=request.user, title="平安行动")],
                        status=status.HTTP_200_OK)


class PinganNowView(APIView):
    permission_classes = (IsAuthenticated, HEUAccountVerified, )
    throttle_classes = [ReportPinganUserRateThrottle]

    def post(self, request):
        info = HEUAccountInfo.objects.get_or_create(user=request.user)[0]
        try:
            crawler = Crawler()
            crawler.login_one(info.heu_username, info.heu_password)
            url = crawler.pingan()
            TaskInfo.objects.create(
                title="平安行动",
                status="Success",
                description=url,
                user=info.user,
                additional_info="立即平安行动"
            ).save()
            return Response({'detail': '提交平安行动成功！',}, status=status.HTTP_200_OK)
        except Exception as e:
            TaskInfo.objects.create(
                title="平安行动",
                status="Fail",
                user=info.user,
                additional_info="立即平安行动提交失败，可能是HEU账号密码错误或是学校服务器出现问题!",
            ).save()
            print(e)
            return Response({"提交平安行动失败！"}, status=status.HTTP_400_BAD_REQUEST)