from rest_framework import viewsets, permissions
from .models import Supplier
from .serializers import SupplierSerializer
class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("name")
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name","contact_person","phone","email"]
