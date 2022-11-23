from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        verbose_name='Название',
        help_text='Укажите название группы',
        max_length=200,
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Короткое обозначение',
        help_text='Краткое описание группы'
    )
    description = models.TextField(
        verbose_name='Описание',
        help_text='Добавьте описание группы',
    )

    def __str__(self):
        return self.title


class Post(models.Model):
    TEST_NUM_POSTS = 15

    text = models.TextField(
        verbose_name='Текст',
        help_text='Текст вашего поста'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='posts',
        help_text='Укажите имя автора'
    )
    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        help_text='Укажите название вашей группы'
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации', auto_now_add=True
    )
    image = models.ImageField(
        'Картинка к посту',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)

    def __str__(self):
        return self.text[:Post.TEST_NUM_POSTS]


class Comment(models.Model):
    TEST_NUM_COMMENTS = 15

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField(
        verbose_name='Текст комментария',
        help_text='Оставьте комментарий'
    )
    created = models.DateTimeField(
        verbose_name='Дата публикации', auto_now_add=True
    )

    def __str__(self):
        return self.text[:Comment.TEST_NUM_COMMENTS]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_following',
            ),
            models.CheckConstraint(
                check=~models.Q(author=models.F('user')),
                name='author_not_follower',
            ),
        ]
