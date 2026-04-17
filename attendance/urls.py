from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Landing pages
    path('',                                   views.instructor_attendance_home, name='instructor_home'),
    path('mine/',                              views.student_attendance_home,    name='student_home'),

    # Instructor: session management
    path('course/<int:course_id>/',            views.session_list,    name='session_list'),
    path('course/<int:course_id>/create/',     views.create_session,  name='create_session'),
    path('session/<int:session_id>/edit/',     views.edit_session,    name='edit_session'),
    path('session/<int:session_id>/delete/',   views.delete_session,  name='delete_session'),
    path('session/<int:session_id>/mark/',     views.mark_attendance, name='mark_attendance'),

    # Instructor: export
    path('course/<int:course_id>/export/',     views.export_attendance,     name='export_attendance'),
    path('course/<int:course_id>/export-pdf/', views.export_attendance_pdf, name='export_attendance_pdf'),

    # Student: my attendance
    path('course/<int:course_id>/mine/',       views.my_attendance,   name='my_attendance'),
]
