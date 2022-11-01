import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from posts.models import *
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

from posts.views import FIRST_TEN_POSTS

User = get_user_model()

POSTS_IN_SECOND_PAGE = 3
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.small_gif = (            
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(
            username='Author1',
        )
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
        )
        cls.group1 = Group.objects.create(
            title='Test group 1',
            slug='test-slug-1',
        )
        cls.post = Post.objects.create(
            text='Test post text',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user_for_authorized = User.objects.create_user(
            username='Author2',
        )
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_for_authorized)

        self.user_for_following = User.objects.create_user(
            username='Author3',
        )

        self.user_not_follow = User.objects.create_user(
            username='Author4',
        )
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user_not_follow)

        self.post_from_authorized = Post.objects.create(
            text='Post from authorized client',
            author=self.user_for_authorized,
            image='posts/small.gif',
        )
        self.comment = Comment.objects.create(
            text='Test comment',
            post=self.post_from_authorized,
            author=self.user_for_authorized
        )
        self.post_from_following = Post.objects.create(
            text='Post from following user',
            author=self.user_for_following
        )

    #тестируем кэш
    def test_index_cash(self):
        response = self.guest_client.get(reverse('posts:index'))
        Post.objects.get(pk=self.post.pk).delete()
        response_cash = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_cash.content)

    # проверяем соответствие шаблонов
    def test_page_uses_correct_templates(self):
        page_template_name = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:profile', kwargs={
                    'username': self.user_for_authorized.username
                }
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:post_create'
            ): 'posts/create_post.html',
            reverse(
                'posts:post_edit', kwargs={
                    'post_id': self.post_from_authorized.pk
                }
            ): 'posts/create_post.html',
        }
        for page, template in page_template_name.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(page)
                self.assertTemplateUsed(response, template)

    # проверяем контекст на странице создания поста
    def test_context_create_page(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields[value]
                self.assertIsInstance(form_field, expected)

    # проверяем контекст на главной странице
    def test_context_index(self):
        response = self.authorized_client.get(reverse('posts:index'))
        first_post = response.context['page_obj'][1]
        self.assertEqual(first_post.text, self.post_from_authorized.text)
        self.assertEqual(first_post.author.username, self.user_for_authorized.username)
        self.assertContains(response, '<img')

    # проверяем контекст на странице группы
    def test_context_group_posts(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        first_post = response.context['page_obj'][0]
        group_page = response.context['group'].title
        post_text_0 = first_post.text
        self.assertEqual(group_page, self.group.title)
        self.assertEqual(post_text_0, self.post.text)
        self.assertContains(response, '<img')

    # проверяем контекст на странице автора
    def test_context_profile(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={
                'username': self.user_for_authorized.username
            })
        )
        self.assertEqual(
            response.context['author'].username,
            self.user_for_authorized.username
        )
        self.assertEqual(response.context['post_count'], 1)
        self.assertEqual(
            response.context['page_obj'][0].author.username,
            self.user_for_authorized.username
        )
        self.assertContains(response, '<img')

    # проверяем контекст на странице подробнее о посте
    def test_context_post_detail(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': self.post_from_authorized.pk
            })
        )
        self.assertEqual(
            response.context['post'].pk,
            self.post_from_authorized.pk
        )
        self.assertIn(self.comment, response.context['comments'])
        self.assertContains(response, '<img')

    # проверяем контекст на странице редактирования поста
    def test_context_post_edit(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post_from_authorized.pk
            })
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
            self.assertEqual(
                response.context['post'].pk,
                self.post_from_authorized.pk
            )

    # проверяем, что при создании поста с группой, он попадает
    # на главную, страницу группы и страницу профайл
    def test_post_with_group_add_to_all_pages(self):
        urls_page_post_with_group = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for url in urls_page_post_with_group:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                list_of_posts = response.context['page_obj']
                self.assertIn(self.post, list_of_posts)

    # проверяем, что этот пост не попадает на страницу другой группы
    def test_post_with_group_not_add_in_other_group(self):
        response = self.guest_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.group1.slug}
            )
        )
        list_of_posts = response.context['page_obj']
        self.assertNotIn(self.post, list_of_posts)

    # проверяем, что авторизованный пользователь может подписаться
    def test_follow(self):
        self.authorized_client.get(reverse
            ('posts:profile_follow', kwargs={
                'username': self.user_for_following.username
            })
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user_for_authorized, author=self.user_for_following
        ).exists())

    # проверяем, что нельзя подписаться на самого себя
    # def test_follow_to_self(self):
        # response = self.authorized_client.get(reverse('posts:profile', kwargs={
            # 'username': self.authorized_client.username
        # }))

    # проверяем, что авторизованный пользователь может отписаться
    def test_unfollow(self):
        self.authorized_client.get(reverse
            ('posts:profile_follow', kwargs={
                'username': self.user_for_following.username
            })
        )
        self.authorized_client.get(reverse
            ('posts:profile_unfollow', kwargs={
                'username': self.user_for_following.username
            })
        )
        self.assertFalse(Follow.objects.filter(
            user=self.user_for_authorized, author=self.user_for_following
        ).exists())

    # проверяем, что новая запись появляется
    # в ленте у тех, кто подписан на автора
    def test_new_post_in_follow_index(self):
        self.authorized_client.get(reverse
            ('posts:profile_follow', kwargs={
                'username': self.user_for_following.username
            })
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(self.post_from_following, response.context['page_obj'])

    # проверяем, что новая запись не появляется
    # в ленте у тех, кто не подписан на автора
    def test_new_post_not_in_follow_index(self):
        self.authorized_client_2.get(reverse
            ('posts:profile_follow', kwargs={
                'username': self.user_for_authorized.username
            })
        )
        response = self.authorized_client_2.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(self.post_from_following, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='Author1',
        )
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
        )
        for i in range(13):
            Post.objects.create(
                text=i,
                author=cls.user,
                group=cls.group,
            )

    def setUp(self):
        self.guest_client = Client()
        self.user_for_authorized = User.objects.create_user(
            username='Author2',
        )
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_for_authorized)

    def test_page_and_count_posts(self):
        page_count_posts = {
            reverse('posts:index'): FIRST_TEN_POSTS,
            '/?page=2': POSTS_IN_SECOND_PAGE,
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): FIRST_TEN_POSTS,
            '/group/test-slug/?page=2': POSTS_IN_SECOND_PAGE,
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): FIRST_TEN_POSTS,
            '/profile/Author1/?page=2': POSTS_IN_SECOND_PAGE,
        }
        for page, count_post in page_count_posts.items():
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(len(response.context['page_obj']), count_post)
