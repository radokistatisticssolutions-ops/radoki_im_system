from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    # ── Instructor ────────────────────────────────────────────────────────────
    path('course/<int:course_id>/', views.quiz_list, name='quiz_list'),
    path('course/<int:course_id>/create/', views.create_quiz, name='create_quiz'),
    path('<int:quiz_id>/edit/', views.edit_quiz, name='edit_quiz'),
    path('<int:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),

    # ── Question Manager ─────────────────────────────────────────────────────
    path('<int:quiz_id>/questions/', views.question_manager, name='question_manager'),
    path('<int:quiz_id>/questions/save/', views.save_question, name='save_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),

    # ── Attempts / Grading ───────────────────────────────────────────────────
    path('<int:quiz_id>/attempts/', views.quiz_attempts, name='quiz_attempts'),
    path('answers/<int:answer_id>/grade/', views.grade_short_answer, name='grade_short_answer'),

    # ── Student ──────────────────────────────────────────────────────────────
    path('my-results/', views.my_quiz_results, name='my_quiz_results'),
    path('<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
]
