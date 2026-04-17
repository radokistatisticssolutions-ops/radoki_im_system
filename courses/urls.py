from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # ── Public ───────────────────────────────────────────────────────────────
    path('', views.course_list, name='course_list'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    path('<int:pk>/enroll/', views.enroll_course, name='enroll_course'),

    # ── Student: My Courses filtered views ───────────────────────────────────
    path('my/enrolled/', views.student_enrolled_courses, name='student_enrolled'),
    path('my/pending/', views.student_pending_courses, name='student_pending'),
    path('my/paid/', views.student_paid_courses, name='student_paid'),
    path('my/completed/', views.student_completed_courses, name='student_completed'),

    # ── Instructor: Course CRUD ───────────────────────────────────────────────
    path('instructor/', views.instructor_courses, name='instructor_courses'),
    path('instructor/students/', views.instructor_students, name='instructor_students'),
    path('instructor/<int:course_id>/students/', views.course_students, name='course_students'),
    path('instructor/analytics/', views.analytics_overview, name='analytics_overview'),
    path('instructor/sessions/', views.instructor_live_sessions, name='instructor_live_sessions'),
    path('instructor/create/', views.create_course, name='create_course'),
    path('instructor/<int:pk>/edit/', views.edit_course, name='edit_course'),
    path('instructor/<int:pk>/delete/', views.delete_course, name='delete_course'),

    # ── Instructor: Resources ────────────────────────────────────────────────
    path('<int:course_id>/upload-resource/', views.upload_resource, name='upload_resource'),
    path('instructor/<int:course_id>/resources/', views.instructor_resource_view, name='instructor_resource_view'),
    path('resource/<int:resource_id>/delete/', views.delete_resource, name='delete_resource'),
    path('resource/<int:resource_id>/preview/', views.preview_resource, name='preview_resource'),
    path('resource/<int:resource_id>/download/', views.download_resource, name='download_resource'),
    path('resource/<int:resource_id>/toggle-download/', views.toggle_resource_download, name='toggle_resource_download'),
    path('resource/<int:resource_id>/serve/', views.serve_file, name='serve_file'),

    # ── Modules ──────────────────────────────────────────────────────────────
    path('<int:course_id>/modules/', views.module_manager, name='module_manager'),
    path('<int:course_id>/modules/create/', views.create_module, name='create_module'),
    path('modules/<int:module_id>/edit/', views.edit_module, name='edit_module'),
    path('modules/<int:module_id>/delete/', views.delete_module, name='delete_module'),
    path('modules/reorder/', views.reorder_modules, name='reorder_modules'),    # AJAX

    # ── Live Sessions ────────────────────────────────────────────────────────
    path('<int:course_id>/sessions/add/', views.add_session, name='add_session'),
    path('sessions/<int:session_id>/edit/', views.edit_session, name='edit_session'),
    path('sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),

    # ── Coupons ──────────────────────────────────────────────────────────────
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.create_coupon, name='create_coupon'),
    path('coupons/<int:coupon_id>/edit/', views.edit_coupon, name='edit_coupon'),
    path('coupons/<int:coupon_id>/delete/', views.delete_coupon, name='delete_coupon'),

    # ── Lessons ──────────────────────────────────────────────────────────────
    path('modules/<int:module_id>/lessons/create/', views.create_lesson, name='create_lesson'),
    path('lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lessons/<int:lesson_id>/edit/', views.edit_lesson, name='edit_lesson'),
    path('lessons/<int:lesson_id>/delete/', views.delete_lesson, name='delete_lesson'),
    path('lessons/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),  # AJAX
    path('lessons/<int:lesson_id>/download-resource/', views.download_lesson_resource, name='download_lesson_resource'),
    path('lessons/reorder/', views.reorder_lessons, name='reorder_lessons'),    # AJAX

    # ── Enrollment / Completion / Certificate ────────────────────────────────
    path('enrollment/<int:enrollment_id>/', views.enrollment_detail, name='enrollment_detail'),
    path('enrollment/<int:enrollment_id>/complete/', views.mark_course_complete, name='mark_complete'),
    path('enrollment/<int:enrollment_id>/certificate/', views.generate_certificate, name='generate_certificate'),
    path('enrollment/<int:enrollment_id>/certificate/download/', views.download_certificate, name='download_certificate'),

    # ── Student API ──────────────────────────────────────────────────────────
    path('api/student-courses/', views.get_student_courses, name='get_student_courses'),
    path('api/my-courses/', views.get_student_courses, name='my_courses'),
    path('api/validate-coupon/', views.validate_coupon_api, name='validate_coupon'),

    # ── Time tracking ─────────────────────────────────────────────────────────
    path('lessons/<int:lesson_id>/log-time/', views.log_lesson_time, name='log_lesson_time'),  # AJAX

    # ── Progress & Analytics ──────────────────────────────────────────────────
    path('<int:course_id>/progress/', views.course_progress, name='course_progress'),
    path('<int:course_id>/analytics/', views.instructor_analytics, name='instructor_analytics'),
]
