from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

class ReportsApiTest(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username="test", password="test12345")
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    def test_dashboard(self):
        response = self.client.get("/api/reports/dashboard/")
        self.assertEqual(response.status_code, 200)
