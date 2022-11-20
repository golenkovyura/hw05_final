from math import ceil
import tempfile
import shutil

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Post, Group, Comment, Follow
from ..forms import PostForm


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.MEDIA_ROOT)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    """Создаем тестовых данных"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='unnamed')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='slug',
            description='Описание'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.another_group = Group.objects.create(
            title='Заголовок1',
            slug='slug1',
            description='Описание1'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст поста',
            group=cls.group,
        )
        cls.comment_post = Comment.objects.create(
            author=cls.user,
            text='Текст комментария',
            post=cls.post
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def post_exist(self, page_context):
        """Проверка существования поста на страницах"""
        if 'page_obj' in page_context:
            post = page_context['page_obj'][0]
        else:
            post = page_context['post']
        self.assertEqual(
            post.author,
            PostViewTests.post.author
        )
        self.assertEqual(
            post.text,
            PostViewTests.post.text
        )
        self.assertEqual(
            post.group,
            PostViewTests.post.group
        )
        self.assertEqual(
            post.comments.last(),
            PostViewTests.comment_post
        )

    def test_show_correct_exist_context(self):
        """Шаблон post_detail, index
        созданы с правильным контекстом"""
        response_list = [
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostViewTests.post.pk}
            ),
            reverse('posts:index'),
        ]
        for url in response_list:
            response = self.authorized_client.get(url)
            page_context = response.context
            self.post_exist(page_context)

    def test_show_correct_context(self):
        """Шаблон group_list, profile
        сформированы с правильным контекстом"""
        response_group = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostViewTests.group.slug})
        )
        response_profile = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': PostViewTests.user.username}
            )
        )
        task_group = response_group.context['group']
        self.assertEqual(task_group, PostViewTests.group)
        task_profile = response_profile.context['author']
        self.assertEqual(task_profile, PostViewTests.user)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_edit_page_show_correct_context(self):
        """Шаблоны create_post/edit сформированы с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': PostViewTests.post.pk})
        )
        self.assertEqual(response.context.get('form').instance, self.post)

    def test_new_post_not_in_another_group(self):
        """Пост не сохраняется в группе, не предназначенной для него."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={
                'slug': PostViewTests.another_group.slug
            })
        )
        self.assertNotEqual(response.context.get('post'), PostViewTests.post)

    def test_index_caches(self):
        """Тестирование кэша главной страницы."""
        new_post = Post.objects.create(
            group=PostViewTests.group,
            author=PostViewTests.user,
            text='Пост для удаления',
        )
        response_1 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_1 = response_1.content
        new_post.delete()
        response_2 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_2 = response_2.content
        self.assertEqual(response_content_1, response_content_2)
        cache.clear()
        response_3 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_3 = response_3.content
        self.assertNotEqual(response_content_2, response_content_3)

    def test_follow(self):
        """Проверка подписки"""
        Follow.objects.all().delete()
        new_author = User.objects.create(username='New')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(Follow.objects.last().author, new_author)
        self.assertEqual(Follow.objects.last().user, PostViewTests.user)

    def test_unfollow(self):
        """Проверка отписки"""
        Follow.objects.all().delete()
        new_author = User.objects.create(username='New')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), 0)

    def test_following_posts(self):
        """Пост появляется в ленте подписчика"""
        new_user = User.objects.create(username='New')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': PostViewTests.user.username}
            )
        )
        response_follow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_follow = response_follow.context
        self.post_exist(context_follow)

    def test_unfollowing_posts(self):
        """Поста нет в ленте у не подписчика"""
        new_user = User.objects.create(username='New')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        response_unfollow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_unfollow = response_unfollow.context
        self.assertEqual(len(context_unfollow['page_obj']), 0)


class PaginatorViewTest(TestCase):

    def setUp(self):
        self.TEST_OF_POST = 13
        self.last_page = ceil(self.TEST_OF_POST // settings.NUM_POSTS + 1)
        self.posts_on_last_page = self.TEST_OF_POST - (
            settings.NUM_POSTS * (self.last_page - 1))
        self.auth = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.auth)
        self.group = Group.objects.create(
            title='title',
            slug='slug',
            description='description'
        )
        paginator_objects = []
        for page in range(self.TEST_OF_POST):
            paginator_objects.append(Post(
                author=self.auth,
                text='Тестовый пост ' + str(page),
                group=self.group
            ))
        Post.objects.bulk_create(paginator_objects)
        cache.clear()

    def test_paginator_correct_context(self):
        """Проверка шаблонов Пагинатора"""
        paginator_data = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.auth.username}
            )
        ]
        for paginator_page in paginator_data:
            with self.subTest(paginator_page=paginator_page):
                response_filled_page = self.authorized_client.get(
                    paginator_page
                )
                response_unfilled_page = self.authorized_client.get(
                    paginator_page + '?page=' + (
                        f'{self.last_page}')
                )
                self.assertEqual(len(
                    response_filled_page.context['page_obj']),
                    settings.NUM_POSTS
                )
                self.assertEqual(len(
                    response_unfilled_page.context['page_obj']),
                    self.posts_on_last_page
                )
