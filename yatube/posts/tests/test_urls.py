from http import HTTPStatus
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from posts.models import Post, Group, Comment
from django.urls import reverse

User = get_user_model()


class StaticURLTests(TestCase):
    def test_homepage(self):
        guest_client = Client()
        response = guest_client.get(reverse('posts:index'))
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
        )

    def setUp(self) -> None:
        self.quest_client = Client()
        self.user_for_auth = User.objects.create_user(username='NoName1')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_for_auth)
        self.post_for_auth = Post.objects.create(
            text='Test_post',
            author=self.user_for_auth,
            group=self.group,
        )
        self.comment = Comment.objects.create(
            text='Test comment',
            post=self.post_for_auth,
            author=self.user_for_auth
        )

    # проверка доступности страниц неавторизованным пользователям
    def test_valid_url_all_client(self):
        urls_to_test = (
            reverse('posts:index'),
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        )
        for url in urls_to_test:
            with self.subTest(url=url):
                response = self.quest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # проверка доступности страниц авторизованным пользователям
    def test_valid_url_authorized_client(self):
        urls_to_test = (
            reverse('posts:post_create'),
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post_for_auth.pk}
            )
        )
        for url in urls_to_test:
            with self.subTest(url=url):
                respons = self.authorized_client.get(url)
                self.assertEqual(respons.status_code, HTTPStatus.OK)

    # проверка редиректов для неавторизованных пользователей
    def test_redirect_anonym_client(self):
        urls_to_redirect = {
            reverse('posts:post_create'): '/auth/login/?next=/create/',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post_for_auth.pk}
            ): '/auth/login/?next=/posts/2/edit/',
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post_for_auth.pk}
            ): '/auth/login/?next=/posts/2/comment/',
        }
        for url, redirect in urls_to_redirect.items():
            with self.subTest(url=url):
                response = self.quest_client.get(url)
                self.assertRedirects(response, redirect)

    # проверка возврата 404 на несуществующую страницу
    def test_404(self):
        response = self.quest_client.get('/some_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # проверка вызываемых шаблонов
    def test_correct_templates(self):
        urls_templates_name = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post_for_auth.pk}
            ): 'posts/create_post.html',
            '/some-page': 'core/404.html',
        }
        for url, template in urls_templates_name.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
