from rest_framework import viewsets, permissions
from .models import Sale
from .serializers import SaleSerializer
class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("customer").prefetch_related("items").all().order_by("-date","-id")
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["invoice_no","customer__name"]
    filterset_fields = ["customer","payment_method","date"]
