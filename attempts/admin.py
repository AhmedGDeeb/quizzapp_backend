from django.contrib import admin
from django.utils.html import format_html
from .models import QuizAttempt, UserAnswer


class UserAnswerInline(admin.TabularInline):
    """Show answers inside attempt detail"""
    model = UserAnswer
    extra = 0
    fields = ('question', 'selected_choice', 'text_answer', 'is_correct')
    readonly_fields = ('question',)
    can_delete = False
    max_num = 0


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    """Admin for QuizAttempt model"""
    
    list_display = (
        'id',
        'user',
        'quiz',
        'score_display',
        'status_display',
        'start_time',
        'end_time',
    )
    
    list_filter = (
        'status',
        'quiz__category',
        'start_time',
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'quiz__title',
    )
    
    readonly_fields = (
        'id',
        'start_time',
        'end_time',
        'score',
        'status',
    )
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'quiz')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time')
        }),
        ('Performance', {
            'fields': ('score', 'status')
        }),
    )
    
    inlines = [UserAnswerInline]
    
    actions = ['mark_completed', 'reset_attempt']
    
    def score_display(self, obj):
        """Show score with color"""
        if obj.score:
            color = '#28a745' if obj.score >= 70 else '#ffc107' if obj.score >= 50 else '#dc3545'
            return format_html(
                '<span style="font-weight: bold; color: {};">{}%</span>',
                color,
                round(obj.score, 1)
            )
        return format_html('<span>-</span>')
    score_display.short_description = 'Score'
    
    def status_display(self, obj):
        """Show status with badge"""
        colors = {
            'in_progress': '#17a2b8',
            'completed': '#28a745',
            'abandoned': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        status_text = obj.status.replace('_', ' ').title()
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            status_text
        )
    status_display.short_description = 'Status'
    
    def mark_completed(self, request, queryset):
        """Mark attempts as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} attempt(s) marked as completed.')
    mark_completed.short_description = 'Mark as completed'
    
    def reset_attempt(self, request, queryset):
        """Reset attempts"""
        for attempt in queryset:
            attempt.answers.all().delete()
            attempt.score = 0
            attempt.status = 'in_progress'
            attempt.end_time = None
            attempt.save()
        self.message_user(request, f'{queryset.count()} attempt(s) reset.')
    reset_attempt.short_description = 'Reset attempts'


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    """Admin for UserAnswer model"""
    
    list_display = (
        'id',
        'attempt',
        'question_preview',
        'answer_preview',
        'is_correct_display',
        'answered_at',
    )
    
    list_filter = (
        'is_correct',
        'attempt__quiz',
    )
    
    search_fields = (
        'question__question_text',
        'text_answer',
        'attempt__user__username',
    )
    
    readonly_fields = (
        'attempt',
        'question',
        'selected_choice',
        'text_answer',
        'is_correct',
        'answered_at',
    )
    
    def question_preview(self, obj):
        """Question preview"""
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_preview.short_description = 'Question'
    
    def answer_preview(self, obj):
        """Answer preview"""
        if obj.selected_choice:
            return obj.selected_choice.choice_text
        elif obj.text_answer:
            return obj.text_answer[:50]
        return '-'
    answer_preview.short_description = 'Answer'
    
    def is_correct_display(self, obj):
        """Show correct/incorrect"""
        if obj.is_correct:
            return format_html('<span style="color: #28a745;">✅ Correct</span>')
        elif obj.is_correct is False:
            return format_html('<span style="color: #dc3545;">❌ Incorrect</span>')
        return '-'
    is_correct_display.short_description = 'Result'