from datetime import datetime
from decimal import Decimal
from xml.sax.saxutils import escape

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
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ..models import Expense


class ExpensePDFReportView(APIView):
    """
    Generate a professional PDF expense report
    for a selected date range.

    Endpoint:
        GET /api/reports/expenses/pdf/

    Parameters:
        from_date=YYYY-MM-DD
        to_date=YYYY-MM-DD

    Example:
        /api/reports/expenses/pdf/
        ?from_date=2026-10-01
        &to_date=2026-10-03

    The PDF is returned as an inline response so that
    the browser can display it instead of downloading it
    automatically.
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    # =========================================================
    # GET
    # =========================================================

    def get(self, request, *args, **kwargs):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        # =====================================================
        # VALIDATE FROM DATE
        # =====================================================

        if not from_date:
            return HttpResponse(
                "from_date is required.",
                status=400,
                content_type="text/plain",
            )

        # =====================================================
        # VALIDATE TO DATE
        # =====================================================

        if not to_date:
            return HttpResponse(
                "to_date is required.",
                status=400,
                content_type="text/plain",
            )

        # =====================================================
        # PARSE DATES
        # =====================================================

        try:
            start_date = datetime.strptime(
                from_date,
                "%Y-%m-%d",
            ).date()

            end_date = datetime.strptime(
                to_date,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return HttpResponse(
                "Invalid date format. Use YYYY-MM-DD.",
                status=400,
                content_type="text/plain",
            )

        # =====================================================
        # VALIDATE DATE RANGE
        # =====================================================

        if start_date > end_date:
            return HttpResponse(
                "from_date cannot be after to_date.",
                status=400,
                content_type="text/plain",
            )

        # =====================================================
        # GET EXPENSES
        # =====================================================

        expenses = (
            Expense.objects
            .filter(
                date__gte=start_date,
                date__lte=end_date,
            )
            .order_by(
                "date",
                "id",
            )
        )

        # Convert queryset to list so it is evaluated once
        expenses = list(expenses)

        # =====================================================
        # CALCULATE TOTALS
        # =====================================================

        total_expenses = sum(
            (
                Decimal(str(expense.amount or 0))
                for expense in expenses
            ),
            Decimal("0.00"),
        )

        record_count = len(expenses)

        # =====================================================
        # PDF FILE NAME
        # =====================================================

        filename = (
            f"kukufarm-expense-report-"
            f"{from_date}-to-{to_date}.pdf"
        )

        # =====================================================
        # HTTP RESPONSE
        # =====================================================

        response = HttpResponse(
            content_type="application/pdf"
        )

        # IMPORTANT:
        # "inline" tells the browser to display the PDF
        # instead of forcing a download.

        response["Content-Disposition"] = (
            f'inline; filename="{filename}"'
        )

        # =====================================================
        # PDF DOCUMENT
        # =====================================================

        document = SimpleDocTemplate(
            response,
            pagesize=A4,

            rightMargin=15 * mm,
            leftMargin=15 * mm,

            topMargin=18 * mm,
            bottomMargin=20 * mm,

            title="KukuFarm Expense Report",
            author="KukuFarm Farming Management System",
            subject="Farm Expense Report",
        )

        # =====================================================
        # STYLES
        # =====================================================

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6c757d"),
            spaceAfter=3 * mm,
        )

        section_style = ParagraphStyle(
            "ReportSection",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
            textColor=colors.HexColor("#212529"),
        )

        normal_style = ParagraphStyle(
            "ReportNormal",
            parent=styles["Normal"],
            fontSize=8.2,
            leading=10,
        )

        center_style = ParagraphStyle(
            "ReportCenter",
            parent=normal_style,
            alignment=TA_CENTER,
        )

        right_style = ParagraphStyle(
            "ReportRight",
            parent=normal_style,
            alignment=TA_RIGHT,
        )

        small_style = ParagraphStyle(
            "ReportSmall",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6c757d"),
        )

        # =====================================================
        # STORY
        # =====================================================

        story = []

        # =====================================================
        # HEADER
        # =====================================================

        story.append(
            Paragraph(
                "KUKUFARM",
                title_style,
            )
        )

        story.append(
            Paragraph(
                "Farming Management System",
                subtitle_style,
            )
        )

        story.append(
            Paragraph(
                "EXPENSE REPORT",
                title_style,
            )
        )

        # =====================================================
        # REPORT PERIOD
        # =====================================================

        period_text = (
            f"<b>Report Period:</b> "
            f"{start_date.strftime('%d %B %Y')} "
            f"to "
            f"{end_date.strftime('%d %B %Y')}"
        )

        story.append(
            Paragraph(
                period_text,
                subtitle_style,
            )
        )

        # =====================================================
        # GENERATED DATE
        # =====================================================

        generated_at = timezone.localtime(
            timezone.now()
        )

        generated_text = (
            f"<b>Generated:</b> "
            f"{generated_at.strftime('%d %B %Y %H:%M')}"
        )

        story.append(
            Paragraph(
                generated_text,
                subtitle_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        # =====================================================
        # SUMMARY
        # =====================================================

        story.append(
            Paragraph(
                "Expense Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "<b>Total Records</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Total Expenses</b>",
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    str(record_count),
                    normal_style,
                ),
                Paragraph(
                    f"TZS {total_expenses:,.2f}",
                    right_style,
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                80 * mm,
                80 * mm,
            ],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#f2f2f2"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#cccccc"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
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

        story.append(summary_table)

        story.append(
            Spacer(
                1,
                6 * mm,
            )
        )

        # =====================================================
        # EXPENSE DETAILS
        # =====================================================

        story.append(
            Paragraph(
                "Expense Details",
                section_style,
            )
        )

        # =====================================================
        # TABLE HEADER
        # =====================================================

        table_data = [
            [
                Paragraph(
                    "<b>#</b>",
                    center_style,
                ),
                Paragraph(
                    "<b>Date</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Category</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Description</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Payment</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Amount (TZS)</b>",
                    right_style,
                ),
            ]
        ]

        # =====================================================
        # EXPENSE ROWS
        # =====================================================

        for index, expense in enumerate(
            expenses,
            start=1,
        ):
            # ---------------------------------------------
            # Payment method
            # ---------------------------------------------

            payment_method = (
                getattr(
                    expense,
                    "payment_method",
                    "",
                )
                or getattr(
                    expense,
                    "payment",
                    "",
                )
                or "-"
            )

            # ---------------------------------------------
            # Safe text values
            # ---------------------------------------------

            category = escape(
                str(
                    expense.category
                    or "-"
                )
            )

            description = escape(
                str(
                    expense.description
                    or "-"
                )
            )

            payment = escape(
                str(payment_method)
            )

            # ---------------------------------------------
            # Date
            # ---------------------------------------------

            expense_date = (
                expense.date.strftime(
                    "%d/%m/%Y"
                )
                if expense.date
                else "-"
            )

            # ---------------------------------------------
            # Amount
            # ---------------------------------------------

            amount = Decimal(
                str(
                    expense.amount
                    or 0
                )
            )

            table_data.append(
                [
                    Paragraph(
                        str(index),
                        center_style,
                    ),

                    Paragraph(
                        expense_date,
                        normal_style,
                    ),

                    Paragraph(
                        category,
                        normal_style,
                    ),

                    Paragraph(
                        description,
                        normal_style,
                    ),

                    Paragraph(
                        payment,
                        normal_style,
                    ),

                    Paragraph(
                        f"{amount:,.2f}",
                        right_style,
                    ),
                ]
            )

        # =====================================================
        # EMPTY REPORT
        # =====================================================

        if record_count == 0:
            table_data.append(
                [
                    "",
                    "",
                    Paragraph(
                        "No expenses found for the selected date range.",
                        center_style,
                    ),
                    "",
                    "",
                    "",
                ]
            )

        # =====================================================
        # TOTAL ROW
        # =====================================================

        table_data.append(
            [
                "",
                "",
                "",
                "",
                Paragraph(
                    "<b>TOTAL</b>",
                    right_style,
                ),
                Paragraph(
                    f"<b>{total_expenses:,.2f}</b>",
                    right_style,
                ),
            ]
        )

        # =====================================================
        # EXPENSE TABLE
        # =====================================================

        expense_table = Table(
            table_data,
            colWidths=[
                10 * mm,
                25 * mm,
                30 * mm,
                60 * mm,
                25 * mm,
                30 * mm,
            ],
            repeatRows=1,
            repeatCols=0,
        )

        expense_table.setStyle(
            TableStyle(
                [
                    # -------------------------------------
                    # Header
                    # -------------------------------------

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#212529"),
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),

                    # -------------------------------------
                    # Grid
                    # -------------------------------------

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#cccccc"),
                    ),

                    # -------------------------------------
                    # Alignment
                    # -------------------------------------

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),

                    # -------------------------------------
                    # Padding
                    # -------------------------------------

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
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

                    # -------------------------------------
                    # Total row
                    # -------------------------------------

                    (
                        "BACKGROUND",
                        (0, -1),
                        (-1, -1),
                        colors.HexColor("#f2f2f2"),
                    ),

                    (
                        "LINEABOVE",
                        (0, -1),
                        (-1, -1),
                        1,
                        colors.HexColor("#212529"),
                    ),
                ]
            )
        )

        story.append(
            expense_table
        )

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        # =====================================================
        # FOOTER INFORMATION
        # =====================================================

        story.append(
            Paragraph(
                "KukuFarm Farming Management System",
                small_style,
            )
        )

        story.append(
            Paragraph(
                "This report was generated electronically.",
                small_style,
            )
        )

        # =====================================================
        # BUILD PDF
        # =====================================================

        document.build(
            story,
            onFirstPage=self._add_page_footer,
            onLaterPages=self._add_page_footer,
        )

        return response

    # =========================================================
    # PAGE FOOTER
    # =========================================================

    @staticmethod
    def _add_page_footer(
        canvas,
        document,
    ):
        """
        Add page number and system name
        to every PDF page.
        """

        canvas.saveState()

        page_number = canvas.getPageNumber()

        canvas.setFont(
            "Helvetica",
            7,
        )

        canvas.setFillColor(
            colors.HexColor("#6c757d")
        )

        canvas.drawString(
            15 * mm,
            10 * mm,
            "KukuFarm Farming Management System",
        )

        canvas.drawRightString(
            A4[0] - (15 * mm),
            10 * mm,
            f"Page {page_number}",
        )

        canvas.restoreState()