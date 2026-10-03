# apps/production/reports/views.py

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import permissions
from rest_framework.views import APIView

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
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

from ..models import EggProduction
from apps.settings.models import FarmSettings


class EggProductionPDFReportView(APIView):
    """
    Generate a professional PDF report for egg production.

    Endpoint:
        GET /api/production/reports/pdf/

    Optional query parameters:
        ?from_date=YYYY-MM-DD
        &to_date=YYYY-MM-DD
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    TRAY_SIZE = Decimal("30")

    # ------------------------------------------------------------------
    # FARM SETTINGS
    # ------------------------------------------------------------------

    def get_farm_settings(self):
        """
        Get the latest farm settings.

        The application normally uses one FarmSettings record.
        If multiple records exist, the most recently updated one
        will be used.
        """
        return (
            FarmSettings.objects
            .order_by("-updated_at", "-id")
            .first()
        )

    # ------------------------------------------------------------------
    # DATE FORMAT
    # ------------------------------------------------------------------

    def format_report_date(
        self,
        value,
        date_format=None,
    ):
        """
        Format date/datetime/string values using the farm's
        configured date format.

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

        # Convert datetime -> date
        if isinstance(value, datetime):
            value = value.date()

        configured_format = (
            str(date_format or "DD/MM/YYYY")
            .strip()
            .upper()
        )

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

        # date object
        if hasattr(value, "strftime"):
            return value.strftime(python_format)

        # string value
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

    # ------------------------------------------------------------------
    # TIMEZONE
    # ------------------------------------------------------------------

    def get_report_timezone(
        self,
        farm_settings,
    ):
        """
        Get timezone from farm settings.

        Falls back to Django's configured timezone.
        """

        if farm_settings:
            timezone_name = (
                getattr(
                    farm_settings,
                    "timezone",
                    None,
                )
                or ""
            ).strip()

            if timezone_name:
                try:
                    return ZoneInfo(timezone_name)

                except ZoneInfoNotFoundError:
                    pass

        return timezone.get_current_timezone()

    # ------------------------------------------------------------------
    # NUMBER FORMAT
    # ------------------------------------------------------------------

    def format_number(self, value):
        """
        Format numeric values with thousands separators.
        """

        if value is None:
            return "0"

        try:
            decimal_value = Decimal(str(value))

            if decimal_value == decimal_value.to_integral_value():
                return f"{int(decimal_value):,}"

            return f"{decimal_value:,.2f}"

        except Exception:
            return str(value)

    # ------------------------------------------------------------------
    # SAFE TEXT
    # ------------------------------------------------------------------

    def safe_text(self, value, fallback="—"):
        """
        Safely prepare dynamic text for ReportLab Paragraph.
        """

        if value is None:
            return fallback

        value = str(value).strip()

        if not value:
            return fallback

        return escape(value)

    # ------------------------------------------------------------------
    # PAGE FOOTER
    # ------------------------------------------------------------------

    @staticmethod
    def _add_page_footer(
        canvas,
        document,
    ):
        """
        Add footer to every PDF page.
        """

        canvas.saveState()

        page_width = landscape(A4)[0]

        farm_name = getattr(
            document,
            "_farm_name",
            "Farm Management System",
        )

        generated_text = getattr(
            document,
            "_generated_text",
            "",
        )

        canvas.setStrokeColor(
            colors.HexColor("#D9D9D9")
        )

        canvas.setLineWidth(0.5)

        canvas.line(
            15 * mm,
            12 * mm,
            page_width - 15 * mm,
            12 * mm,
        )

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        canvas.setFillColor(
            colors.HexColor("#666666")
        )

        canvas.drawString(
            15 * mm,
            7 * mm,
            farm_name,
        )

        canvas.drawCentredString(
            page_width / 2,
            7 * mm,
            generated_text,
        )

        canvas.drawRightString(
            page_width - 15 * mm,
            7 * mm,
            f"Page {canvas.getPageNumber()}",
        )

        canvas.restoreState()

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get(self, request):

        # --------------------------------------------------------------
        # FARM SETTINGS
        # --------------------------------------------------------------

        farm_settings = self.get_farm_settings()

        if farm_settings:

            farm_name = (
                getattr(
                    farm_settings,
                    "farm_name",
                    None,
                )
                or "Farm Management System"
            )

            owner_name = (
                getattr(
                    farm_settings,
                    "owner_name",
                    None,
                )
                or ""
            )

            phone = (
                getattr(
                    farm_settings,
                    "phone",
                    None,
                )
                or ""
            )

            email = (
                getattr(
                    farm_settings,
                    "email",
                    None,
                )
                or ""
            )

            location = (
                getattr(
                    farm_settings,
                    "location",
                    None,
                )
                or ""
            )

            address = (
                getattr(
                    farm_settings,
                    "address",
                    None,
                )
                or ""
            )

            currency = (
                getattr(
                    farm_settings,
                    "currency",
                    None,
                )
                or "TZS"
            )

            date_format = (
                getattr(
                    farm_settings,
                    "date_format",
                    None,
                )
                or "DD/MM/YYYY"
            )

        else:

            farm_name = "Farm Management System"
            owner_name = ""
            phone = ""
            email = ""
            location = ""
            address = ""
            currency = "TZS"
            date_format = "DD/MM/YYYY"

        # --------------------------------------------------------------
        # DATE PARAMETERS
        # --------------------------------------------------------------

        from_date_param = request.query_params.get(
            "from_date"
        )

        to_date_param = request.query_params.get(
            "to_date"
        )

        today = timezone.localdate()

        start_date = today
        end_date = today

        # --------------------------------------------------------------
        # FROM DATE
        # --------------------------------------------------------------

        if from_date_param:

            try:

                start_date = datetime.strptime(
                    from_date_param,
                    "%Y-%m-%d",
                ).date()

            except ValueError:

                return Response(
                    {
                        "detail": (
                            "Invalid from_date. "
                            "Use YYYY-MM-DD."
                        )
                    },
                    status=400,
                )

        # --------------------------------------------------------------
        # TO DATE
        # --------------------------------------------------------------

        if to_date_param:

            try:

                end_date = datetime.strptime(
                    to_date_param,
                    "%Y-%m-%d",
                ).date()

            except ValueError:

                return Response(
                    {
                        "detail": (
                            "Invalid to_date. "
                            "Use YYYY-MM-DD."
                        )
                    },
                    status=400,
                )

        # --------------------------------------------------------------
        # DATE RANGE VALIDATION
        # --------------------------------------------------------------

        if start_date > end_date:

            return Response(
                {
                    "detail": (
                        "from_date cannot be later "
                        "than to_date."
                    )
                },
                status=400,
            )

        # --------------------------------------------------------------
        # QUERY PRODUCTION
        # --------------------------------------------------------------

        production_records = (
            EggProduction.objects
            .select_related("flock")
            .filter(
                date__gte=start_date,
                date__lte=end_date,
            )
            .order_by(
                "date",
                "id",
            )
        )

        # --------------------------------------------------------------
        # CALCULATIONS
        # --------------------------------------------------------------

        total_records = production_records.count()

        total_eggs_collected = Decimal("0")
        total_broken_eggs = Decimal("0")
        total_rejected_eggs = Decimal("0")
        total_trays = Decimal("0")

        for record in production_records:

            total_eggs_collected += (
                record.eggs_collected
                or Decimal("0")
            )

            total_broken_eggs += (
                record.broken_eggs
                or Decimal("0")
            )

            total_rejected_eggs += (
                record.rejected_eggs
                or Decimal("0")
            )

            total_trays += (
                record.trays
                or Decimal("0")
            )

        # --------------------------------------------------------------
        # GOOD / LOST EGGS
        # --------------------------------------------------------------

        total_lost_eggs = (
            total_broken_eggs
            + total_rejected_eggs
        )

        total_good_eggs = max(
            Decimal("0"),
            total_eggs_collected
            - total_lost_eggs,
        )

        # --------------------------------------------------------------
        # GOOD TRAYS
        # --------------------------------------------------------------

        equivalent_good_trays = (
            total_good_eggs
            / self.TRAY_SIZE
        )

        # --------------------------------------------------------------
        # PERCENTAGES
        # --------------------------------------------------------------

        if total_eggs_collected > 0:

            good_egg_percentage = (
                total_good_eggs
                / total_eggs_collected
            ) * Decimal("100")

            loss_percentage = (
                total_lost_eggs
                / total_eggs_collected
            ) * Decimal("100")

        else:

            good_egg_percentage = Decimal("0")
            loss_percentage = Decimal("0")

        # --------------------------------------------------------------
        # AVERAGE DAILY PRODUCTION
        # --------------------------------------------------------------

        if total_records > 0:

            average_daily_production = (
                total_eggs_collected
                / Decimal(str(total_records))
            )

        else:

            average_daily_production = Decimal("0")

        # --------------------------------------------------------------
        # REPORT TIMEZONE
        # --------------------------------------------------------------

        report_timezone = self.get_report_timezone(
            farm_settings
        )

        generated_at = (
            timezone.now()
            .astimezone(report_timezone)
        )

        generated_text = (
            "Generated "
            + generated_at.strftime(
                "%d/%m/%Y %H:%M"
            )
        )

        # --------------------------------------------------------------
        # REPORT PERIOD
        # --------------------------------------------------------------

        formatted_start_date = (
            self.format_report_date(
                start_date,
                date_format,
            )
        )

        formatted_end_date = (
            self.format_report_date(
                end_date,
                date_format,
            )
        )

        report_period = (
            f"{self.safe_text(formatted_start_date)} "
            f"to "
            f"{self.safe_text(formatted_end_date)}"
        )

        # --------------------------------------------------------------
        # PDF RESPONSE
        # --------------------------------------------------------------

        filename = (
            "egg-production-report-"
            f"{start_date.isoformat()}-"
            f"to-{end_date.isoformat()}.pdf"
        )

        response = HttpResponse(
            content_type="application/pdf"
        )

        response[
            "Content-Disposition"
        ] = (
            f'inline; filename="{filename}"'
        )

        # --------------------------------------------------------------
        # PAGE
        # --------------------------------------------------------------

        page_size = landscape(A4)

        document = SimpleDocTemplate(
            response,
            pagesize=page_size,
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=17 * mm,
            title=(
                f"{farm_name} - "
                "Egg Production Report"
            ),
            author=str(farm_name),
        )

        # Store values for footer
        document._farm_name = str(
            farm_name
        )

        document._generated_text = (
            generated_text
        )

        # --------------------------------------------------------------
        # STYLES
        # --------------------------------------------------------------

        styles = getSampleStyleSheet()

        farm_title_style = ParagraphStyle(
            "FarmTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#1F2937"
            ),
            spaceAfter=2 * mm,
        )

        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#6B7280"
            ),
        )

        report_title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )

        section_style = ParagraphStyle(
            "Section",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor(
                "#1F2937"
            ),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )

        normal_style = ParagraphStyle(
            "NormalCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(
                "#374151"
            ),
        )

        small_style = ParagraphStyle(
            "Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor(
                "#4B5563"
            ),
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=8.5,
            alignment=TA_CENTER,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor(
                "#1F2937"
            ),
        )

        table_cell_center_style = ParagraphStyle(
            "TableCellCenter",
            parent=table_cell_style,
            alignment=TA_CENTER,
        )

        table_cell_right_style = ParagraphStyle(
            "TableCellRight",
            parent=table_cell_style,
            alignment=TA_RIGHT,
        )

        # --------------------------------------------------------------
        # STORY
        # --------------------------------------------------------------

        story = []

        # --------------------------------------------------------------
        # FARM HEADER
        # --------------------------------------------------------------

        story.append(
            Paragraph(
                self.safe_text(
                    farm_name
                ),
                farm_title_style,
            )
        )

        story.append(
            Paragraph(
                "Farming Management System",
                subtitle_style,
            )
        )

        story.append(
            Spacer(
                1,
                2 * mm,
            )
        )

        story.append(
            Paragraph(
                "EGG PRODUCTION REPORT",
                report_title_style,
            )
        )

        story.append(
            Paragraph(
                f"<b>Reporting Period:</b> "
                f"{report_period}",
                subtitle_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        # --------------------------------------------------------------
        # FARM INFORMATION
        # --------------------------------------------------------------

        farm_info_data = [
            [
                Paragraph(
                    "<b>Farm Name</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        farm_name
                    ),
                    small_style,
                ),
                Paragraph(
                    "<b>Owner</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        owner_name
                    ),
                    small_style,
                ),
            ],
            [
                Paragraph(
                    "<b>Phone</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        phone
                    ),
                    small_style,
                ),
                Paragraph(
                    "<b>Email</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        email
                    ),
                    small_style,
                ),
            ],
            [
                Paragraph(
                    "<b>Location</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        location
                    ),
                    small_style,
                ),
                Paragraph(
                    "<b>Address</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        address
                    ),
                    small_style,
                ),
            ],
            [
                Paragraph(
                    "<b>Currency</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        currency
                    ),
                    small_style,
                ),
                Paragraph(
                    "<b>Timezone</b>",
                    small_style,
                ),
                Paragraph(
                    self.safe_text(
                        getattr(
                            farm_settings,
                            "timezone",
                            "",
                        )
                        if farm_settings
                        else "",
                    ),
                    small_style,
                ),
            ],
        ]

        farm_info_table = Table(
            farm_info_data,
            colWidths=[
                28 * mm,
                72 * mm,
                25 * mm,
                72 * mm,
            ],
            repeatRows=0,
        )

        farm_info_table.setStyle(
            TableStyle(
                [
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
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor(
                            "#D1D5DB"
                        ),
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor(
                            "#E5E7EB"
                        ),
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
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
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
            farm_info_table
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        # --------------------------------------------------------------
        # PRODUCTION SUMMARY
        # --------------------------------------------------------------

        story.append(
            Paragraph(
                "Production Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "Production Records",
                    table_header_style,
                ),
                Paragraph(
                    "Eggs Collected",
                    table_header_style,
                ),
                Paragraph(
                    "Good Eggs",
                    table_header_style,
                ),
                Paragraph(
                    "Broken",
                    table_header_style,
                ),
                Paragraph(
                    "Rejected",
                    table_header_style,
                ),
                Paragraph(
                    "Total Trays",
                    table_header_style,
                ),
                Paragraph(
                    "Good Trays",
                    table_header_style,
                ),
                Paragraph(
                    "Good %",
                    table_header_style,
                ),
                Paragraph(
                    "Loss %",
                    table_header_style,
                ),
                Paragraph(
                    "Avg / Record",
                    table_header_style,
                ),
            ],
            [
                self.format_number(
                    total_records
                ),
                self.format_number(
                    total_eggs_collected
                ),
                self.format_number(
                    total_good_eggs
                ),
                self.format_number(
                    total_broken_eggs
                ),
                self.format_number(
                    total_rejected_eggs
                ),
                self.format_number(
                    total_trays
                ),
                self.format_number(
                    equivalent_good_trays
                ),
                f"{good_egg_percentage:.2f}%",
                f"{loss_percentage:.2f}%",
                self.format_number(
                    average_daily_production
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                25 * mm,
                28 * mm,
                28 * mm,
                23 * mm,
                23 * mm,
                25 * mm,
                25 * mm,
                22 * mm,
                22 * mm,
                28 * mm,
            ],
            repeatRows=1,
        )

        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#374151"
                        ),
                    ),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, 1),
                        colors.HexColor(
                            "#F9FAFB"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 1),
                        (-1, 1),
                        colors.HexColor(
                            "#111827"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
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
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, 1),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, 1),
                        (-1, 1),
                        8,
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

        # --------------------------------------------------------------
        # QUALITY SUMMARY
        # --------------------------------------------------------------

        story.append(
            Paragraph(
                "Egg Quality Summary",
                section_style,
            )
        )

        quality_data = [
            [
                Paragraph(
                    "Metric",
                    table_header_style,
                ),
                Paragraph(
                    "Quantity",
                    table_header_style,
                ),
                Paragraph(
                    "Percentage",
                    table_header_style,
                ),
            ],
            [
                Paragraph(
                    "Good Eggs",
                    table_cell_style,
                ),
                Paragraph(
                    self.format_number(
                        total_good_eggs
                    ),
                    table_cell_right_style,
                ),
                Paragraph(
                    f"{good_egg_percentage:.2f}%",
                    table_cell_center_style,
                ),
            ],
            [
                Paragraph(
                    "Broken Eggs",
                    table_cell_style,
                ),
                Paragraph(
                    self.format_number(
                        total_broken_eggs
                    ),
                    table_cell_right_style,
                ),
                Paragraph(
                    (
                        f"{(
                            total_broken_eggs
                            / total_eggs_collected
                            * Decimal('100')
                        ):.2f}%"
                        if total_eggs_collected
                        > 0
                        else "0.00%"
                    ),
                    table_cell_center_style,
                ),
            ],
            [
                Paragraph(
                    "Rejected Eggs",
                    table_cell_style,
                ),
                Paragraph(
                    self.format_number(
                        total_rejected_eggs
                    ),
                    table_cell_right_style,
                ),
                Paragraph(
                    (
                        f"{(
                            total_rejected_eggs
                            / total_eggs_collected
                            * Decimal('100')
                        ):.2f}%"
                        if total_eggs_collected
                        > 0
                        else "0.00%"
                    ),
                    table_cell_center_style,
                ),
            ],
            [
                Paragraph(
                    "Total Loss",
                    table_cell_style,
                ),
                Paragraph(
                    self.format_number(
                        total_lost_eggs
                    ),
                    table_cell_right_style,
                ),
                Paragraph(
                    f"{loss_percentage:.2f}%",
                    table_cell_center_style,
                ),
            ],
        ]

        quality_table = Table(
            quality_data,
            colWidths=[
                80 * mm,
                55 * mm,
                55 * mm,
            ],
            repeatRows=1,
        )

        quality_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#374151"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
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
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
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
            quality_table
        )

        # --------------------------------------------------------------
        # PRODUCTION DETAILS
        # --------------------------------------------------------------

        story.append(
            Paragraph(
                "Production Details",
                section_style,
            )
        )

        detail_data = [
            [
                Paragraph(
                    "#",
                    table_header_style,
                ),
                Paragraph(
                    "Date",
                    table_header_style,
                ),
                Paragraph(
                    "Flock",
                    table_header_style,
                ),
                Paragraph(
                    "Eggs<br/>Collected",
                    table_header_style,
                ),
                Paragraph(
                    "Broken",
                    table_header_style,
                ),
                Paragraph(
                    "Rejected",
                    table_header_style,
                ),
                Paragraph(
                    "Good Eggs",
                    table_header_style,
                ),
                Paragraph(
                    "Trays",
                    table_header_style,
                ),
                Paragraph(
                    "Good %",
                    table_header_style,
                ),
                Paragraph(
                    "Notes",
                    table_header_style,
                ),
            ]
        ]

        # --------------------------------------------------------------
        # DETAIL ROWS
        # --------------------------------------------------------------

        if production_records.exists():

            row_number = 1

            for record in production_records:

                collected = (
                    record.eggs_collected
                    or Decimal("0")
                )

                broken = (
                    record.broken_eggs
                    or Decimal("0")
                )

                rejected = (
                    record.rejected_eggs
                    or Decimal("0")
                )

                good_eggs = max(
                    Decimal("0"),
                    collected
                    - broken
                    - rejected,
                )

                if collected > 0:

                    good_percentage = (
                        good_eggs
                        / collected
                    ) * Decimal("100")

                else:

                    good_percentage = (
                        Decimal("0")
                    )

                flock_name = "—"

                if record.flock:

                    flock_name = (
                        getattr(
                            record.flock,
                            "name",
                            None,
                        )
                        or getattr(
                            record.flock,
                            "flock_name",
                            None,
                        )
                        or str(
                            record.flock
                        )
                    )

                notes = (
                    getattr(
                        record,
                        "notes",
                        None,
                    )
                    or "—"
                )

                detail_data.append(
                    [
                        Paragraph(
                            str(row_number),
                            table_cell_center_style,
                        ),
                        Paragraph(
                            self.safe_text(
                                self.format_report_date(
                                    record.date,
                                    date_format,
                                )
                            ),
                            table_cell_center_style,
                        ),
                        Paragraph(
                            self.safe_text(
                                flock_name
                            ),
                            table_cell_style,
                        ),
                        Paragraph(
                            self.format_number(
                                collected
                            ),
                            table_cell_right_style,
                        ),
                        Paragraph(
                            self.format_number(
                                broken
                            ),
                            table_cell_right_style,
                        ),
                        Paragraph(
                            self.format_number(
                                rejected
                            ),
                            table_cell_right_style,
                        ),
                        Paragraph(
                            self.format_number(
                                good_eggs
                            ),
                            table_cell_right_style,
                        ),
                        Paragraph(
                            self.format_number(
                                record.trays
                                or Decimal("0")
                            ),
                            table_cell_right_style,
                        ),
                        Paragraph(
                            f"{good_percentage:.2f}%",
                            table_cell_center_style,
                        ),
                        Paragraph(
                            self.safe_text(
                                notes
                            ),
                            table_cell_style,
                        ),
                    ]
                )

                row_number += 1

        else:

            detail_data.append(
                [
                    Paragraph(
                        "—",
                        table_cell_center_style,
                    ),
                    Paragraph(
                        "No production records found",
                        table_cell_center_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        # --------------------------------------------------------------
        # TOTAL ROW
        # --------------------------------------------------------------

        if production_records.exists():

            detail_data.append(
                [
                    Paragraph(
                        "",
                        table_cell_center_style,
                    ),
                    Paragraph(
                        "<b>TOTAL</b>",
                        table_cell_right_style,
                    ),
                    Paragraph(
                        "",
                        table_cell_style,
                    ),
                    Paragraph(
                        f"<b>{self.format_number(total_eggs_collected)}</b>",
                        table_cell_right_style,
                    ),
                    Paragraph(
                        f"<b>{self.format_number(total_broken_eggs)}</b>",
                        table_cell_right_style,
                    ),
                    Paragraph(
                        f"<b>{self.format_number(total_rejected_eggs)}</b>",
                        table_cell_right_style,
                    ),
                    Paragraph(
                        f"<b>{self.format_number(total_good_eggs)}</b>",
                        table_cell_right_style,
                    ),
                    Paragraph(
                        f"<b>{self.format_number(total_trays)}</b>",
                        table_cell_right_style,
                    ),
                    Paragraph(
                        f"<b>{good_egg_percentage:.2f}%</b>",
                        table_cell_center_style,
                    ),
                    Paragraph(
                        "",
                        table_cell_style,
                    ),
                ]
            )

        # --------------------------------------------------------------
        # DETAIL TABLE
        # --------------------------------------------------------------

        detail_table = Table(
            detail_data,
            colWidths=[
                9 * mm,
                25 * mm,
                35 * mm,
                25 * mm,
                19 * mm,
                20 * mm,
                25 * mm,
                20 * mm,
                20 * mm,
                45 * mm,
            ],
            repeatRows=1,
        )

        detail_style_commands = [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#374151"
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
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                3,
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

        # Alternating row backgrounds
        if production_records.exists():

            data_row_count = len(
                production_records
            )

            for index in range(
                1,
                data_row_count + 1,
            ):

                if index % 2 == 0:

                    detail_style_commands.append(
                        (
                            "BACKGROUND",
                            (0, index),
                            (-1, index),
                            colors.HexColor(
                                "#F9FAFB"
                            ),
                        )
                    )

            # Total row
            total_row_index = (
                data_row_count + 1
            )

            detail_style_commands.extend(
                [
                    (
                        "BACKGROUND",
                        (0, total_row_index),
                        (-1, total_row_index),
                        colors.HexColor(
                            "#E5E7EB"
                        ),
                    ),
                    (
                        "FONTNAME",
                        (0, total_row_index),
                        (-1, total_row_index),
                        "Helvetica-Bold",
                    ),
                ]
            )

        else:

            detail_style_commands.extend(
                [
                    (
                        "SPAN",
                        (1, 1),
                        (-1, 1),
                    ),
                    (
                        "ALIGN",
                        (1, 1),
                        (-1, 1),
                        "CENTER",
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 1),
                        (-1, 1),
                        colors.HexColor(
                            "#6B7280"
                        ),
                    ),
                ]
            )

        detail_table.setStyle(
            TableStyle(
                detail_style_commands
            )
        )

        story.append(
            detail_table
        )

        # --------------------------------------------------------------
        # REPORT NOTES
        # --------------------------------------------------------------

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        story.append(
            Paragraph(
                (
                    "<b>Report Notes:</b> "
                    "Good eggs are calculated as eggs collected "
                    "minus broken and rejected eggs. "
                    "Good trays are calculated using "
                    f"{self.format_number(self.TRAY_SIZE)} "
                    "eggs per tray."
                ),
                small_style,
            )
        )

        # --------------------------------------------------------------
        # BUILD PDF
        # --------------------------------------------------------------

        document.build(
            story,
            onFirstPage=self._add_page_footer,
            onLaterPages=self._add_page_footer,
        )

        return response