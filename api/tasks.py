from __future__ import absolute_import, unicode_literals
from celery import shared_task
from lib.heu import Crawler
from api.models import *
from django.utils import timezone
from django.core.mail import send_mail
from qinglianjie.settings import EMAIL_FROM
from django.db import transaction
import os, json, django
import multiprocessing
from api.api_views import get_statistics_result

lock = multiprocessing.Lock()


@shared_task
def query_scores(id, task_info_id):
    django.setup()
    info = HEUAccountInfo.objects.get(id=id)
    try:
        crawler = Crawler()
        crawler.login(info.heu_username, info.heu_password)
        res = ScoreQueryResult.objects.get_or_create(heu_username=info.heu_username)[0]

        try:
            pre = len(json.loads(res.result))
        except Exception as e:
            pre = 0

        res.result = json.dumps(crawler.getScores())
        cur = len(json.loads(res.result))

        # 出分
        if cur != pre:
            print(cur,pre)
            for info in HEUAccountInfo.objects.filter(heu_username=info.heu_username):
                do_collect_scores.delay(info.id)

        res.status = "Success"
        res.fail = False
        res.created = timezone.now()
        res.save()

        TaskInfo.objects.filter(id=task_info_id).update(
            title="刷新我的成绩",
            status="Success",
            user=info.user,
        )
        return "Success"

    except Exception as e:
        res = ScoreQueryResult.objects.get_or_create(heu_username=info.heu_username)[0]
        res.status = "Fail"
        res.fail = True
        res.created = timezone.now()
        res.save()

        TaskInfo.objects.filter(id=task_info_id).update(
            title="刷新我的成绩",
            status="Fail",
            user=info.user,
            additional_info="刷新成绩失败，可能是HEU账号密码错误或是学校服务器出现问题!",
            exception=str(e),
        )
        return "Fail"


@shared_task
def query_time_table(id, term:str, task_info_id):
    django.setup()
    info = HEUAccountInfo.objects.get(id=id)
    try:
        crawler = Crawler()
        crawler.login(info.heu_username, info.heu_password)
        res = TimetableQueryResult.objects.get_or_create(heu_username=info.heu_username)[0]
        res.result = json.dumps(crawler.getTermTimetable(term))
        res.status = "Success"
        res.fail = False
        res.created = timezone.now()
        res.save()

        TaskInfo.objects.filter(id=task_info_id).update(
            title="刷新我的课表",
            description="%s 学期" % term,
            status="Success",
            user=info.user,
        )

    except Exception as e:
        res = TimetableQueryResult.objects.get_or_create(heu_username=info.heu_username)[0]
        res.status = "Fail"
        res.fail = True
        res.created = timezone.now()
        res.save()
        print(e)

        TaskInfo.objects.filter(id=task_info_id).update(
            title="刷新我的课表",
            description="%s 学期" % term,
            status="Fail",
            user=info.user,
            additional_info="刷新课表失败，可能是HEU账号密码错误或是学校服务器出现问题!",
            exception=str(e),
        )
        return "Fail"

    return "Success"


@shared_task
def report_daily():
    django.setup()
    for info in HEUAccountInfo.objects.filter(report_daily=True, account_verify_status=True):
        print(HEUAccountInfo.heu_username)
        do_report.delay(info.id, "每日自动报备")
    now = timezone.now()
    for task in ReportTask.objects.filter(
        time__year=now.year,
        time__month=now.month,
        time__day=now.day,
        status="Waiting",
    ):
        info = HEUAccountInfo.objects.get_or_create(user=task.user)
        do_report.delay(info.id, "定时报备任务", task.id)
    return "Done"


@shared_task
def do_report(id, task_title, report_task_id = None):
    info = HEUAccountInfo.objects.get_or_create(id=id)[0]
    try:
        crawler = Crawler()
        crawler.login_one(info.heu_username, info.heu_password)
        crawler.report()

        TaskInfo.objects.create(
            title=task_title,
            status="Success",
            user=info.user,
        ).save()

        if report_task_id != None:
            task = ReportTask.objects.get(id=report_task_id)
            task.status = "Success"
            task.save()

        return "Success"

    except Exception as e:
        TaskInfo.objects.create(
            title=task_title,
            status="Fail",
            user=info.user,
            exception=str(e),
            additional_info="报备失败，可能是HEU账号密码错误或是学校服务器出现问题!",
        ).save()

        if report_task_id != None:
            task = ReportTask.objects.get(id=report_task_id)
            task.status = "Fail"
            task.save()

        return str(e)


def check_specialty_grade_courses(specialty:str):
    last, created = LastRefreshTimeOfSpecialty.objects.get_or_create(specialty=specialty)
    if created or (timezone.now()-last.created).total_seconds() >= 60*30:
        last.created = timezone.now()
        last.save()
        for info in HEUAccountInfo.objects.filter(heu_username__startswith=specialty):
            print(info.id)
            do_collect_scores.delay(info.id, True)
        return "Successfully create refresh tasks for specialty %s" % specialty

    last.save()
    return "Refresh interval to short."


@shared_task
def do_collect_scores(id, not_check_specialty:bool = False):
    django.setup()
    info = HEUAccountInfo.objects.get(id=id)

    # 获取成绩
    try:
        crawler = Crawler()
        crawler.login(info.heu_username, info.heu_password)
        scores = crawler.getScores()
        TaskInfo.objects.create(
            title="清廉街后台收集分数",
            status="Success",
            user=info.user,
        ).save()
    except Exception as e:
        info.fail_last_time = True
        info.save()
        TaskInfo.objects.create(
            title="清廉街后台收集分数",
            status="Fail",
            user=info.user,
            exception=str(e),
            additional_info="清廉街后台收集分数失败，可能是HEU账号密码错误或是学校服务器出现问题!",
        ).save()
        return "Fail"

    # 处理成绩记录
    try:
        lock.acquire()
        for record in scores:
            with transaction.atomic():
                print(record)
                course_id = record[2]
                name = record[3]
                credit = record[5]
                total_time = record[6]
                assessment_method = record[7]
                course_kind = record[8]
                attributes = record[9]
                kind = record[10]
                general_category = record[11]

                course, created = CourseInfo.objects.get_or_create(
                    course_id=course_id
                )

                if created:
                    course.name = name
                    course.credit = credit
                    course.total_time = total_time
                    course.assessment_method = assessment_method
                    course.attributes = attributes
                    course.kind = kind
                    course.general_category = general_category
                    course.save()

                # course = CourseInfo.objects.get(course_id=course_id)
                # print(heu_username, course_id)

                if record[4] != "---" and course_kind == "正常考试":
                    obj, created = CourseScore.objects.get_or_create(
                        course=course,
                        heu_username=info.heu_username,
                        score=record[4],
                        term=record[1],
                    )
                    obj.save()

                    if (not info.fail_last_time) and created:
                        recent = RecentGradeCourse.objects.filter(course=course)
                        flag = True
                        if len(recent) >= 1:
                            delta = timezone.now() - recent[0].created
                            if delta.total_seconds() <= 60 * 60 * 24:
                                flag = False
                        if flag:
                            RecentGradeCourse.objects.create(course=course).save()

                        # 检查系内出分情况
                        if not not_check_specialty:
                            check_specialty_grade_courses(info.heu_username[:5])

                        content = \
                            '课程 %s 出分啦！' % record[3] + \
                            '你的分数是 %s，欢迎到清廉街发表课程评论。\n' % str(record[4]) + \
                            '如果你不想再收到出分提醒，可以在个人主页里关闭该功能。\n' + \
                            'Qinglianjie'

                        # 出分时qq提醒我！
                        if info.qq_me_when_grade:
                            try:
                                print(content)
                                qq_id = QQBindInfo.objects.get(user=info.user).qq_id
                                NoticeTask.objects.get_or_create(
                                    qq_id=qq_id,
                                    content=content
                                )[0].save()
                            except Exception as e:
                                print(e)
                                pass

        if info.fail_last_time:
            info.fail_last_time = False
            info.save()

    finally:
        lock.release()

    return "Success"


@shared_task
def collect_course_statistics_result():
    try:
        lock.acquire()
        for course in CourseInfo.objects.all():
            print(course)
            obj = CourseStatisticsResult.objects.get_or_create(course=course)[0]
            obj.result = json.dumps(get_statistics_result(course.course_id))
            obj.save()
    finally:
        lock.release()
    return "Done"

@shared_task
def collect_scores():
    django.setup()
    for info in HEUAccountInfo.objects.filter(account_verify_status=True):
        do_collect_scores.delay(info.id, True)
    return "Success"


#统计学过某课程的人数
@shared_task
def count_courses():
    django.setup()
    for course in CourseInfo.objects.all():
        course.count = CourseScore.objects.filter(course=course).count()
        course.save()
    return "Success"


@shared_task
def get_xk_info():
    django.setup()
    XKInfo.objects.all().delete()
    for info in HEUAccountInfo.objects.filter(account_verify_status=True):
        heu_username = info.heu_username
        try:
            crawler = Crawler()
            crawler.login(info.heu_username, info.heu_password)
            result = crawler.getXKInfo()
        except Exception as e:
            continue
        for record in result:
            obj, created = XKInfo.objects.get_or_create(
                term=record[0],
                title=record[1],
                time=record[2],
            )

            if created:
                obj.save()

                for group in GroupInfo.objects.filter(notice_when_xk=True):
                    NoticeTask.objects.create(
                        qq_id = group.group_id,
                        content = \
                        '%s 已经开始，' % record[1] + \
                        '时间为 %s\n' % record[2] + \
                        "请注意及时选课！",
                        type = "Group",
                    ).save()

                for user in QQBindInfo.objects.filter(notice_when_xk=True):
                    NoticeTask.objects.create(
                        qq_id=user.qq_id,
                        content= \
                            '%s 已经开始，' % record[1] + \
                            '时间为 %s\n' % record[2] + \
                            "请注意及时选课！",
                        type="QQ",  
                    ).save()
        break
    return "Done"


@shared_task
def pingan_daily():
    django.setup()
    for info in HEUAccountInfo.objects.filter(pingan_daily=True, account_verify_status=True):
        print(HEUAccountInfo.heu_username)
        do_pingan.delay(info.id, "平安行动")
    return "Done"


DEFAULT_RETRY_TIMES = 3
@shared_task
def do_pingan(id, task_title, retry_times=DEFAULT_RETRY_TIMES):
    info = HEUAccountInfo.objects.get_or_create(id=id)[0]
    try:
        crawler = Crawler()
        crawler.login_one(info.heu_username, info.heu_password)
        url = crawler.pingan()

        TaskInfo.objects.create(
            title=task_title,
            status="Success",
            description=url,
            additional_info="每日自动平安行动",
            user=info.user,
        ).save()
        return "Success"

    except Exception as e:
        if retry_times == 0:
            TaskInfo.objects.create(
                title=task_title,
                status="Fail",
                user=info.user,
                exception=str(e),
                additional_info="每日自动平安行动尝试%d次后失败，可能是HEU账号密码错误或是学校服务器出现问题!" % DEFAULT_RETRY_TIMES,
            ).save()
            return str(e)
        else:
            do_pingan.delay(id, task_title, retry_times-1)
