from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache

from posts.models import Post, Group


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='unnamed')
        cls.non_author = User.objects.create_user(username='non_author')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Описание группы'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст поста'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)

    def test_actual_url_correct_name(self):
        """Соотвествие адресов страниц их именам"""
        url_names = [
            (f'/profile/{PostURLTests.user.username}/', reverse(
                'posts:profile',
                kwargs={'username': 'unnamed'}
            )),
            ('/', reverse('posts:index')),
            (f'/group/{PostURLTests.group.slug}/', reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug'}
            )),
            (f'/posts/{PostURLTests.post.pk}/', reverse(
                'posts:post_detail',
                kwargs={'post_id': PostURLTests.post.pk}
            )),
            ('/create/', reverse('posts:post_create')),
            (f'/posts/{PostURLTests.post.pk}/edit/', reverse(
                'posts:post_edit',
                kwargs={'post_id': PostURLTests.post.pk}
            )),
            (f'/posts/{PostURLTests.post.pk}/comment/', reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.pk}
            )),
            ('/follow/', reverse('posts:follow_index')),
            (f'/profile/{PostURLTests.user.username}/follow/', reverse(
                'posts:profile_follow',
                kwargs={'username': 'unnamed'}
            )),
            (f'/profile/{PostURLTests.user.username}/unfollow/', reverse(
                'posts:profile_unfollow',
                kwargs={'username': 'unnamed'}
            )),
        ]
        for url, name in url_names:
            with self.subTest(url=url):
                self.assertEqual(url, name)

    def test_urls_uses_correct_template(self):
        """Проверяем запрашиваемые шаблоны страниц через имена."""
        cache.clear()
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': PostURLTests.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': PostURLTests.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostURLTests.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostURLTests.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_urls_response_guest_and_auth(self):
        """Доступность страниц для клиента"""
        url_status = [
            (reverse('posts:index'), HTTPStatus.OK, False),
            (reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug'}
            ), HTTPStatus.OK, False),
            (reverse(
                'posts:profile',
                kwargs={'username': 'unnamed'}
            ), HTTPStatus.OK, False),
            (reverse(
                'posts:post_detail',
                kwargs={'post_id': PostURLTests.post.pk}
            ), HTTPStatus.OK, False),
            ('/unexpecting_page/', HTTPStatus.NOT_FOUND, False),
            (reverse(
                'posts:post_edit', kwargs={'post_id': PostURLTests.post.pk}
            ), HTTPStatus.OK, True),
            (reverse('posts:post_create'), HTTPStatus.OK, True),
            (reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.pk}
            ), HTTPStatus.FOUND, True),
            (reverse('posts:follow_index'), HTTPStatus.OK, True),
            (reverse(
                'posts:profile_follow',
                kwargs={'username': 'unnamed'}
            ), HTTPStatus.FOUND, True),
            (reverse(
                'posts:profile_unfollow',
                kwargs={'username': 'unnamed'}
            ), HTTPStatus.FOUND, False),
        ]
        for url, status_code, auth in url_status:
            with self.subTest(url=url):
                if auth is False:
                    response = self.guest_client.get(url)
                else:
                    response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, status_code)

    def test_urls_response_guest_redirect(self):
        """Проверяем редирект страниц для гостя"""
        url_redirect = [
            (reverse(
                'posts:post_edit',
                kwargs={'post_id': PostURLTests.post.pk}
            ), reverse('users:login')),
            (reverse('posts:post_create'),
                reverse('users:login') + '?next='
                + reverse('posts:post_create')),
            (reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.pk}
            ), reverse('users:login') + '?next='
                + reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.pk}
            )),
            (reverse(
                'posts:follow_index'
            ), reverse('users:login') + '?next=' + reverse(
                'posts:follow_index')),
            (reverse(
                'posts:profile_follow',
                kwargs={'username': PostURLTests.user.username}
            ), reverse('users:login') + '?next=' + reverse(
                'posts:profile_follow',
                kwargs={'username': PostURLTests.user.username}
            )),
            (reverse(
                'posts:profile_unfollow',
                kwargs={'username': PostURLTests.user.username}
            ), reverse('users:login') + '?next=' + reverse(
                'posts:profile_unfollow',
                kwargs={'username': PostURLTests.user.username}
            ))
        ]
        for url, redirect_url in url_redirect:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, redirect_url)

    def test_urls_response_non_author_redirect(self):
        self.authorized_client.force_login(PostURLTests.non_author)
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostURLTests.post.pk}
            ))
        redirect_url = reverse('users:login')
        self.assertRedirects(response, redirect_url)
