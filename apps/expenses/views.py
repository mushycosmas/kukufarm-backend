from rest_framework import viewsets, permissions
from .models import Expense
from .serializers import ExpenseSerializer
class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by("-date","-id")
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["description","reference"]
    filterset_fields = ["category","payment_method","date"]
