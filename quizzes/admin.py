from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import Quiz, Question, AnswerOption, QuizAttempt, StudentAnswer
from core.admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class PublishedFilter(SimpleListFilter):
    title = 'Publication Status'
    parameter_name = 'is_published'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Published'),
            ('false', 'Draft'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_published=True)
        if self.value() == 'false':
            return queryset.filter(is_published=False)
        return queryset


class PassRequiredFilter(SimpleListFilter):
    title = 'Pass Required'
    parameter_name = 'require_pass_for_completion'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Yes'),
            ('false', 'No'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(require_pass_for_completion=True)
        if self.value() == 'false':
            return queryset.filter(require_pass_for_completion=False)
        return queryset


class QuizCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        from courses.models import Course
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class QuestionTypeFilter(SimpleListFilter):
    title = 'Question Type'
    parameter_name = 'question_type'

    def lookups(self, request, model_admin):
        choices = Question._meta.get_field('question_type').choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(question_type=self.value())
        return queryset


class QuestionQuizFilter(SimpleListFilter):
    title = 'Quiz'
    parameter_name = 'quiz'

    def lookups(self, request, model_admin):
        quizzes = Quiz.objects.all().values_list('id', 'title')
        return [(quiz_id, title) for quiz_id, title in quizzes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(quiz_id=self.value())
        return queryset


class PassedFilter(SimpleListFilter):
    title = 'Result'
    parameter_name = 'passed'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Passed'),
            ('false', 'Failed'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(passed=True)
        if self.value() == 'false':
            return queryset.filter(passed=False)
        return queryset


class CompleteFilter(SimpleListFilter):
    title = 'Completion Status'
    parameter_name = 'is_complete'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Completed'),
            ('false', 'In Progress'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_complete=True)
        if self.value() == 'false':
            return queryset.filter(is_complete=False)
        return queryset


class AttemptQuizFilter(SimpleListFilter):
    title = 'Quiz'
    parameter_name = 'quiz'

    def lookups(self, request, model_admin):
        quizzes = Quiz.objects.all().values_list('id', 'title')
        return [(quiz_id, title) for quiz_id, title in quizzes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(quiz_id=self.value())
        return queryset


class CorrectAnswerFilter(SimpleListFilter):
    title = 'Answer Correctness'
    parameter_name = 'is_correct'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Correct'),
            ('false', 'Incorrect'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_correct=True)
        if self.value() == 'false':
            return queryset.filter(is_correct=False)
        return queryset


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4
    fields = ['text', 'is_correct', 'order']


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    fields = ['text', 'question_type', 'marks', 'order', 'explanation']


@admin.register(Quiz)
class QuizAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = [
        'title', 'course', 'pass_mark', 'question_count',
        'is_published', 'require_pass_for_completion', 'created_at'
    ]
    list_filter = [PublishedFilter, PassRequiredFilter, QuizCourseFilter]
    search_fields = ['title', 'course__title']
    inlines = [QuestionInline]

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['text', 'quiz', 'question_type', 'marks', 'order']
    list_filter = [QuestionTypeFilter, QuestionQuizFilter]
    search_fields = ['text', 'quiz__title']
    inlines = [AnswerOptionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['student', 'quiz', 'score', 'passed', 'is_complete', 'started_at']
    list_filter = [PassedFilter, CompleteFilter, AttemptQuizFilter]
    search_fields = ['student__username', 'quiz__title']
    readonly_fields = ['started_at', 'completed_at']


@admin.register(StudentAnswer)
class StudentAnswerAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['attempt', 'question', 'is_correct', 'marks_awarded']
    list_filter = [CorrectAnswerFilter]
    search_fields = ['attempt__student__username']
