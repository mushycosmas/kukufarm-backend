from rest_framework import viewsets, permissions
from .models import Customer
from .serializers import CustomerSerializer
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by("name")
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name","phone","email"]
    filterset_fields = ["active"]
