from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
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
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ..models import Expense
from apps.settings.models import FarmSettings


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

    Features:
        - Farm settings
        - Farm logo watermark
        - Farm contact information
        - Configurable date format
        - Farm timezone
        - Expense summary
        - Expense details
        - Total expenses
        - Page numbers
        - Generated timestamp
        - Inline PDF response
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def escape_text(value):
        """
        Safely escape text before passing it
        to ReportLab Paragraph.
        """
        if value is None:
            return ""

        return escape(str(value))

    @staticmethod
    def to_decimal(value):
        """
        Safely convert a numeric value to Decimal.

        Handles:
            - Decimal
            - float
            - int
            - string
            - None
        """
        if value is None:
            return Decimal("0")

        try:
            return Decimal(str(value))

        except (
            TypeError,
            ValueError,
            ArithmeticError,
        ):
            return Decimal("0")

    @staticmethod
    def parse_date(value):
        """
        Parse YYYY-MM-DD date.
        """
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
    def get_farm_timezone(farm_settings):
        """
        Get timezone configured in FarmSettings.

        Falls back to Africa/Dar_es_Salaam.
        """

        timezone_name = getattr(
            farm_settings,
            "timezone",
            "Africa/Dar_es_Salaam",
        )

        try:
            return ZoneInfo(
                timezone_name
                or "Africa/Dar_es_Salaam"
            )

        except ZoneInfoNotFoundError:
            return ZoneInfo(
                "Africa/Dar_es_Salaam"
            )

    @staticmethod
    def format_report_date(
        value,
        date_format=None,
    ):
        """
        Format a date according to FarmSettings.date_format.

        Supported formats:
            DD/MM/YYYY
            DD-MM-YYYY
            DD.MM.YYYY
            MM/DD/YYYY
            MM-DD-YYYY
            YYYY/MM/DD
            YYYY-MM-DD
            YYYY.MM.DD
        """

        if not value:
            return ""

        # datetime -> date
        if isinstance(value, datetime):
            value = value.date()

        configured_format = str(
            date_format or "DD/MM/YYYY"
        ).strip().upper()

        format_map = {
            "DD/MM/YYYY": "%d/%m/%Y",
            "DD-MM-YYYY": "%d-%m-%Y",
            "DD.MM.YYYY": "%d.%m.%Y",
            "MM/DD/YYYY": "%m/%d/%Y",
            "MM-DD-YYYY": "%m-%d-%Y",
            "YYYY/MM/DD": "%Y/%m/%d",
            "YYYY-MM-DD": "%Y-%m-%d",
            "YYYY.MM.DD": "%Y.%m.%d",
        }

        python_format = format_map.get(
            configured_format,
            "%d/%m/%Y",
        )

        if hasattr(value, "strftime"):
            return value.strftime(
                python_format
            )

        if isinstance(value, str):
            value = value.strip()

            input_formats = (
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%Y/%m/%d",
                "%Y.%m.%d",
                "%d.%m.%Y",
            )

            for input_format in input_formats:
                try:
                    parsed_date = datetime.strptime(
                        value,
                        input_format,
                    ).date()

                    return parsed_date.strftime(
                        python_format
                    )

                except ValueError:
                    continue

            return value

        return str(value)

    # =========================================================
    # PAGE FOOTER + WATERMARK
    # =========================================================

    @staticmethod
    def _add_page_footer(
        canvas,
        document,
    ):
        """
        Add:
            - Farm logo watermark
            - Footer line
            - Farm name
            - Generated timestamp
            - Page number
        """

        canvas.saveState()

        page_width, page_height = A4

        # =====================================================
        # FARM LOGO WATERMARK
        # =====================================================

        logo_path = getattr(
            document,
            "_logo_path",
            None,
        )

        if logo_path:
            try:
                logo = ImageReader(
                    logo_path
                )

                logo_width = 100 * mm
                logo_height = 100 * mm

                x = (
                    page_width - logo_width
                ) / 2

                y = (
                    page_height - logo_height
                ) / 2

                # Very light watermark
                try:
                    canvas.setFillAlpha(
                        0.07
                    )
                except AttributeError:
                    pass

                canvas.drawImage(
                    logo,
                    x,
                    y,
                    width=logo_width,
                    height=logo_height,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )

                # Restore opacity
                try:
                    canvas.setFillAlpha(
                        1
                    )
                except AttributeError:
                    pass

            except (
                ValueError,
                AttributeError,
                OSError,
            ):
                # Continue generating PDF
                # if logo cannot be loaded.
                pass

        # =====================================================
        # FOOTER
        # =====================================================

        farm_name = getattr(
            document,
            "_farm_name",
            "KukuFarm",
        )

        generated_text = getattr(
            document,
            "_generated_text",
            "",
        )

        # Footer line
        canvas.setStrokeColor(
            colors.HexColor("#D9D9D9")
        )

        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            15 * mm,
            13 * mm,
            page_width - 15 * mm,
            13 * mm,
        )

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        canvas.setFillColor(
            colors.HexColor("#666666")
        )

        # Farm name
        canvas.drawString(
            15 * mm,
            8 * mm,
            str(farm_name),
        )

        # Generated timestamp
        canvas.drawCentredString(
            page_width / 2,
            8 * mm,
            generated_text,
        )

        # Page number
        canvas.drawRightString(
            page_width - 15 * mm,
            8 * mm,
            f"Page {canvas.getPageNumber()}",
        )

        canvas.restoreState()

    # =========================================================
    # GET
    # =========================================================

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        # =====================================================
        # QUERY PARAMETERS
        # =====================================================

        from_date = request.query_params.get(
            "from_date"
        )

        to_date = request.query_params.get(
            "to_date"
        )

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

        start_date = self.parse_date(
            from_date
        )

        end_date = self.parse_date(
            to_date
        )

        if not start_date:
            return HttpResponse(
                "Invalid from_date format. "
                "Use YYYY-MM-DD.",
                status=400,
                content_type="text/plain",
            )

        if not end_date:
            return HttpResponse(
                "Invalid to_date format. "
                "Use YYYY-MM-DD.",
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
        # FARM SETTINGS
        # =====================================================

        farm_settings = (
            FarmSettings.objects
            .order_by("id")
            .first()
        )

        if farm_settings:
            farm_name = (
                farm_settings.farm_name
                or "KukuFarm"
            )
        else:
            farm_name = "KukuFarm"

        date_format = getattr(
            farm_settings,
            "date_format",
            "DD/MM/YYYY",
        )

        farm_timezone = (
            self.get_farm_timezone(
                farm_settings
            )
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

        # Evaluate once
        expenses = list(
            expenses
        )

        # =====================================================
        # CALCULATE TOTALS
        # =====================================================

        total_expenses = Decimal(
            "0.00"
        )

        for expense in expenses:
            total_expenses += (
                self.to_decimal(
                    expense.amount
                )
            )

        record_count = len(
            expenses
        )

        # =====================================================
        # GENERATED TIME
        # =====================================================

        generated_at = (
            timezone.now()
            .astimezone(
                farm_timezone
            )
        )

        generated_text = (
            "Generated: "
            + generated_at.strftime(
                "%d/%m/%Y %H:%M"
            )
        )

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

        response[
            "Content-Disposition"
        ] = (
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
            title=(
                f"{farm_name} - Expense Report"
            ),
            author=str(farm_name),
            subject="Farm Expense Report",
        )

        # =====================================================
        # DOCUMENT METADATA
        # =====================================================

        document._farm_name = str(
            farm_name
        )

        document._generated_text = (
            generated_text
        )

        document._logo_path = None

        # Get farm logo
        if farm_settings:
            logo_file = getattr(
                farm_settings,
                "logo",
                None,
            )

            if logo_file:
                try:
                    document._logo_path = (
                        logo_file.path
                    )

                except (
                    ValueError,
                    AttributeError,
                    OSError,
                ):
                    document._logo_path = None

        # =====================================================
        # STYLES
        # =====================================================

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
            textColor=colors.HexColor(
                "#1F2937"
            ),
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#6c757d"
            ),
            spaceAfter=3 * mm,
        )

        section_style = ParagraphStyle(
            "ReportSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
            textColor=colors.HexColor(
                "#212529"
            ),
        )

        normal_style = ParagraphStyle(
            "ReportNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
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
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#6c757d"
            ),
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
                self.escape_text(
                    farm_name
                ),
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
            "<b>Report Period:</b> "
            f"{self.format_report_date(start_date, date_format)} "
            "to "
            f"{self.format_report_date(end_date, date_format)}"
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

        generated_body_text = (
            "<b>Generated:</b> "
            + generated_at.strftime(
                "%d %B %Y %H:%M"
            )
        )

        story.append(
            Paragraph(
                generated_body_text,
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
        # FARM INFORMATION
        # =====================================================

        if farm_settings:
            farm_information = []

            owner_name = getattr(
                farm_settings,
                "owner_name",
                "",
            )

            phone = getattr(
                farm_settings,
                "phone",
                "",
            )

            email = getattr(
                farm_settings,
                "email",
                "",
            )

            location = getattr(
                farm_settings,
                "location",
                "",
            )

            address = getattr(
                farm_settings,
                "address",
                "",
            )

            if owner_name:
                farm_information.append(
                    f"Owner: {owner_name}"
                )

            if phone:
                farm_information.append(
                    f"Phone: {phone}"
                )

            if email:
                farm_information.append(
                    f"Email: {email}"
                )

            if location:
                farm_information.append(
                    f"Location: {location}"
                )

            if address:
                farm_information.append(
                    f"Address: {address}"
                )

            if farm_information:
                story.append(
                    Paragraph(
                        self.escape_text(
                            " | ".join(
                                farm_information
                            )
                        ),
                        small_style,
                    )
                )

                story.append(
                    Spacer(
                        1,
                        3 * mm,
                    )
                )

        # =====================================================
        # EXPENSE SUMMARY
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
                    center_style,
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
                        colors.HexColor(
                            "#f2f2f2"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor(
                            "#cccccc"
                        ),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
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

        story.append(
            summary_table
        )

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
            # -------------------------------------------------
            # PAYMENT METHOD
            # -------------------------------------------------

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

            # -------------------------------------------------
            # SAFE TEXT VALUES
            # -------------------------------------------------

            category = self.escape_text(
                getattr(
                    expense,
                    "category",
                    None,
                )
                or "-"
            )

            description = self.escape_text(
                getattr(
                    expense,
                    "description",
                    None,
                )
                or "-"
            )

            payment = self.escape_text(
                payment_method
            )

            # -------------------------------------------------
            # DATE
            # -------------------------------------------------

            expense_date = (
                self.format_report_date(
                    expense.date,
                    date_format,
                )
                if expense.date
                else "-"
            )

            # -------------------------------------------------
            # AMOUNT
            # -------------------------------------------------

            amount = self.to_decimal(
                expense.amount
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
                    # -------------------------------------------------
                    # HEADER
                    # -------------------------------------------------

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#212529"
                        ),
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),

                    # -------------------------------------------------
                    # GRID
                    # -------------------------------------------------

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor(
                            "#cccccc"
                        ),
                    ),

                    # -------------------------------------------------
                    # ALIGNMENT
                    # -------------------------------------------------

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),

                    # -------------------------------------------------
                    # PADDING
                    # -------------------------------------------------

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

                    # -------------------------------------------------
                    # ALTERNATING ROWS
                    # -------------------------------------------------

                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -2),
                        [
                            colors.white,
                            colors.HexColor(
                                "#f8f9fa"
                            ),
                        ],
                    ),

                    # -------------------------------------------------
                    # TOTAL ROW
                    # -------------------------------------------------

                    (
                        "BACKGROUND",
                        (0, -1),
                        (-1, -1),
                        colors.HexColor(
                            "#f2f2f2"
                        ),
                    ),

                    (
                        "LINEABOVE",
                        (0, -1),
                        (-1, -1),
                        1,
                        colors.HexColor(
                            "#212529"
                        ),
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
        # REPORT NOTES
        # =====================================================

        story.append(
            Paragraph(
                "Report Notes",
                section_style,
            )
        )

        notes_text = (
            "This report contains expenses recorded "
            "within the selected date range. "
            "The total expense amount is calculated "
            "from the recorded expense amounts."
        )

        story.append(
            Paragraph(
                self.escape_text(
                    notes_text
                ),
                small_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        story.append(
            Paragraph(
                "This report was generated electronically "
                "by the KukuFarm Farming Management System.",
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