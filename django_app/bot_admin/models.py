from django.db import models
from django.core.cache import cache


class BotSettings(models.Model):
    """Настройки бота. Singleton модель - только одна запись."""
    
    bot_token = models.CharField(
        max_length=100,
        verbose_name='Токен бота',
        help_text='Токен от @BotFather. Если пусто, используется из .env',
        blank=True,
        null=True
    )
    bot_name = models.CharField(
        max_length=100,
        verbose_name='Имя бота',
        blank=True,
        null=True
    )
    welcome_image = models.ImageField(
        upload_to='settings/',
        verbose_name='Приветственное изображение',
        blank=True,
        null=True,
        help_text='Изображение для приветственного сообщения'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Бот активен'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Настройки бота'
        verbose_name_plural = 'Настройки бота'
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)
        # Clear cache when settings change
        cache.delete('bot_settings')
    
    def delete(self, *args, **kwargs):
        pass  # Prevent deletion
    
    @classmethod
    def get_settings(cls):
        """Get or create settings instance."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    @classmethod
    def get_bot_token(cls):
        """Get bot token from DB or return None to use env fallback."""
        try:
            settings = cls.objects.get(pk=1)
            return settings.bot_token if settings.bot_token else None
        except cls.DoesNotExist:
            return None
    
    def __str__(self):
        return "Настройки бота"


class Question(models.Model):
    """Модель вопроса для бота."""
    
    class QuestionType(models.TextChoices):
        TEXT = 'text', 'Текстовый ответ'
        PHOTO = 'photo', 'Фото'
        CHOICE = 'choice', 'Выбор из вариантов'
        INFO = 'info', 'Информационное сообщение'
    
    order = models.PositiveIntegerField(
        verbose_name='Порядок',
        default=0,
        help_text='Порядок отображения вопроса'
    )
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.TEXT,
        verbose_name='Тип вопроса'
    )
    text = models.TextField(
        verbose_name='Текст вопроса',
        help_text='Поддерживает HTML-форматирование для Telegram'
    )
    choices = models.TextField(
        verbose_name='Варианты ответа',
        blank=True,
        null=True,
        help_text='Для типа "Выбор": введите варианты через запятую (например: да, нет)'
    )
    image = models.ImageField(
        upload_to='questions/',
        verbose_name='Изображение',
        blank=True,
        null=True,
        help_text='Изображение для отправки с вопросом'
    )
    field_name = models.CharField(
        max_length=100,
        verbose_name='Имя поля',
        blank=True,
        null=True,
        help_text='Техническое имя поля для сохранения ответа (например: full_name, phone)'
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name='Обязательный'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.order}. {self.text[:50]}..."
    
    def get_choices_list(self):
        """Возвращает список вариантов ответа."""
        if self.choices:
            return [c.strip() for c in self.choices.split(',')]
        return []


class UserProfile(models.Model):
    """Профиль пользователя бота."""
    
    telegram_id = models.BigIntegerField(
        unique=True,
        verbose_name='Telegram ID'
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Username'
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Имя в Telegram'
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Фамилия в Telegram'
    )
    current_question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Текущий вопрос'
    )
    is_team_member = models.BooleanField(
        default=False,
        verbose_name='Член команды'
    )
    is_registration_complete = models.BooleanField(
        default=False,
        verbose_name='Регистрация завершена'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"{self.telegram_id} - {self.username or 'No username'}"


class UserResponse(models.Model):
    """Ответ пользователя на вопрос."""
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name='Пользователь'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name='Вопрос'
    )
    text_answer = models.TextField(
        blank=True,
        null=True,
        verbose_name='Текстовый ответ'
    )
    photo = models.ImageField(
        upload_to='responses/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        unique_together = ['user', 'question']
    
    def __str__(self):
        return f"{self.user.telegram_id} - {self.question.text[:30]}..."
    
    def get_answer_display(self):
        """Возвращает отображение ответа."""
        if self.photo:
            return f"[Фото: {self.photo.name}]"
        return self.text_answer or "-"


class StaffApplication(models.Model):
    """Анкета сотрудника - все данные в одном объекте."""
    
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'В процессе заполнения'
        COMPLETED = 'completed', 'Заполнена'
        APPROVED = 'approved', 'Одобрена'
        REJECTED = 'rejected', 'Отклонена'
    
    # Связь с профилем Telegram
    user = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='application',
        verbose_name='Профиль Telegram'
    )
    
    # Статус анкеты
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        verbose_name='Статус'
    )
    
    # Позиция в команде
    position = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Позиция в команде'
    )
    
    # Личные данные
    full_name = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='ФИО'
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='Адрес проживания'
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Телефон'
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='Email'
    )
    
    # Документы (фото)
    passport_main = models.ImageField(
        upload_to='applications/passports/',
        blank=True,
        null=True,
        verbose_name='Паспорт (главный разворот)'
    )
    passport_registration = models.ImageField(
        upload_to='applications/passports/',
        blank=True,
        null=True,
        verbose_name='Паспорт (прописка)'
    )
    snils = models.ImageField(
        upload_to='applications/snils/',
        blank=True,
        null=True,
        verbose_name='СНИЛС'
    )
    inn = models.ImageField(
        upload_to='applications/inn/',
        blank=True,
        null=True,
        verbose_name='ИНН'
    )
    
    # Семейное положение
    marital_status = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Семейное положение'
    )
    children = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Дети'
    )
    
    # Контакты близких
    emergency_contact = models.TextField(
        blank=True,
        null=True,
        verbose_name='Контакты близких'
    )
    
    # Дополнительная информация
    additional_info = models.TextField(
        blank=True,
        null=True,
        verbose_name='Дополнительная информация'
    )
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата завершения'
    )
    
    class Meta:
        verbose_name = 'Анкета сотрудника'
        verbose_name_plural = 'Анкеты сотрудников'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name or self.user.username or self.user.telegram_id} - {self.get_status_display()}"
    
    def get_completion_percentage(self):
        """Возвращает процент заполнения анкеты."""
        fields = ['full_name', 'address', 'phone', 'email', 'passport_main', 
                  'passport_registration', 'snils', 'inn', 'marital_status', 
                  'children', 'emergency_contact']
        filled = sum(1 for f in fields if getattr(self, f))
        return int((filled / len(fields)) * 100)

