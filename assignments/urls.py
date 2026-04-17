from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # ── Student ──────────────────────────────────────────────
    path('',                             views.student_assignments,     name='student_assignments'),
    path('submit/<int:assignment_id>/',  views.submit_assignment,       name='submit_assignment'),
    path('my-submissions/',              views.my_submissions,          name='my_submissions'),

    # ── Instructor: Assignment Management ────────────────────
    path('manage/',                      views.instructor_assignments,  name='instructor_assignments'),
    path('create/',                      views.create_assignment,       name='create_assignment'),
    path('edit/<int:assignment_id>/',    views.edit_assignment,         name='edit_assignment'),
    path('delete/<int:assignment_id>/',  views.delete_assignment,       name='delete_assignment'),

    # ── Instructor: Submissions Dashboard ────────────────────
    path('dashboard/',                   views.instructor_dashboard,    name='instructor_dashboard'),

    # ── AJAX ─────────────────────────────────────────────────
    path('ajax/update-status/',                    views.update_submission_status, name='update_submission_status'),
    path('ajax/grade/<int:submission_id>/',        views.grade_submission,         name='grade_submission'),
]
