from django.db import models
from django.contrib.auth import settings
from django.utils import timezone
from mdeditor.fields import MDTextField
import json, os


class HEUAccountInfo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    heu_username = models.CharField(max_length=100)
    heu_password = models.CharField(max_length=100)
    account_verify_status = models.BooleanField(default=False)

    report_daily = models.BooleanField(default=False)
    fail_last_time = models.BooleanField(default=True)

    mail_when_grade = models.BooleanField(default=False)

    qq_me_when_grade = models.BooleanField(default=False)

    pingan_daily = models.BooleanField(default=False)

    def __str__(self):
        return " ".join([str(self.user), self.heu_username])


class CourseInfo(models.Model):
    #课程编号
    course_id = models.CharField(max_length=20, unique=True)
    #课程名称
    name = models.CharField(max_length=100)
    #学分
    credit = models.CharField(max_length=20)
    #总学时
    total_time = models.CharField(max_length=20)
    #考察方式 考查 考试
    assessment_method = models.CharField(max_length=100)
    #课程属性 必修 选修
    attributes = models.CharField(max_length=100)
    #课程性质
    kind = models.CharField(max_length=100)
    #通识类别
    general_category = models.CharField(max_length=100)
    #参与统计人数
    count = models.IntegerField(default=0)

    class Meta:
        ordering = ('-count',)

    def __str__(self):
        return " ".join([str(self.course_id),self.name])


class CourseScore(models.Model):
    heu_username = models.CharField(max_length=100)
    course = models.ForeignKey(CourseInfo, on_delete=models.CASCADE)
    score = models.CharField(max_length=20)
    term = models.CharField(max_length=50)

    def __str__(self):
        return " ".join([self.heu_username,str(self.course),self.score])


#课程评论
class CourseComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(CourseInfo, on_delete=models.CASCADE)
    content = models.TextField(max_length=100)
    created = models.DateTimeField(default=timezone.now)
    anonymous = models.BooleanField(default=False)

    # 展示成绩
    show = models.BooleanField(default=False)
    score = models.CharField(max_length=20, default="", blank=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return " ".join([str(self.user), str(self.course)])


STATUS_CHOICES = (('Fail', 'Fail'), ('Pending', 'Pending'), ('Success', 'Success'), ('Never', 'Never'))

class ScoreQueryResult(models.Model):
    heu_username = models.CharField(max_length=100)
    result = models.TextField(default="")
    created = models.DateTimeField(default=timezone.now)
    fail = models.BooleanField(default=False)

    # 状态 {'Success', 'Fail', 'Pending'}
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")


    def set_result(self, value):
        self.result = json.jumps(value)

    def get_result(self):
        return json.loads(self.result)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return " ".join([str(self.heu_username), str(self.created), str(self.fail)])


class TimetableQueryResult(models.Model):
    heu_username = models.CharField(max_length=100)
    result = models.TextField(default="")
    created = models.DateTimeField(default=timezone.now)
    fail = models.BooleanField(default=False)

    # 状态 {'Success', 'Fail', 'Pending'}
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    def set_result(self, value):
        self.result = json.dumps(value)

    def get_result(self):
        return json.loads(self.result)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return " ".join([str(self.heu_username), str(self.created), str(self.fail)])


class RecentGradeCourse(models.Model):
    course = models.ForeignKey(CourseInfo, on_delete=models.CASCADE)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return " ".join([str(self.course), str(self.created)])


class QQBindInfo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    qq_id = models.BigIntegerField(default=0)

    # 选课开始时提醒我
    notice_when_xk = models.BooleanField(default=False)
    def __str__(self):
        return " ".join([str(self.user), str(self.qq_id)])


NOTICE_TYPES = (('QQ', 'QQ'), ('Group', 'Group'))


class NoticeTask(models.Model):
    qq_id = models.BigIntegerField(default=0)
    content = models.TextField()
    type = models.CharField(max_length=10, choices=NOTICE_TYPES, default="QQ")

    def __str__(self):
        return " ".join([str(self.qq_id), str(self.content), str(self.type)])


class XKInfo(models.Model):
    term = models.CharField(max_length=20)
    title = models.CharField(max_length=100)
    time = models.CharField(max_length=100)

    def __str__(self):
        return " ".join([str(self.term), str(self.title), str(self.time)])


class GroupInfo(models.Model):
    group_id = models.BigIntegerField(default=0)
    #选课开始时提醒群
    notice_when_xk = models.BooleanField(default=False)

    def __str__(self):
        return " ".join((str(self.group_id), self.notice_when_xk))


def user_directory_path(instance, filename):
    ext = filename.split('.').pop()
    name = filename.split('.')[-2]
    filename = '{0}_{1}.{2}'.format(instance.user.username, name, ext)
    return os.path.join("profile", "photo", filename)


class UserProfilePhoto(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(
        os.path.join("profile", "photo"),
        upload_to=user_directory_path,
        null=True,
    )

    def __str__(self):
        return str(self.user)


class CourseStatisticsResult(models.Model):
    course = models.ForeignKey(CourseInfo, on_delete=models.CASCADE)
    result = models.TextField(default="")

    def __str__(self):
        return str(self.course)


class LastRefreshTimeOfSpecialty(models.Model):
    specialty = models.CharField(max_length=20)
    created = models.DateTimeField(default=timezone.now)


# 后台任务信息
class TaskInfo(models.Model):
    title = models.CharField(max_length=20)
    description = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    additional_info = models.CharField(max_length=100, default="", blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(default=timezone.now)
    exception = models.TextField(default="", blank=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return " ".join((str(self.title), str(self.status), str(self.user), str(self.created)))




REPORT_TASK_STATUS_CHOICES = (('Waiting', 'Waiting'), ('Fail', 'Fail'), ('Success', 'Success'))


class ReportTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=REPORT_TASK_STATUS_CHOICES, default="Waiting")

    class Meta:
        ordering = ('-time',)

    def __str__(self):
        return " ".join((str(self.user), str(self.time), str(self.status),))


class LastReportTime(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-time',)


class Article(models.Model):
    title = models.CharField(max_length=100)
    body = MDTextField()
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return self.title