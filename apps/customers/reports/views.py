from datetime import datetime
from decimal import Decimal
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import permissions
from rest_framework.views import APIView

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from apps.customers.models import Customer
from apps.sales.models import Sale, SalePayment

try:
    from apps.settings.models import FarmSettings
except ImportError:
    FarmSettings = None


class CustomerPDFReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        customer_id = request.query_params.get("customer_id")

        parsed_from_date = None
        parsed_to_date = None

        # =========================================================
        # DATE VALIDATION
        # =========================================================

        if from_date:
            try:
                parsed_from_date = datetime.strptime(
                    from_date,
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                return HttpResponse(
                    "Invalid from_date. Expected format: YYYY-MM-DD.",
                    status=400,
                )

        if to_date:
            try:
                parsed_to_date = datetime.strptime(
                    to_date,
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                return HttpResponse(
                    "Invalid to_date. Expected format: YYYY-MM-DD.",
                    status=400,
                )

        if (
            parsed_from_date
            and parsed_to_date
            and parsed_from_date > parsed_to_date
        ):
            return HttpResponse(
                "from_date cannot be after to_date.",
                status=400,
            )

        # =========================================================
        # CUSTOMERS
        # =========================================================

        customers = Customer.objects.filter(
            active=True
        ).order_by("name")

        if customer_id:
            customers = customers.filter(
                id=customer_id
            )

        # =========================================================
        # SALES
        # =========================================================

        sales = (
            Sale.objects
            .select_related("customer")
            .prefetch_related(
                "items",
                "payments",
            )
            .order_by(
                "date",
                "invoice_no",
            )
        )

        if parsed_from_date:
            sales = sales.filter(
                date__gte=parsed_from_date
            )

        if parsed_to_date:
            sales = sales.filter(
                date__lte=parsed_to_date
            )

        if customer_id:
            sales = sales.filter(
                customer_id=customer_id
            )

        # =========================================================
        # PAYMENTS
        # =========================================================

        payments = (
            SalePayment.objects
            .select_related(
                "sale",
                "sale__customer",
            )
            .order_by(
                "date",
                "id",
            )
        )

        if parsed_from_date:
            payments = payments.filter(
                date__gte=parsed_from_date
            )

        if parsed_to_date:
            payments = payments.filter(
                date__lte=parsed_to_date
            )

        if customer_id:
            payments = payments.filter(
                sale__customer_id=customer_id
            )

        sales = list(sales)
        payments = list(payments)

        # =========================================================
        # FARM SETTINGS
        # =========================================================

        settings_obj = None

        if FarmSettings:
            try:
                settings_obj = (
                    FarmSettings.objects.first()
                )
            except Exception:
                settings_obj = None

        farm_name = (
            "KukuFarm Poultry Management System"
        )

        farm_address = ""
        farm_phone = ""
        farm_email = ""
        farm_logo = None

        if settings_obj:
            farm_name = (
                getattr(
                    settings_obj,
                    "farm_name",
                    None,
                )
                or getattr(
                    settings_obj,
                    "name",
                    None,
                )
                or farm_name
            )

            farm_address = (
                getattr(
                    settings_obj,
                    "address",
                    "",
                )
                or ""
            )

            farm_phone = (
                getattr(
                    settings_obj,
                    "phone",
                    "",
                )
                or ""
            )

            farm_email = (
                getattr(
                    settings_obj,
                    "email",
                    "",
                )
                or ""
            )

            farm_logo = getattr(
                settings_obj,
                "logo",
                None,
            )

        # =========================================================
        # HTTP RESPONSE
        # =========================================================

        response = HttpResponse(
            content_type="application/pdf"
        )

        filename = "customer_report.pdf"

        if customer_id and customers.exists():
            customer = customers.first()

            safe_name = "".join(
                char
                if char.isalnum()
                else "_"
                for char in customer.name
            )

            filename = (
                f"customer_report_"
                f"{safe_name}.pdf"
            )

        response[
            "Content-Disposition"
        ] = (
            f'inline; filename="{filename}"'
        )

        # =========================================================
        # PDF DOCUMENT
        # =========================================================

        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=14 * mm,
            leftMargin=14 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="Customer Report",
            author=farm_name,
        )

        styles = getSampleStyleSheet()

        # =========================================================
        # STYLES
        # =========================================================

        title_style = ParagraphStyle(
            "CustomerReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=5,
        )

        subtitle_style = ParagraphStyle(
            "CustomerReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#666666"
            ),
            spaceAfter=10,
        )

        section_style = ParagraphStyle(
            "CustomerReportSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor(
                "#1F2937"
            ),
        )

        normal_style = ParagraphStyle(
            "CustomerReportNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )

        small_style = ParagraphStyle(
            "CustomerReportSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        )

        right_style = ParagraphStyle(
            "CustomerReportRight",
            parent=small_style,
            alignment=TA_RIGHT,
        )

        center_style = ParagraphStyle(
            "CustomerReportCenter",
            parent=small_style,
            alignment=TA_CENTER,
        )

        story = []

        # =========================================================
        # HELPERS
        # =========================================================

        def money(value):
            value = Decimal(
                value or 0
            )

            return (
                f"TZS {value:,.2f}"
            )

        def safe(value):
            if value is None:
                return ""

            return escape(
                str(value)
            )

        def paragraph(
            value,
            style=small_style,
        ):
            return Paragraph(
                safe(value),
                style,
            )

        def date_text(value):
            if not value:
                return "-"

            return value.strftime(
                "%d %b %Y"
            )

        def report_period_text():
            if (
                parsed_from_date
                and parsed_to_date
            ):
                return (
                    f"{date_text(parsed_from_date)} "
                    f"to "
                    f"{date_text(parsed_to_date)}"
                )

            if parsed_from_date:
                return (
                    f"From "
                    f"{date_text(parsed_from_date)}"
                )

            if parsed_to_date:
                return (
                    f"Up to "
                    f"{date_text(parsed_to_date)}"
                )

            return (
                "All available transactions"
            )

        # =========================================================
        # WATERMARK
        # =========================================================

        def draw_watermark(
            canvas,
            doc,
        ):
            """
            Draw the farm logo as a light watermark
            behind the report content on every page.
            """

            canvas.saveState()

            if farm_logo:
                try:
                    logo_path = farm_logo.path

                    page_width, page_height = A4

                    watermark_width = (
                        95 * mm
                    )

                    watermark_height = (
                        95 * mm
                    )

                    x = (
                        page_width
                        - watermark_width
                    ) / 2

                    y = (
                        page_height
                        - watermark_height
                    ) / 2

                    # -------------------------------------------------
                    # Transparency
                    # -------------------------------------------------

                    try:
                        canvas.setFillAlpha(
                            0.08
                        )

                        canvas.setStrokeAlpha(
                            0.08
                        )
                    except Exception:
                        pass

                    # -------------------------------------------------
                    # Draw logo
                    # -------------------------------------------------

                    canvas.drawImage(
                        logo_path,
                        x,
                        y,
                        width=watermark_width,
                        height=watermark_height,
                        preserveAspectRatio=True,
                        mask="auto",
                        anchor="c",
                    )

                except Exception:
                    pass

            canvas.restoreState()

        # =========================================================
        # PAGE FOOTER
        # =========================================================

        generated_at = (
            timezone.localtime().strftime(
                "%d %b %Y %H:%M"
            )
        )

        def add_page_footer(
            canvas,
            doc,
        ):
            """
            Draw watermark first, then footer.
            The watermark is therefore behind the
            report content.
            """

            # -----------------------------------------------------
            # Watermark
            # -----------------------------------------------------

            draw_watermark(
                canvas,
                doc,
            )

            # -----------------------------------------------------
            # Footer
            # -----------------------------------------------------

            canvas.saveState()

            width, height = A4

            canvas.setFont(
                "Helvetica",
                7,
            )

            canvas.setFillColor(
                colors.HexColor(
                    "#777777"
                )
            )

            canvas.drawString(
                14 * mm,
                9 * mm,
                f"Generated: {generated_at}",
            )

            canvas.drawRightString(
                width - 14 * mm,
                9 * mm,
                f"Page {doc.page}",
            )

            canvas.setStrokeColor(
                colors.HexColor(
                    "#D1D5DB"
                )
            )

            canvas.line(
                14 * mm,
                13 * mm,
                width - 14 * mm,
                13 * mm,
            )

            canvas.restoreState()

        # =========================================================
        # HEADER
        # =========================================================

        story.append(
            Paragraph(
                safe(farm_name),
                title_style,
            )
        )

        farm_contact = " | ".join(
            item
            for item in [
                farm_address,
                farm_phone,
                farm_email,
            ]
            if item
        )

        if farm_contact:
            story.append(
                Paragraph(
                    safe(farm_contact),
                    subtitle_style,
                )
            )

        story.append(
            Paragraph(
                "CUSTOMER REPORT",
                ParagraphStyle(
                    "CustomerReportHeading",
                    parent=title_style,
                    fontSize=13,
                    leading=16,
                    spaceAfter=4,
                ),
            )
        )

        story.append(
            Paragraph(
                (
                    "Reporting Period: "
                    f"{safe(report_period_text())}"
                ),
                subtitle_style,
            )
        )

        # =========================================================
        # SUMMARY CALCULATIONS
        # =========================================================

        total_customers = (
            customers.count()
        )

        total_sales = sum(
            (
                Decimal(
                    s.total or 0
                )
                for s in sales
            ),
            Decimal("0"),
        )

        total_subtotal = sum(
            (
                Decimal(
                    s.subtotal or 0
                )
                for s in sales
            ),
            Decimal("0"),
        )

        total_discount = sum(
            (
                Decimal(
                    s.discount or 0
                )
                for s in sales
            ),
            Decimal("0"),
        )

        total_amount_paid = sum(
            (
                Decimal(
                    s.amount_paid or 0
                )
                for s in sales
            ),
            Decimal("0"),
        )

        total_balance = sum(
            (
                max(
                    Decimal(
                        s.total or 0
                    )
                    - Decimal(
                        s.amount_paid or 0
                    ),
                    Decimal("0"),
                )
                for s in sales
            ),
            Decimal("0"),
        )

        total_payment_transactions = sum(
            (
                Decimal(
                    p.amount or 0
                )
                for p in payments
            ),
            Decimal("0"),
        )

        paid_count = sum(
            1
            for s in sales
            if s.payment_status
            == Sale.PaymentStatus.PAID
        )

        partial_count = sum(
            1
            for s in sales
            if s.payment_status
            == Sale.PaymentStatus.PARTIAL
        )

        unpaid_count = sum(
            1
            for s in sales
            if s.payment_status
            == Sale.PaymentStatus.UNPAID
        )

        # =========================================================
        # SUMMARY
        # =========================================================

        story.append(
            Paragraph(
                "REPORT SUMMARY",
                section_style,
            )
        )

        summary_value_style = (
            lambda name: ParagraphStyle(
                name,
                parent=center_style,
                fontName="Helvetica-Bold",
                fontSize=9,
            )
        )

        summary_data = [
            [
                paragraph(
                    "CUSTOMERS",
                    center_style,
                ),
                paragraph(
                    "INVOICES",
                    center_style,
                ),
                paragraph(
                    "TOTAL SALES",
                    center_style,
                ),
                paragraph(
                    "AMOUNT PAID",
                    center_style,
                ),
            ],
            [
                paragraph(
                    str(
                        total_customers
                    ),
                    summary_value_style(
                        "SummaryValue1"
                    ),
                ),
                paragraph(
                    str(
                        len(sales)
                    ),
                    summary_value_style(
                        "SummaryValue2"
                    ),
                ),
                paragraph(
                    money(
                        total_sales
                    ),
                    summary_value_style(
                        "SummaryValue3"
                    ),
                ),
                paragraph(
                    money(
                        total_amount_paid
                    ),
                    summary_value_style(
                        "SummaryValue4"
                    ),
                ),
            ],
            [
                paragraph(
                    "OUTSTANDING",
                    center_style,
                ),
                paragraph(
                    "PAID / PARTIAL / UNPAID",
                    center_style,
                ),
                paragraph(
                    "PAYMENT TRANSACTIONS",
                    center_style,
                ),
                paragraph(
                    "DISCOUNTS",
                    center_style,
                ),
            ],
            [
                paragraph(
                    money(
                        total_balance
                    ),
                    summary_value_style(
                        "SummaryValue5"
                    ),
                ),
                paragraph(
                    (
                        f"{paid_count} / "
                        f"{partial_count} / "
                        f"{unpaid_count}"
                    ),
                    summary_value_style(
                        "SummaryValue6"
                    ),
                ),
                paragraph(
                    money(
                        total_payment_transactions
                    ),
                    summary_value_style(
                        "SummaryValue7"
                    ),
                ),
                paragraph(
                    money(
                        total_discount
                    ),
                    summary_value_style(
                        "SummaryValue8"
                    ),
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                44 * mm,
                44 * mm,
                44 * mm,
                44 * mm,
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
                            "#F3F4F6"
                        ),
                    ),
                    (
                        "BACKGROUND",
                        (0, 2),
                        (-1, 2),
                        colors.HexColor(
                            "#F3F4F6"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D1D5DB"
                        ),
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
            summary_table
        )

        story.append(
            Spacer(1, 5 * mm)
        )

        # =========================================================
        # CUSTOMER OVERVIEW
        # =========================================================

        story.append(
            Paragraph(
                "CUSTOMER OVERVIEW",
                section_style,
            )
        )

        customer_rows = [
            [
                paragraph(
                    "Customer",
                    center_style,
                ),
                paragraph(
                    "Phone",
                    center_style,
                ),
                paragraph(
                    "Email",
                    center_style,
                ),
                paragraph(
                    "Invoices",
                    center_style,
                ),
                paragraph(
                    "Purchases",
                    center_style,
                ),
                paragraph(
                    "Paid",
                    center_style,
                ),
                paragraph(
                    "Balance",
                    center_style,
                ),
            ]
        ]

        for customer in customers:
            customer_sales = [
                sale
                for sale in sales
                if sale.customer_id
                == customer.id
            ]

            purchases = sum(
                (
                    Decimal(
                        sale.total or 0
                    )
                    for sale in customer_sales
                ),
                Decimal("0"),
            )

            paid = sum(
                (
                    Decimal(
                        sale.amount_paid or 0
                    )
                    for sale in customer_sales
                ),
                Decimal("0"),
            )

            balance = sum(
                (
                    max(
                        Decimal(
                            sale.total or 0
                        )
                        - Decimal(
                            sale.amount_paid or 0
                        ),
                        Decimal("0"),
                    )
                    for sale in customer_sales
                ),
                Decimal("0"),
            )

            customer_rows.append(
                [
                    paragraph(
                        customer.name
                    ),
                    paragraph(
                        customer.phone
                        or "-"
                    ),
                    paragraph(
                        customer.email
                        or "-"
                    ),
                    paragraph(
                        str(
                            len(
                                customer_sales
                            )
                        ),
                        center_style,
                    ),
                    paragraph(
                        money(
                            purchases
                        ),
                        right_style,
                    ),
                    paragraph(
                        money(
                            paid
                        ),
                        right_style,
                    ),
                    paragraph(
                        money(
                            balance
                        ),
                        right_style,
                    ),
                ]
            )

        if len(customer_rows) > 1:
            customer_table = Table(
                customer_rows,
                colWidths=[
                    30 * mm,
                    24 * mm,
                    35 * mm,
                    17 * mm,
                    29 * mm,
                    29 * mm,
                    29 * mm,
                ],
                repeatRows=1,
            )

            customer_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#1F2937"
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
                            0.3,
                            colors.HexColor(
                                "#D1D5DB"
                            ),
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                colors.white,
                                colors.HexColor(
                                    "#F9FAFB"
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
                customer_table
            )
        else:
            story.append(
                Paragraph(
                    "No customers found for the selected period.",
                    normal_style,
                )
            )

        # =========================================================
        # SALES TRANSACTIONS
        # =========================================================

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "SALES TRANSACTIONS",
                section_style,
            )
        )

        sales_rows = [
            [
                paragraph(
                    "Date",
                    center_style,
                ),
                paragraph(
                    "Invoice",
                    center_style,
                ),
                paragraph(
                    "Customer",
                    center_style,
                ),
                paragraph(
                    "Method",
                    center_style,
                ),
                paragraph(
                    "Status",
                    center_style,
                ),
                paragraph(
                    "Total",
                    center_style,
                ),
                paragraph(
                    "Paid",
                    center_style,
                ),
                paragraph(
                    "Balance",
                    center_style,
                ),
            ]
        ]

        for sale in sales:
            balance = max(
                Decimal(
                    sale.total or 0
                )
                - Decimal(
                    sale.amount_paid or 0
                ),
                Decimal("0"),
            )

            customer_name = (
                sale.customer.name
                if sale.customer
                else "Walk-in Customer"
            )

            sales_rows.append(
                [
                    paragraph(
                        date_text(
                            sale.date
                        ),
                        center_style,
                    ),
                    paragraph(
                        sale.invoice_no,
                        center_style,
                    ),
                    paragraph(
                        customer_name
                    ),
                    paragraph(
                        sale.get_payment_method_display(),
                        center_style,
                    ),
                    paragraph(
                        sale.get_payment_status_display(),
                        center_style,
                    ),
                    paragraph(
                        money(
                            sale.total
                        ),
                        right_style,
                    ),
                    paragraph(
                        money(
                            sale.amount_paid
                        ),
                        right_style,
                    ),
                    paragraph(
                        money(
                            balance
                        ),
                        right_style,
                    ),
                ]
            )

        if len(sales_rows) > 1:
            sales_table = Table(
                sales_rows,
                colWidths=[
                    20 * mm,
                    25 * mm,
                    35 * mm,
                    23 * mm,
                    23 * mm,
                    28 * mm,
                    28 * mm,
                    28 * mm,
                ],
                repeatRows=1,
            )

            sales_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#1F2937"
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
                            0.3,
                            colors.HexColor(
                                "#D1D5DB"
                            ),
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                colors.white,
                                colors.HexColor(
                                    "#F9FAFB"
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
                sales_table
            )
        else:
            story.append(
                Paragraph(
                    "No sales transactions found for the selected period.",
                    normal_style,
                )
            )

        # =========================================================
        # PAYMENT TRANSACTIONS
        # =========================================================

        story.append(
            Spacer(1, 6 * mm)
        )

        story.append(
            Paragraph(
                "PAYMENT TRANSACTIONS",
                section_style,
            )
        )

        payment_rows = [
            [
                paragraph(
                    "Date",
                    center_style,
                ),
                paragraph(
                    "Invoice",
                    center_style,
                ),
                paragraph(
                    "Customer",
                    center_style,
                ),
                paragraph(
                    "Method",
                    center_style,
                ),
                paragraph(
                    "Reference",
                    center_style,
                ),
                paragraph(
                    "Amount",
                    center_style,
                ),
            ]
        ]

        for payment in payments:
            customer_name = (
                payment.sale.customer.name
                if payment.sale
                and payment.sale.customer
                else "Walk-in Customer"
            )

            payment_rows.append(
                [
                    paragraph(
                        date_text(
                            payment.date
                        ),
                        center_style,
                    ),
                    paragraph(
                        payment.sale.invoice_no
                        if payment.sale
                        else "-",
                        center_style,
                    ),
                    paragraph(
                        customer_name
                    ),
                    paragraph(
                        payment.get_payment_method_display(),
                        center_style,
                    ),
                    paragraph(
                        payment.reference
                        or "-"
                    ),
                    paragraph(
                        money(
                            payment.amount
                        ),
                        right_style,
                    ),
                ]
            )

        if len(payment_rows) > 1:
            payment_table = Table(
                payment_rows,
                colWidths=[
                    22 * mm,
                    27 * mm,
                    42 * mm,
                    27 * mm,
                    37 * mm,
                    30 * mm,
                ],
                repeatRows=1,
            )

            payment_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#1F2937"
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
                            0.3,
                            colors.HexColor(
                                "#D1D5DB"
                            ),
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                colors.white,
                                colors.HexColor(
                                    "#F9FAFB"
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
                payment_table
            )
        else:
            story.append(
                Paragraph(
                    "No payment transactions found for the selected period.",
                    normal_style,
                )
            )

        # =========================================================
        # CUSTOMER STATEMENTS
        # =========================================================

        for customer in customers:
            customer_sales = [
                sale
                for sale in sales
                if sale.customer_id
                == customer.id
            ]

            if not customer_sales:
                continue

            story.append(
                PageBreak()
            )

            story.append(
                Paragraph(
                    (
                        "CUSTOMER STATEMENT: "
                        f"{safe(customer.name).upper()}"
                    ),
                    section_style,
                )
            )

            customer_info = [
                [
                    paragraph(
                        "<b>Customer</b>",
                        normal_style,
                    ),
                    paragraph(
                        customer.name,
                        normal_style,
                    ),
                    paragraph(
                        "<b>Phone</b>",
                        normal_style,
                    ),
                    paragraph(
                        customer.phone
                        or "-",
                        normal_style,
                    ),
                ],
                [
                    paragraph(
                        "<b>Email</b>",
                        normal_style,
                    ),
                    paragraph(
                        customer.email
                        or "-",
                        normal_style,
                    ),
                    paragraph(
                        "<b>Address</b>",
                        normal_style,
                    ),
                    paragraph(
                        customer.address
                        or "-",
                        normal_style,
                    ),
                ],
            ]

            customer_info_table = Table(
                customer_info,
                colWidths=[
                    25 * mm,
                    65 * mm,
                    25 * mm,
                    65 * mm,
                ],
            )

            customer_info_table.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.3,
                            colors.HexColor(
                                "#D1D5DB"
                            ),
                        ),
                        (
                            "BACKGROUND",
                            (0, 0),
                            (0, -1),
                            colors.HexColor(
                                "#F3F4F6"
                            ),
                        ),
                        (
                            "BACKGROUND",
                            (2, 0),
                            (2, -1),
                            colors.HexColor(
                                "#F3F4F6"
                            ),
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
                customer_info_table
            )

            story.append(
                Spacer(1, 4 * mm)
            )

            customer_total = sum(
                (
                    Decimal(
                        sale.total or 0
                    )
                    for sale in customer_sales
                ),
                Decimal("0"),
            )

            customer_paid = sum(
                (
                    Decimal(
                        sale.amount_paid or 0
                    )
                    for sale in customer_sales
                ),
                Decimal("0"),
            )

            customer_balance = sum(
                (
                    max(
                        Decimal(
                            sale.total or 0
                        )
                        - Decimal(
                            sale.amount_paid or 0
                        ),
                        Decimal("0"),
                    )
                    for sale in customer_sales
                ),
                Decimal("0"),
            )

            statement_summary = Table(
                [
                    [
                        paragraph(
                            "TOTAL PURCHASES",
                            center_style,
                        ),
                        paragraph(
                            "TOTAL PAID",
                            center_style,
                        ),
                        paragraph(
                            "OUTSTANDING",
                            center_style,
                        ),
                    ],
                    [
                        paragraph(
                            money(
                                customer_total
                            ),
                            summary_value_style(
                                "CS1"
                            ),
                        ),
                        paragraph(
                            money(
                                customer_paid
                            ),
                            summary_value_style(
                                "CS2"
                            ),
                        ),
                        paragraph(
                            money(
                                customer_balance
                            ),
                            summary_value_style(
                                "CS3"
                            ),
                        ),
                    ],
                ],
                colWidths=[
                    60 * mm,
                    60 * mm,
                    60 * mm,
                ],
            )

            statement_summary.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#F3F4F6"
                            ),
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.35,
                            colors.HexColor(
                                "#D1D5DB"
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
                statement_summary
            )

            story.append(
                Spacer(1, 4 * mm)
            )

            statement_rows = [
                [
                    paragraph(
                        "Date",
                        center_style,
                    ),
                    paragraph(
                        "Invoice",
                        center_style,
                    ),
                    paragraph(
                        "Description",
                        center_style,
                    ),
                    paragraph(
                        "Total",
                        center_style,
                    ),
                    paragraph(
                        "Paid",
                        center_style,
                    ),
                    paragraph(
                        "Balance",
                        center_style,
                    ),
                    paragraph(
                        "Status",
                        center_style,
                    ),
                ]
            ]

            for sale in customer_sales:
                balance = max(
                    Decimal(
                        sale.total or 0
                    )
                    - Decimal(
                        sale.amount_paid or 0
                    ),
                    Decimal("0"),
                )

                products = ", ".join(
                    item.product
                    for item in sale.items.all()
                )

                statement_rows.append(
                    [
                        paragraph(
                            date_text(
                                sale.date
                            ),
                            center_style,
                        ),
                        paragraph(
                            sale.invoice_no,
                            center_style,
                        ),
                        paragraph(
                            products
                            or "Sale"
                        ),
                        paragraph(
                            money(
                                sale.total
                            ),
                            right_style,
                        ),
                        paragraph(
                            money(
                                sale.amount_paid
                            ),
                            right_style,
                        ),
                        paragraph(
                            money(
                                balance
                            ),
                            right_style,
                        ),
                        paragraph(
                            sale.get_payment_status_display(),
                            center_style,
                        ),
                    ]
                )

            statement_table = Table(
                statement_rows,
                colWidths=[
                    20 * mm,
                    25 * mm,
                    48 * mm,
                    29 * mm,
                    29 * mm,
                    29 * mm,
                    25 * mm,
                ],
                repeatRows=1,
            )

            statement_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#1F2937"
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
                            0.3,
                            colors.HexColor(
                                "#D1D5DB"
                            ),
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                colors.white,
                                colors.HexColor(
                                    "#F9FAFB"
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
                statement_table
            )

        # =========================================================
        # BUILD PDF
        # =========================================================

        doc.build(
            story,
            onFirstPage=add_page_footer,
            onLaterPages=add_page_footer,
        )

        return response