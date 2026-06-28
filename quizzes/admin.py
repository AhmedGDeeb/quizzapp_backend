from django.contrib import admin
from .models import Quiz, Question, Choice, Answer

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1
    fields = ('choice_text', 'is_correct')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('question_text', 'question_type', 'points', 'order_index')
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'category', 
                    'is_published', 'question_count', 'created_at')
    list_filter = ('is_published', 'category', 'created_at')
    search_fields = ('title', 'description', 'creator__username')
    readonly_fields = ('created_at', 'updated_at', 'question_count', 'total_points')
    inlines = [QuestionInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'creator')
        }),
        ('Quiz Settings', {
            'fields': ('category', 'time_limit', 'attempts_allowed')
        }),
        ('Publishing', {
            'fields': ('is_published',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'question_count', 'total_points')
        }),
    )

    def question_count(self, obj):
        return obj.question_count
    question_count.short_description = 'Questions'

    def total_points(self, obj):
        return obj.total_points
    total_points.short_description = 'Total Points'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'quiz', 'question_type', 'points', 'order_index')
    list_filter = ('question_type', 'quiz')
    search_fields = ('question_text', 'quiz__title')
    inlines = [ChoiceInline]
    fieldsets = (
        (None, {
            'fields': ('quiz', 'question_text', 'question_type', 'points', 'order_index')
        }),
    )


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('choice_text', 'question', 'is_correct')
    list_filter = ('is_correct', 'question__question_type')
    search_fields = ('choice_text', 'question__question_text')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'correct_answer_text_preview')
    search_fields = ('question__question_text', 'correct_answer_text')

    def correct_answer_text_preview(self, obj):
        return obj.correct_answer_text[:50] + '...' if len(obj.correct_answer_text) > 50 else obj.correct_answer_text
    correct_answer_text_preview.short_description = 'Correct Answer'