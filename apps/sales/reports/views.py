from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.sax.saxutils import escape

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import permissions
from rest_framework.views import APIView

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ..models import (
    Sale,
    SaleItem,
    SalePayment,
)

from apps.settings.models import FarmSettings


class SalesPDFReportView(APIView):
    """
    Generate a professional Sales PDF report.

    Includes:

        - Sales summary
        - Sales by payment status
        - Sales by payment method
        - Sales by customer
        - Product sales
        - Payment transactions
        - Detailed invoices
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def escape_text(value):
        if value is None:
            return ""

        return escape(
            str(value)
        )

    @staticmethod
    def parse_date(value):
        if not value:
            return None

        try:
            return datetime.strptime(
                value,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return None

    @staticmethod
    def get_farm_timezone():
        try:
            return ZoneInfo(
                "Africa/Dar_es_Salaam"
            )

        except ZoneInfoNotFoundError:
            return timezone.get_current_timezone()

    @staticmethod
    def format_report_date(value):
        if not value:
            return "-"

        return value.strftime(
            "%d %B %Y"
        )

    @staticmethod
    def format_datetime(value, tz):
        if not value:
            return "-"

        try:
            value = value.astimezone(
                tz
            )

        except Exception:
            pass

        return value.strftime(
            "%d %B %Y %H:%M"
        )

    @staticmethod
    def money(value):
        if value is None:
            value = Decimal("0")

        return (
            f"TZS "
            f"{Decimal(str(value)):,.2f}"
        )

    # ============================================================
    # FOOTER / WATERMARK
    # ============================================================

    def _add_page_footer(
        self,
        canvas,
        doc,
        farm_settings,
        logo_path=None,
    ):
        canvas.saveState()

        width, height = A4

        # --------------------------------------------------------
        # WATERMARK
        # --------------------------------------------------------

        if logo_path:

            try:
                logo = ImageReader(
                    logo_path
                )

                canvas.saveState()

                canvas.setFillAlpha(
                    0.05
                )

                watermark_size = 90 * mm

                canvas.drawImage(
                    logo,
                    (
                        width
                        - watermark_size
                    ) / 2,
                    (
                        height
                        - watermark_size
                    ) / 2,
                    width=watermark_size,
                    height=watermark_size,
                    preserveAspectRatio=True,
                    mask="auto",
                )

                canvas.restoreState()

            except Exception:
                pass

        # --------------------------------------------------------
        # FOOTER LINE
        # --------------------------------------------------------

        canvas.setStrokeColor(
            colors.HexColor(
                "#D9D9D9"
            )
        )

        canvas.line(
            15 * mm,
            12 * mm,
            width - 15 * mm,
            12 * mm,
        )

        # --------------------------------------------------------
        # FARM NAME
        # --------------------------------------------------------

        farm_name = ""

        if farm_settings:

            farm_name = getattr(
                farm_settings,
                "farm_name",
                "",
            ) or ""

        canvas.setFont(
            "Helvetica",
            7,
        )

        canvas.setFillColor(
            colors.HexColor(
                "#666666"
            )
        )

        canvas.drawString(
            15 * mm,
            8 * mm,
            self.escape_text(
                farm_name
            ),
        )

        # --------------------------------------------------------
        # PAGE NUMBER
        # --------------------------------------------------------

        canvas.drawRightString(
            width - 15 * mm,
            8 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # ============================================================
    # GET
    # ============================================================

    def get(self, request):

        # --------------------------------------------------------
        # DATE PARAMETERS
        # --------------------------------------------------------

        from_date_raw = request.query_params.get(
            "from_date"
        )

        to_date_raw = request.query_params.get(
            "to_date"
        )

        if not from_date_raw:

            return HttpResponse(
                "from_date is required.",
                status=400,
                content_type="text/plain",
            )

        if not to_date_raw:

            return HttpResponse(
                "to_date is required.",
                status=400,
                content_type="text/plain",
            )

        from_date = self.parse_date(
            from_date_raw
        )

        to_date = self.parse_date(
            to_date_raw
        )

        if not from_date:

            return HttpResponse(
                "Invalid from_date. Expected YYYY-MM-DD.",
                status=400,
                content_type="text/plain",
            )

        if not to_date:

            return HttpResponse(
                "Invalid to_date. Expected YYYY-MM-DD.",
                status=400,
                content_type="text/plain",
            )

        if from_date > to_date:

            return HttpResponse(
                "from_date cannot be after to_date.",
                status=400,
                content_type="text/plain",
            )

        # --------------------------------------------------------
        # FARM SETTINGS
        # --------------------------------------------------------

        try:

            farm_settings = (
                FarmSettings.objects.first()
            )

        except Exception:

            farm_settings = None

        # --------------------------------------------------------
        # SALES
        # --------------------------------------------------------

        sales = (
            Sale.objects
            .filter(
                date__gte=from_date,
                date__lte=to_date,
            )
            .select_related(
                "customer"
            )
            .prefetch_related(
                "items",
                "payments",
            )
            .order_by(
                "date",
                "id",
            )
        )

        # --------------------------------------------------------
        # PAYMENTS
        # --------------------------------------------------------

        payments = (
            SalePayment.objects
            .filter(
                date__gte=from_date,
                date__lte=to_date,
            )
            .select_related(
                "sale",
                "sale__customer",
            )
            .order_by(
                "date",
                "id",
            )
        )

        # --------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------

        sales_list = list(
            sales
        )

        payments_list = list(
            payments
        )

        invoice_count = len(
            sales_list
        )

        total_subtotal = sum(
            (
                sale.subtotal
                for sale in sales_list
            ),
            Decimal("0"),
        )

        total_discount = sum(
            (
                sale.discount
                for sale in sales_list
            ),
            Decimal("0"),
        )

        total_sales = sum(
            (
                sale.total
                for sale in sales_list
            ),
            Decimal("0"),
        )

        total_amount_paid = sum(
            (
                sale.amount_paid
                for sale in sales_list
            ),
            Decimal("0"),
        )

        total_balance = sum(
            (
                sale.balance
                for sale in sales_list
            ),
            Decimal("0"),
        )

        total_payment_transactions = sum(
            (
                payment.amount
                for payment in payments_list
            ),
            Decimal("0"),
        )

        paid_count = sum(
            1
            for sale in sales_list
            if sale.payment_status
            == Sale.PaymentStatus.PAID
        )

        partial_count = sum(
            1
            for sale in sales_list
            if sale.payment_status
            == Sale.PaymentStatus.PARTIAL
        )

        unpaid_count = sum(
            1
            for sale in sales_list
            if sale.payment_status
            == Sale.PaymentStatus.UNPAID
        )

        # --------------------------------------------------------
        # UNIQUE CUSTOMERS
        # --------------------------------------------------------

        customer_ids = set()

        for sale in sales_list:

            if sale.customer_id:

                customer_ids.add(
                    sale.customer_id
                )

        customer_count = len(
            customer_ids
        )

        # --------------------------------------------------------
        # PAYMENT METHOD SUMMARY
        # --------------------------------------------------------

        payment_method_summary = defaultdict(
            lambda: {
                "count": 0,
                "amount": Decimal("0"),
            }
        )

        for sale in sales_list:

            method = (
                sale.get_payment_method_display()
            )

            payment_method_summary[
                method
            ]["count"] += 1

            payment_method_summary[
                method
            ]["amount"] += (
                sale.total
            )

        # --------------------------------------------------------
        # CUSTOMER SUMMARY
        # --------------------------------------------------------

        customer_summary = defaultdict(
            lambda: {
                "customer": "",
                "invoices": 0,
                "sales": Decimal("0"),
                "paid": Decimal("0"),
                "balance": Decimal("0"),
            }
        )

        for sale in sales_list:

            if sale.customer:

                customer_name = (
                    getattr(
                        sale.customer,
                        "name",
                        None,
                    )
                    or str(
                        sale.customer
                    )
                )

                customer_key = (
                    sale.customer_id
                )

            else:

                customer_name = (
                    "Walk-in Customer"
                )

                customer_key = (
                    "walk-in"
                )

            customer_summary[
                customer_key
            ]["customer"] = (
                customer_name
            )

            customer_summary[
                customer_key
            ]["invoices"] += 1

            customer_summary[
                customer_key
            ]["sales"] += (
                sale.total
            )

            customer_summary[
                customer_key
            ]["paid"] += (
                sale.amount_paid
            )

            customer_summary[
                customer_key
            ]["balance"] += (
                sale.balance
            )

        customer_summary_rows = sorted(
            customer_summary.values(),
            key=lambda row: row["sales"],
            reverse=True,
        )

        # --------------------------------------------------------
        # PRODUCT SUMMARY
        # --------------------------------------------------------

        product_summary = defaultdict(
            lambda: {
                "product": "",
                "quantity": Decimal("0"),
                "sales": Decimal("0"),
            }
        )

        for sale in sales_list:

            for item in sale.items.all():

                product_key = (
                    item.product.lower().strip()
                )

                product_summary[
                    product_key
                ]["product"] = (
                    item.product
                )

                product_summary[
                    product_key
                ]["quantity"] += (
                    item.quantity
                )

                product_summary[
                    product_key
                ]["sales"] += (
                    item.total
                )

        product_summary_rows = sorted(
            product_summary.values(),
            key=lambda row: row["sales"],
            reverse=True,
        )

        # --------------------------------------------------------
        # GENERATED TIME
        # --------------------------------------------------------

        farm_timezone = (
            self.get_farm_timezone()
        )

        generated_at = (
            timezone.now()
        )

        generated_at = (
            generated_at.astimezone(
                farm_timezone
            )
        )

        # --------------------------------------------------------
        # RESPONSE
        # --------------------------------------------------------

        filename = (
            "kukufarm-sales-report-"
            f"{from_date_raw}-to-"
            f"{to_date_raw}.pdf"
        )

        response = HttpResponse(
            content_type="application/pdf"
        )

        response[
            "Content-Disposition"
        ] = (
            "inline; "
            f'filename="{filename}"'
        )

        # --------------------------------------------------------
        # DOCUMENT
        # --------------------------------------------------------

        document = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="Sales Report",
            author="KukuFarm",
        )

        styles = getSampleStyleSheet()

        # --------------------------------------------------------
        # STYLES
        # --------------------------------------------------------

        title_style = ParagraphStyle(
            "SalesTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=5,
        )

        subtitle_style = ParagraphStyle(
            "SalesSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceAfter=10,
        )

        section_style = ParagraphStyle(
            "SalesSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(
                "#1F4E78"
            ),
            spaceBefore=8,
            spaceAfter=6,
        )

        small_style = ParagraphStyle(
            "SalesSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        )

        right_style = ParagraphStyle(
            "SalesRight",
            parent=small_style,
            alignment=TA_RIGHT,
        )

        # --------------------------------------------------------
        # STORY
        # --------------------------------------------------------

        story = []

        # ========================================================
        # HEADER
        # ========================================================

        farm_name = ""
        farm_address = ""
        farm_phone = ""
        farm_email = ""

        if farm_settings:

            farm_name = getattr(
                farm_settings,
                "farm_name",
                "",
            ) or ""

            farm_address = getattr(
                farm_settings,
                "address",
                "",
            ) or ""

            farm_phone = getattr(
                farm_settings,
                "phone",
                "",
            ) or ""

            farm_email = getattr(
                farm_settings,
                "email",
                "",
            ) or ""

        if farm_name:

            story.append(
                Paragraph(
                    self.escape_text(
                        farm_name
                    ),
                    title_style,
                )
            )

        story.append(
            Paragraph(
                "SALES REPORT",
                title_style,
            )
        )

        story.append(
            Paragraph(
                "Sales, Payments and Customer Receivables",
                subtitle_style,
            )
        )

        # ========================================================
        # FARM INFORMATION
        # ========================================================

        farm_info = []

        if farm_address:

            farm_info.append(
                self.escape_text(
                    farm_address
                )
            )

        if farm_phone:

            farm_info.append(
                "Tel: "
                + self.escape_text(
                    farm_phone
                )
            )

        if farm_email:

            farm_info.append(
                "Email: "
                + self.escape_text(
                    farm_email
                )
            )

        if farm_info:

            story.append(
                Paragraph(
                    "<br/>".join(
                        farm_info
                    ),
                    ParagraphStyle(
                        "FarmInfo",
                        parent=small_style,
                        alignment=TA_CENTER,
                        textColor=colors.HexColor(
                            "#666666"
                        ),
                    ),
                )
            )

            story.append(
                Spacer(
                    1,
                    5,
                )
            )

        # ========================================================
        # REPORT PERIOD
        # ========================================================

        period_data = [
            [
                Paragraph(
                    "<b>Report From</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Report To</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Generated</b>",
                    small_style,
                ),
            ],
            [
                Paragraph(
                    self.format_report_date(
                        from_date
                    ),
                    small_style,
                ),
                Paragraph(
                    self.format_report_date(
                        to_date
                    ),
                    small_style,
                ),
                Paragraph(
                    self.format_datetime(
                        generated_at,
                        farm_timezone,
                    ),
                    small_style,
                ),
            ],
        ]

        period_table = Table(
            period_data,
            colWidths=[
                55 * mm,
                55 * mm,
                60 * mm,
            ],
        )

        period_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#EAF2F8"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(
            period_table
        )

        story.append(
            Spacer(
                1,
                8,
            )
        )

        # ========================================================
        # SALES SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Sales Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "<b>Invoices</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Total Sales</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Amount Paid</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Outstanding</b>",
                    small_style,
                ),
            ],
            [
                Paragraph(
                    f"{invoice_count:,}",
                    right_style,
                ),
                Paragraph(
                    self.money(
                        total_sales
                    ),
                    right_style,
                ),
                Paragraph(
                    self.money(
                        total_amount_paid
                    ),
                    right_style,
                ),
                Paragraph(
                    self.money(
                        total_balance
                    ),
                    right_style,
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                40 * mm,
                50 * mm,
                50 * mm,
                40 * mm,
            ],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#1F4E78"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, 1),
                        colors.HexColor(
                            "#F7F9FA"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(
            summary_table
        )

        # ========================================================
        # PAYMENT STATUS
        # ========================================================

        story.append(
            Paragraph(
                "Payment Status",
                section_style,
            )
        )

        status_data = [
            [
                Paragraph(
                    "<b>Paid</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Partial</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Unpaid</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Total Transactions</b>",
                    small_style,
                ),
            ],
            [
                Paragraph(
                    f"{paid_count:,}",
                    right_style,
                ),
                Paragraph(
                    f"{partial_count:,}",
                    right_style,
                ),
                Paragraph(
                    f"{unpaid_count:,}",
                    right_style,
                ),
                Paragraph(
                    f"{len(payments_list):,}",
                    right_style,
                ),
            ],
        ]

        status_table = Table(
            status_data,
            colWidths=[
                45 * mm,
                45 * mm,
                45 * mm,
                45 * mm,
            ],
        )

        status_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#38761D"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(
            status_table
        )

        # ========================================================
        # PAYMENT METHODS
        # ========================================================

        story.append(
            Paragraph(
                "Sales by Payment Method",
                section_style,
            )
        )

        payment_method_data = [
            [
                Paragraph(
                    "<b>Payment Method</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Invoices</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Sales Amount</b>",
                    small_style,
                ),
            ]
        ]

        for method, row in sorted(
            payment_method_summary.items(),
            key=lambda x: x[1]["amount"],
            reverse=True,
        ):

            payment_method_data.append(
                [
                    Paragraph(
                        self.escape_text(
                            method
                        ),
                        small_style,
                    ),
                    Paragraph(
                        f'{row["count"]:,}',
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            row["amount"]
                        ),
                        right_style,
                    ),
                ]
            )

        if len(payment_method_data) == 1:

            payment_method_data.append(
                [
                    Paragraph(
                        "No sales found.",
                        small_style,
                    ),
                    "",
                    "",
                ]
            )

        payment_method_table = Table(
            payment_method_data,
            repeatRows=1,
            colWidths=[
                70 * mm,
                40 * mm,
                70 * mm,
            ],
        )

        payment_method_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#1F4E78"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#F8FAFC"
                            ),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(
            payment_method_table
        )

        # ========================================================
        # CUSTOMER SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Sales by Customer",
                section_style,
            )
        )

        customer_data = [
            [
                Paragraph(
                    "<b>Customer</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Invoices</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Total Sales</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Paid</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Balance</b>",
                    small_style,
                ),
            ]
        ]

        for row in customer_summary_rows:

            customer_data.append(
                [
                    Paragraph(
                        self.escape_text(
                            row["customer"]
                        ),
                        small_style,
                    ),
                    Paragraph(
                        f'{row["invoices"]:,}',
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            row["sales"]
                        ),
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            row["paid"]
                        ),
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            row["balance"]
                        ),
                        right_style,
                    ),
                ]
            )

        if len(customer_data) == 1:

            customer_data.append(
                [
                    Paragraph(
                        "No customers found.",
                        small_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                ]
            )

        customer_table = Table(
            customer_data,
            repeatRows=1,
            colWidths=[
                55 * mm,
                25 * mm,
                40 * mm,
                40 * mm,
                40 * mm,
            ],
        )

        customer_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#1F4E78"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#F8FAFC"
                            ),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(
            customer_table
        )

        # ========================================================
        # PRODUCT SALES
        # ========================================================

        story.append(
            Paragraph(
                "Product Sales",
                section_style,
            )
        )

        product_data = [
            [
                Paragraph(
                    "<b>Product</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Quantity</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Sales Amount</b>",
                    small_style,
                ),
            ]
        ]

        for row in product_summary_rows:

            product_data.append(
                [
                    Paragraph(
                        self.escape_text(
                            row["product"]
                        ),
                        small_style,
                    ),
                    Paragraph(
                        f'{row["quantity"]:,.2f}',
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            row["sales"]
                        ),
                        right_style,
                    ),
                ]
            )

        if len(product_data) == 1:

            product_data.append(
                [
                    Paragraph(
                        "No products found.",
                        small_style,
                    ),
                    "",
                    "",
                ]
            )

        product_table = Table(
            product_data,
            repeatRows=1,
            colWidths=[
                80 * mm,
                40 * mm,
                60 * mm,
            ],
        )

        product_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#38761D"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#F8FAFC"
                            ),
                        ],
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(
            product_table
        )

        # ========================================================
        # PAYMENT TRANSACTIONS
        # ========================================================

        story.append(
            Paragraph(
                "Payment Transactions",
                section_style,
            )
        )

        payment_data = [
            [
                Paragraph(
                    "<b>Date</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Invoice</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Customer</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Method</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Reference</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Amount</b>",
                    small_style,
                ),
            ]
        ]

        for payment in payments_list:

            customer_name = (
                "Walk-in Customer"
            )

            if payment.sale.customer:

                customer_name = (
                    getattr(
                        payment.sale.customer,
                        "name",
                        None,
                    )
                    or str(
                        payment.sale.customer
                    )
                )

            payment_data.append(
                [
                    Paragraph(
                        payment.date.strftime(
                            "%d/%m/%Y"
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            payment.sale.invoice_no
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            customer_name
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            payment.get_payment_method_display()
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            payment.reference
                            or "-"
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.money(
                            payment.amount
                        ),
                        right_style,
                    ),
                ]
            )

        if len(payment_data) == 1:

            payment_data.append(
                [
                    Paragraph(
                        "No payment transactions found.",
                        small_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        payment_table = Table(
            payment_data,
            repeatRows=1,
            colWidths=[
                22 * mm,
                28 * mm,
                38 * mm,
                28 * mm,
                34 * mm,
                40 * mm,
            ],
        )

        payment_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#38761D"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#F8FAFC"
                            ),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(
            payment_table
        )

        # ========================================================
        # INVOICE DETAILS
        # ========================================================

        story.append(
            Paragraph(
                "Invoice Details",
                section_style,
            )
        )

        invoice_data = [
            [
                Paragraph(
                    "<b>Date</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Invoice</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Customer</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Total</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Paid</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Balance</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Status</b>",
                    small_style,
                ),
            ]
        ]

        for sale in sales_list:

            customer_name = (
                "Walk-in Customer"
            )

            if sale.customer:

                customer_name = (
                    getattr(
                        sale.customer,
                        "name",
                        None,
                    )
                    or str(
                        sale.customer
                    )
                )

            invoice_data.append(
                [
                    Paragraph(
                        sale.date.strftime(
                            "%d/%m/%Y"
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            sale.invoice_no
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            customer_name
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.money(
                            sale.total
                        ),
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            sale.amount_paid
                        ),
                        right_style,
                    ),
                    Paragraph(
                        self.money(
                            sale.balance
                        ),
                        right_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            sale.get_payment_status_display()
                        ),
                        small_style,
                    ),
                ]
            )

        if len(invoice_data) == 1:

            invoice_data.append(
                [
                    Paragraph(
                        "No invoices found.",
                        small_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        invoice_table = Table(
            invoice_data,
            repeatRows=1,
            colWidths=[
                20 * mm,
                28 * mm,
                40 * mm,
                32 * mm,
                32 * mm,
                32 * mm,
                26 * mm,
            ],
        )

        invoice_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#1F4E78"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D0D7DE"
                        ),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#F8FAFC"
                            ),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(
            invoice_table
        )

        # ========================================================
        # REPORT NOTES
        # ========================================================

        story.append(
            Spacer(
                1,
                8,
            )
        )

        story.append(
            Paragraph(
                "Report Notes",
                section_style,
            )
        )

        notes = [
            (
                "Total Sales represents the total value of "
                "sales invoices within the selected period."
            ),
            (
                "Amount Paid represents the cumulative "
                "amount_paid recorded on the selected sales."
            ),
            (
                "Outstanding represents the remaining "
                "balance calculated as Total minus Amount "
                "Paid."
            ),
            (
                "Payment Transactions show payments recorded "
                "through the SalePayment model during the "
                "selected period."
            ),
            (
                "Customer balances are calculated from the "
                "sales included in this report period."
            ),
        ]

        for note in notes:

            story.append(
                Paragraph(
                    f"• {self.escape_text(note)}",
                    small_style,
                )
            )

            story.append(
                Spacer(
                    1,
                    2,
                )
            )

        # ========================================================
        # LOGO
        # ========================================================

        logo_path = None

        if farm_settings:

            logo = getattr(
                farm_settings,
                "logo",
                None,
            )

            if logo:

                try:
                    logo_path = logo.path

                except Exception:
                    logo_path = None

        # ========================================================
        # BUILD PDF
        # ========================================================

        document.build(
            story,
            onFirstPage=lambda canvas, doc:
                self._add_page_footer(
                    canvas,
                    doc,
                    farm_settings,
                    logo_path,
                ),
            onLaterPages=lambda canvas, doc:
                self._add_page_footer(
                    canvas,
                    doc,
                    farm_settings,
                    logo_path,
                ),
        )

        return response