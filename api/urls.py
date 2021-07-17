from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views, api_views, bot_view

urlpatterns = [
    path('query/scores', views.query_scores, name="query_scores"),
    path('refresh/scores', views.refresh_scores, name="refresh_scores"),
    path('query/timetable', views.query_time_table, name="query_time_table"),
    path('refresh/timetable', views.refresh_time_table, name="refresh_time_table"),

    #测试用
    path('report', views.test_auto_report, name="test_auto_report"),
    path('collect/scores', views.test_collect_scores, name="test_collect_scores"),
    path('collect/xkinfo', views.test_collect_xk_info, name="test_collect_xk_info"),

    path('query/course_scores', views.query_course_scores, name="query_course_scores"),
    path('query/courses', views.query_course_info, name="query_courses"),
    #path('heu/update', views.update_heu_accounts, name="update_heu_accounts"),
    #path('heu/remove', views.remove_heu_accounts, name="remove_heu_accounts"),

    path('course/comment', views.CourseCommentView.as_view(), name="course_comment"),
    path('course/count', views.course_count, name="course_count"),
    path('course/comment/my', views.query_my_comment, name="query_my_comment"),
    path('course/comment/remove', views.remove_my_comment, name="remove_my_comment"),
    path('course/recent', views.recent_grade_course, name="recent_grade_course"),

    path('pingjiao', views.pingjiao, name="query_pingjiao"),
    path('pingjiao/do', views.do_pingjiao, name="do_pingjiao"),

    path('grade/notify', login_required(views.MailWhenGradeView.as_view()),
                                        name="grade_notify"),

    path('HEUAccount', api_views.HEUAccountView.as_view(), name="HEUAccount"),
    path('my/timetable', api_views.MyTimeTableView.as_view(), name="my_timetable"),
    path('my/scores', api_views.MyScoresView.as_view(), name="my_scores"),

    path('my/qq',api_views.BindQQView.as_view()),

    path('bot/notice/task', bot_view.NoticeTaskList.as_view()),
    path('bot/notice/task/<int:pk>', bot_view.NoticeTaskRetrieveDestroy.as_view()),

    path('bot/group', bot_view.GroupInfoListCreate.as_view()),
    path('bot/group/<int:group_id>', bot_view.GroupInfoRetrieveUpdate.as_view()),

    # 用户信息
    path('user',api_views.CurrentUserInfoView.as_view()),
    path('user/<str:username>', api_views.UserInfoView.as_view()),

    # 首页最近评论
    path('recent/comments', api_views.RecentCommentView.as_view()),

    # 首页今日出分
    path('recent/grade/courses', api_views.RecentGradeCourseView.as_view()),
    
    # 头像上传
    path('user/profile/photo', api_views.UserProfilePhotoView.as_view()),

    # 课程信息
    path('course/<str:course_id>', api_views.CourseInfoView.as_view()),
    path('course/<str:course_id>/comments', api_views.CourseCommentView.as_view(), name="api_course_comment"),
    path('course/<str:course_id>/statistics', api_views.CourseStatisticsView.as_view()),

    # 课程列表
    path('courses', api_views.CoursesView.as_view()),
]
