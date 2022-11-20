from django.test import TestCase, Client
from django.urls import reverse

from http import HTTPStatus


class AboutURLTest(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_urls_uses_correct_template_and_response(self):
        templates_pages_names = {
            'about/author.html': reverse('about:author'),
            'about/tech.html': reverse('about:tech'),
        }
        for template, adress in templates_pages_names.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)
