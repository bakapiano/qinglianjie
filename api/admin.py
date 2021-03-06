from django.contrib import admin
from api.models import *


class HEUAccountInfoAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'heu_username',
        "heu_password",
        "report_daily",
        "account_verify_status",
        "fail_last_time",
        "mail_when_grade",
        "qq_me_when_grade",
        'pingan_daily',
    )
    list_filter = ('report_daily', 'account_verify_status', 'fail_last_time', 'mail_when_grade', "qq_me_when_grade", 'pingan_daily')
    fk_fields = ('user',)
    search_fields = ('user__username', "heu_username", "user__email")


class CourseScoreAdmin(admin.ModelAdmin):
    list_display = (
        'heu_username',
        'course',
        "score",
        "term",
    )
    list_filter = ('term',)
    fk_fields = ('course',)
    search_fields = ('heu_username', "course__name", "course__course_id")


class CourseInfoAdmin(admin.ModelAdmin):
    list_display = (
        'course_id',
        'name',
        "assessment_method",
    )
    list_filter = ('assessment_method',)
    search_fields = ('course_id', "name")


class CourseCommentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'course',
        "content",
        "created",
        "anonymous",
    )
    list_filter = ('created', 'anonymous',)
    date_hierarchy = 'created'
    fk_fields = ('user', "course")
    search_fields = ('user__username', "course__name", "course__course_id", "content")


class TimetableQueryResultAdmin(admin.ModelAdmin):
    list_display = (
        'heu_username',
        'created',
        "status",
    )
    list_filter = ('created', 'status',)
    date_hierarchy = 'created'
    search_fields = ('heu_username',)


class ScoreQueryResultResultAdmin(admin.ModelAdmin):
    list_display = (
        'heu_username',
        'created',
        "status",
    )
    list_filter = ('created', 'status',)
    date_hierarchy = 'created'
    search_fields = ('heu_username',)


class RecentGradeCourseAdmin(admin.ModelAdmin):
    list_display = (
        'course',
        'created',
    )
    fk_fields = ('user',)
    list_filter = ('created',)
    date_hierarchy = 'created'
    search_fields = ('course__name', "course__course_id",)


class UserProfilePhotoAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'image',
    )
    fk_fields = ('user',)
    search_fields = ('user__username',)


class TaskInfoAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'status',
        'user',
        'created',
    )

    fk_fields = ('user',)
    list_filter = ('title', 'created', 'status', 'additional_info')
    date_hierarchy = 'created'
    search_fields = ('title', "description", 'user__username')


class CourseStatisticsResultAdmin(admin.ModelAdmin):
    list_display = (
        'course',
    )
    fk_fields = ('course',)
    search_fields = ('course__name', 'course__course_id')


admin.site.register(HEUAccountInfo, HEUAccountInfoAdmin)
admin.site.register(CourseScore, CourseScoreAdmin)
admin.site.register(CourseInfo, CourseInfoAdmin)
admin.site.register(CourseComment, CourseCommentAdmin)
admin.site.register(TimetableQueryResult, TimetableQueryResultAdmin)
admin.site.register(ScoreQueryResult, ScoreQueryResultResultAdmin)
admin.site.register(RecentGradeCourse, RecentGradeCourseAdmin)
admin.site.register(NoticeTask)
admin.site.register(QQBindInfo)
admin.site.register(XKInfo)
admin.site.register(GroupInfo)
admin.site.register(UserProfilePhoto, UserProfilePhotoAdmin)
admin.site.register(CourseStatisticsResult, CourseStatisticsResultAdmin)
admin.site.register(LastRefreshTimeOfSpecialty)
admin.site.register(TaskInfo, TaskInfoAdmin)
admin.site.register(ReportTask)
admin.site.register(LastReportTime)
admin.site.register(Article)
