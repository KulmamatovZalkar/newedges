from django.contrib import admin
from django.utils.html import format_html
from .models import Question, UserProfile, UserResponse, StaffApplication, BotSettings


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """Админка для настроек бота (singleton)."""
    
    list_display = ['__str__', 'bot_name', 'is_active', 'updated_at']
    
    fieldsets = (
        ('Telegram', {
            'fields': ('bot_token', 'bot_name', 'is_active')
        }),
        ('Внешний вид', {
            'fields': ('welcome_image',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not BotSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['order', 'short_text', 'question_type', 'field_name', 'is_required', 'is_active']
    list_display_links = ['short_text']
    list_editable = ['order', 'is_active']
    list_filter = ['question_type', 'is_active', 'is_required']
    search_fields = ['text', 'field_name']
    ordering = ['order']
    
    fieldsets = (
        ('Основное', {
            'fields': ('order', 'text', 'question_type', 'field_name')
        }),
        ('Дополнительно', {
            'fields': ('choices', 'image', 'is_required', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def short_text(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    short_text.short_description = 'Текст вопроса'


@admin.register(StaffApplication)
class StaffApplicationAdmin(admin.ModelAdmin):
    """Админка для анкет сотрудников - все данные в одном месте."""
    
    list_display = ['full_name', 'position', 'phone', 'email', 'status', 'completion', 'created_at']
    list_display_links = ['full_name']
    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'user__telegram_id', 'user__username']
    readonly_fields = ['user', 'created_at', 'updated_at', 'completed_at', 'completion',
                       'passport_main_preview', 'passport_registration_preview', 
                       'snils_preview', 'inn_preview']
    
    fieldsets = (
        ('Telegram', {
            'fields': ('user', 'status')
        }),
        ('Основная информация', {
            'fields': ('position', 'full_name', 'address', 'phone', 'email')
        }),
        ('Документы', {
            'fields': (
                ('passport_main', 'passport_main_preview'),
                ('passport_registration', 'passport_registration_preview'),
                ('snils', 'snils_preview'),
                ('inn', 'inn_preview'),
            )
        }),
        ('Семья', {
            'fields': ('marital_status', 'children', 'emergency_contact')
        }),
        ('Дополнительно', {
            'fields': ('additional_info',),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def completion(self, obj):
        pct = obj.get_completion_percentage()
        color = 'green' if pct == 100 else 'orange' if pct >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} %</span>',
            color, pct
        )
    completion.short_description = 'Заполнено'
    
    def _photo_preview(self, photo):
        if photo:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-height: 150px; max-width: 200px;"/>'
                '</a>', 
                photo.url, photo.url
            )
        return '-'
    
    def passport_main_preview(self, obj):
        return self._photo_preview(obj.passport_main)
    passport_main_preview.short_description = 'Превью'
    
    def passport_registration_preview(self, obj):
        return self._photo_preview(obj.passport_registration)
    passport_registration_preview.short_description = 'Превью'
    
    def snils_preview(self, obj):
        return self._photo_preview(obj.snils)
    snils_preview.short_description = 'Превью'
    
    def inn_preview(self, obj):
        return self._photo_preview(obj.inn)
    inn_preview.short_description = 'Превью'


class UserResponseInline(admin.TabularInline):
    model = UserResponse
    extra = 0
    readonly_fields = ['question', 'text_answer', 'photo_preview', 'created_at']
    fields = ['question', 'text_answer', 'photo_preview', 'created_at']
    can_delete = False
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 100px;"/></a>', 
                             obj.photo.url, obj.photo.url)
        return '-'
    photo_preview.short_description = 'Фото'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['telegram_id', 'username', 'full_name', 'is_team_member', 'is_registration_complete', 'created_at']
    list_filter = ['is_team_member', 'is_registration_complete', 'created_at']
    search_fields = ['telegram_id', 'username', 'first_name', 'last_name']
    readonly_fields = ['telegram_id', 'username', 'first_name', 'last_name', 'created_at', 'updated_at']
    inlines = [UserResponseInline]
    
    def full_name(self, obj):
        parts = filter(None, [obj.first_name, obj.last_name])
        return ' '.join(parts) or '-'
    full_name.short_description = 'Полное имя'


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_short', 'answer_short', 'photo_preview', 'created_at']
    list_filter = ['question', 'created_at']
    search_fields = ['user__telegram_id', 'user__username', 'text_answer']
    readonly_fields = ['user', 'question', 'text_answer', 'photo_preview', 'created_at', 'updated_at']
    
    def question_short(self, obj):
        return obj.question.text[:50] + '...' if len(obj.question.text) > 50 else obj.question.text
    question_short.short_description = 'Вопрос'
    
    def answer_short(self, obj):
        if obj.text_answer:
            return obj.text_answer[:50] + '...' if len(obj.text_answer) > 50 else obj.text_answer
        return '-'
    answer_short.short_description = 'Ответ'
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 50px;"/></a>', 
                             obj.photo.url, obj.photo.url)
        return '-'
    photo_preview.short_description = 'Фото'


# Customize admin site
admin.site.site_header = 'New Edge Team: Staff Bot'
admin.site.site_title = 'Бот "Новые грани"'
admin.site.index_title = 'Управление ботом'
