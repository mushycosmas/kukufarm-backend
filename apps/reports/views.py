from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.flocks.models import Flock
from apps.production.models import EggProduction
from apps.sales.models import Sale
from apps.expenses.models import Expense
from apps.feed.models import FeedStock

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    today = date.today()
    active = Flock.objects.filter(status=Flock.Status.ACTIVE)
    return Response({
        "date": today,
        "flocks": active.count(),
        "birds": active.aggregate(v=Sum("current_quantity"))["v"] or 0,
        "eggs_today": EggProduction.objects.filter(date=today).aggregate(v=Sum("eggs_collected"))["v"] or 0,
        "sales_today": Sale.objects.filter(date=today).aggregate(v=Sum("total"))["v"] or Decimal("0"),
        "expenses_today": Expense.objects.filter(date=today).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "mortality_today": 0,
        "low_stock_feeds": FeedStock.objects.filter(quantity__lte=0).count(),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary(request):
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    sales = Sale.objects.all()
    expenses = Expense.objects.all()
    eggs = EggProduction.objects.all()
    if start:
        sales = sales.filter(date__gte=start); expenses = expenses.filter(date__gte=start); eggs = eggs.filter(date__gte=start)
    if end:
        sales = sales.filter(date__lte=end); expenses = expenses.filter(date__lte=end); eggs = eggs.filter(date__lte=end)
    total_sales = sales.aggregate(v=Sum("total"))["v"] or Decimal("0")
    total_expenses = expenses.aggregate(v=Sum("amount"))["v"] or Decimal("0")
    total_eggs = eggs.aggregate(v=Sum("eggs_collected"))["v"] or 0
    return Response({"sales": total_sales, "expenses": total_expenses, "profit": total_sales-total_expenses, "eggs": total_eggs})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def production_chart(request):
    days = max(1, min(int(request.query_params.get("days", 30)), 365))
    start = date.today() - timedelta(days=days - 1)
    rows = EggProduction.objects.filter(date__gte=start).values("date").annotate(eggs=Sum("eggs_collected")).order_by("date")
    return Response([{"date": row["date"], "eggs": row["eggs"]} for row in rows])
