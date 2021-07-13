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

lock = multiprocessing.Lock()


@shared_task
def query_scores(username:str, password:str):
    django.setup()
    # ScoreQueryResult.objects.filter(heu_username=username).delete()
    try:
        crawler = Crawler()
        crawler.login(username, password)
        res = ScoreQueryResult.objects.get_or_create(heu_username=username)[0]
        res.result = json.dumps(crawler.getScores())
        res.status = "Success"
        res.fail = False
        res.created = timezone.now()
        res.save()
    except Exception as e:
        res = ScoreQueryResult.objects.get_or_create(heu_username=username)[0]
        res.status = "Fail"
        res.fail = True
        res.created = timezone.now()
        res.save()
        print(e)
        return "Fail"
    return "Success"


@shared_task
def query_time_table(username:str, password:str, term:str):
    django.setup()
    # TimetableQueryResult.objects.filter(heu_username=username).delete()
    try:
        crawler = Crawler()
        crawler.login(username, password)
        res = TimetableQueryResult.objects.get_or_create(heu_username=username)[0]
        res.result = json.dumps(crawler.getTermTimetable(term))
        res.status = "Success"
        res.fail = False
        res.created = timezone.now()
        res.save()
    except Exception as e:
        res = TimetableQueryResult.objects.get_or_create(heu_username=username)[0]
        res.status = "Fail"
        res.fail = True
        res.created = timezone.now()
        res.save()
        print(e)
        return "Fail"

    return "Success"


@shared_task
def report_daily():
    django.setup()
    for info in HEUAccountInfo.objects.filter(report_daily=True, account_verify_status=True):
        print(HEUAccountInfo.heu_username)
        do_report.delay(info.heu_username, info.heu_password)
    return "Done"


@shared_task
def do_report(username:str, password:str):
    try:
        crawler = Crawler()
        crawler.login_one(username, password)
        crawler.report()
        return "Success"
    except Exception as e:
        return str(e)


@shared_task
def do_collect_scores(id):
    django.setup()
    info = HEUAccountInfo.objects.get(id=id)

    # 获取成绩
    try:
        crawler = Crawler()
        crawler.login(info.heu_username, info.heu_password)
        scores = crawler.getScores()
    except Exception as e:
        info.fail_last_time = True
        info.save()
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
def collect_scores():
    django.setup()
    for info in HEUAccountInfo.objects.filter(account_verify_status=True):
        do_collect_scores.delay(info.id)
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
                term = record[0],
                title = record[1],
                time = record[2],
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