import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from posts.models import Post, Group
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreatFormTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='Author1'
        )
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug'
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

        self.post = Post.objects.create(
            text='Test post text',
            author=self.user_for_authorized,
        )

    # проверяем, что при отправке валидной формы
    # создается новый пост без группы в бд
    def test_form_create_post(self):
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'New post 1',
            'image': uploaded
        }

        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(Post.objects.first().text, form_data['text'])

    # провверяем, что при отправке валидной формы
    # создается новый пост с группой в бд
    def test_form_create_post_with_group(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'New post 2',
            'group': self.group.pk,
        }

        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(Post.objects.first().text, form_data['text'])

    # проверяем, что при отправке валидной формы со страницы изменения поста
    # происходит изменения поста с тем же post_id
    def test_valid_edit_form(self):
        form_data = {
            'text': 'New post 1 after edit',
        }

        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )

        self.assertEqual(
            Post.objects.get(id=self.post.pk).text,
            form_data['text']
        )
