from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
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

from ..models import EggProduction
from apps.settings.models import FarmSettings


# ================================================================
# BASE PDF REPORT VIEW
# ================================================================

class BaseEggPDFReportView(APIView):
    """
    Shared functionality for KukuFarm egg PDF reports.

    Provides:
        - Number formatting
        - Percentage formatting
        - Date formatting
        - Farm settings
        - Timezone handling
        - Logo watermark
        - PDF footer
        - Common validation
    """

    permission_classes = [permissions.IsAuthenticated]

    EGGS_PER_TRAY = Decimal("30")

    # ============================================================
    # TEXT HELPERS
    # ============================================================

    @staticmethod
    def escape_text(value):
        """
        Safely escape text before putting it inside ReportLab
        Paragraph XML.
        """

        if value is None:
            return ""

        return escape(str(value))

    # ============================================================
    # DECIMAL HELPERS
    # ============================================================

    @staticmethod
    def to_decimal(value):
        """
        Safely convert values to Decimal.
        """

        if value is None:
            return Decimal("0")

        try:
            return Decimal(str(value))

        except Exception:
            return Decimal("0")

    @staticmethod
    def format_number(value, decimals=0):
        """
        Format numbers professionally.

        Examples:
            1000      -> 1,000
            1000.50   -> 1,000.5
        """

        value = BaseEggPDFReportView.to_decimal(value)

        if decimals == 0:
            return f"{value:,.0f}"

        return f"{value:,.{decimals}f}"

    @staticmethod
    def format_percentage(value):
        """
        Format percentage values.
        """

        value = BaseEggPDFReportView.to_decimal(value)

        return f"{value:,.1f}%"

    # ============================================================
    # DATE HELPERS
    # ============================================================

    @staticmethod
    def parse_date(value):
        """
        Parse API date:

            YYYY-MM-DD
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
    def format_report_date(
        value,
        date_format="%Y-%m-%d",
    ):
        """
        Convert FarmSettings date format into Python strftime format.

        FarmSettings may contain frontend-style formats such as:

            DD/MM/YYYY
            DD-MM-YYYY
            YYYY-MM-DD

        Python requires:

            %d/%m/%Y
            %d-%m-%Y
            %Y-%m-%d
        """

        if not value:
            return ""

        format_map = {
            "DD/MM/YYYY": "%d/%m/%Y",
            "DD-MM-YYYY": "%d-%m-%Y",
            "DD.MM.YYYY": "%d.%m.%Y",

            "MM/DD/YYYY": "%m/%d/%Y",
            "MM-DD-YYYY": "%m-%d-%Y",
            "MM.DD.YYYY": "%m.%d.%Y",

            "YYYY/MM/DD": "%Y/%m/%d",
            "YYYY-MM-DD": "%Y-%m-%d",
            "YYYY.MM.DD": "%Y.%m.%d",
        }

        raw_format = str(
            date_format or "%Y-%m-%d"
        ).strip()

        python_format = format_map.get(
            raw_format.upper(),
            raw_format,
        )

        try:
            return value.strftime(
                python_format
            )

        except Exception:
            return value.strftime(
                "%d/%m/%Y"
            )

    # ============================================================
    # FARM TIMEZONE
    # ============================================================

    @staticmethod
    def get_farm_timezone(farm):
        """
        Get farm timezone safely.
        """

        timezone_name = getattr(
            farm,
            "timezone",
            None,
        )

        if not timezone_name:
            return timezone.get_current_timezone()

        try:
            return ZoneInfo(
                timezone_name
            )

        except ZoneInfoNotFoundError:
            return timezone.get_current_timezone()

        except Exception:
            return timezone.get_current_timezone()

    # ============================================================
    # FARM SETTINGS
    # ============================================================

    @staticmethod
    def get_farm_settings():
        """
        Load farm settings safely.

        Returns a dictionary so both reports use exactly
        the same farm information.
        """

        farm = FarmSettings.objects.first()

        if not farm:
            return {
                "farm": None,
                "farm_name": "KukuFarm",
                "owner_name": "",
                "phone": "",
                "email": "",
                "location": "",
                "address": "",
                "date_format": "%Y-%m-%d",
                "farm_timezone": timezone.get_current_timezone(),
                "logo": None,
            }

        return {
            "farm": farm,

            "farm_name": (
                getattr(
                    farm,
                    "farm_name",
                    None,
                )
                or "KukuFarm"
            ),

            "owner_name": (
                getattr(
                    farm,
                    "owner_name",
                    None,
                )
                or ""
            ),

            "phone": (
                getattr(
                    farm,
                    "phone",
                    None,
                )
                or ""
            ),

            "email": (
                getattr(
                    farm,
                    "email",
                    None,
                )
                or ""
            ),

            "location": (
                getattr(
                    farm,
                    "location",
                    None,
                )
                or ""
            ),

            "address": (
                getattr(
                    farm,
                    "address",
                    None,
                )
                or ""
            ),

            "date_format": (
                getattr(
                    farm,
                    "date_format",
                    None,
                )
                or "%Y-%m-%d"
            ),

            "farm_timezone": (
                BaseEggPDFReportView.get_farm_timezone(
                    farm
                )
            ),

            "logo": getattr(
                farm,
                "logo",
                None,
            ),
        }

    # ============================================================
    # LOGO WATERMARK
    # ============================================================

    @staticmethod
    def _draw_logo_watermark(
        canvas,
        logo,
    ):
        """
        Draw the farm logo as a professional watermark.

        IMPORTANT:
        The logo is NOT added to the Story.

        It is drawn directly on the PDF canvas so it appears
        behind the report content on every page.

        Characteristics:
            - Centered
            - Large
            - Very light
            - Maintains original aspect ratio
            - Does not affect document layout
        """

        if not logo:
            return

        try:
            logo_path = logo.path

        except Exception:
            return

        if not logo_path:
            return

        try:
            logo_reader = ImageReader(
                logo_path
            )

            image_width, image_height = (
                logo_reader.getSize()
            )

            if not image_width or not image_height:
                return

            page_width, page_height = landscape(
                A4
            )

            # ----------------------------------------------------
            # WATERMARK SIZE
            # ----------------------------------------------------

            max_width = 105 * mm
            max_height = 105 * mm

            scale = min(
                max_width / float(image_width),
                max_height / float(image_height),
            )

            draw_width = (
                float(image_width)
                * scale
            )

            draw_height = (
                float(image_height)
                * scale
            )

            x = (
                page_width
                - draw_width
            ) / 2

            y = (
                page_height
                - draw_height
            ) / 2

            canvas.saveState()

            # ----------------------------------------------------
            # TRANSPARENCY
            # ----------------------------------------------------

            try:
                canvas.setFillAlpha(
                    0.055
                )

            except Exception:
                pass

            try:
                canvas.setStrokeAlpha(
                    0.055
                )

            except Exception:
                pass

            # ----------------------------------------------------
            # DRAW WATERMARK
            # ----------------------------------------------------

            canvas.drawImage(
                logo_reader,
                x,
                y,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask="auto",
            )

            canvas.restoreState()

        except Exception:
            # A missing/broken logo must NEVER prevent the PDF
            # report from being generated.
            try:
                canvas.restoreState()
            except Exception:
                pass

    # ============================================================
    # PAGE FOOTER + WATERMARK
    # ============================================================

    @staticmethod
    def _draw_page_elements(
        canvas,
        doc,
        farm_name,
        logo=None,
    ):
        """
        Draw page-level elements.

        Order:
            1. Watermark
            2. Footer line
            3. Footer farm name
            4. Page number
        """

        canvas.saveState()

        # ========================================================
        # WATERMARK
        # ========================================================

        if logo:
            try:
                BaseEggPDFReportView._draw_logo_watermark(
                    canvas,
                    logo,
                )

            except Exception:
                pass

        # ========================================================
        # PAGE DIMENSIONS
        # ========================================================

        width, height = landscape(A4)

        # ========================================================
        # FOOTER LINE
        # ========================================================

        canvas.setStrokeColor(
            colors.HexColor(
                "#D9DEE7"
            )
        )

        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            15 * mm,
            12 * mm,
            width - 15 * mm,
            12 * mm,
        )

        # ========================================================
        # FOOTER FONT
        # ========================================================

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        canvas.setFillColor(
            colors.HexColor(
                "#6B7280"
            )
        )

        # ========================================================
        # FARM NAME
        # ========================================================

        canvas.drawString(
            15 * mm,
            7 * mm,
            str(
                farm_name or "KukuFarm"
            ),
        )

        # ========================================================
        # PAGE NUMBER
        # ========================================================

        canvas.drawRightString(
            width - 15 * mm,
            7 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # ============================================================
    # COMMON VALIDATION
    # ============================================================

    def get_report_dates(self, request):
        """
        Read and validate from_date / to_date.
        """

        from_date_text = request.query_params.get(
            "from_date"
        )

        to_date_text = request.query_params.get(
            "to_date"
        )

        from_date = self.parse_date(
            from_date_text
        )

        to_date = self.parse_date(
            to_date_text
        )

        if (
            from_date_text
            and not from_date
        ):
            return (
                None,
                None,
                Response(
                    {
                        "detail": (
                            "Invalid from_date. "
                            "Use YYYY-MM-DD."
                        )
                    },
                    status=400,
                ),
            )

        if (
            to_date_text
            and not to_date
        ):
            return (
                None,
                None,
                Response(
                    {
                        "detail": (
                            "Invalid to_date. "
                            "Use YYYY-MM-DD."
                        )
                    },
                    status=400,
                ),
            )

        if (
            from_date
            and to_date
            and from_date > to_date
        ):
            return (
                None,
                None,
                Response(
                    {
                        "detail": (
                            "from_date cannot be "
                            "later than to_date."
                        )
                    },
                    status=400,
                ),
            )

        return (
            from_date,
            to_date,
            None,
        )

    # ============================================================
    # PERIOD TEXT
    # ============================================================

    def get_period_text(
        self,
        from_date,
        to_date,
        date_format,
        empty_text,
    ):
        """
        Build the report period text.
        """

        if from_date and to_date:
            return (
                "Period: "
                + self.format_report_date(
                    from_date,
                    date_format,
                )
                + " to "
                + self.format_report_date(
                    to_date,
                    date_format,
                )
            )

        if from_date:
            return (
                "From: "
                + self.format_report_date(
                    from_date,
                    date_format,
                )
            )

        if to_date:
            return (
                "Up to: "
                + self.format_report_date(
                    to_date,
                    date_format,
                )
            )

        return empty_text

    # ============================================================
    # COMMON STYLES
    # ============================================================

    @staticmethod
    def get_styles(prefix):
        """
        Create professional ReportLab styles.
        """

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            f"{prefix}Title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        )

        subtitle_style = ParagraphStyle(
            f"{prefix}Subtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#6B7280"
            ),
            spaceAfter=4 * mm,
        )

        section_style = ParagraphStyle(
            f"{prefix}Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(
                "#1F2937"
            ),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )

        normal_style = ParagraphStyle(
            f"{prefix}Normal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
        )

        small_style = ParagraphStyle(
            f"{prefix}Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
        )

        right_style = ParagraphStyle(
            f"{prefix}Right",
            parent=normal_style,
            alignment=TA_RIGHT,
        )

        return {
            "title": title_style,
            "subtitle": subtitle_style,
            "section": section_style,
            "normal": normal_style,
            "small": small_style,
            "right": right_style,
        }


# =================================================================
# EGG PRODUCTION PDF REPORT
# =================================================================

class EggProductionPDFReportView(
    BaseEggPDFReportView
):
    """
    Professional PDF report for egg production.

    Endpoint:
        /api/reports/pdf/

    Query parameters:
        from_date=YYYY-MM-DD
        to_date=YYYY-MM-DD
    """

    # ============================================================
    # GET
    # ============================================================

    def get(self, request):
        # ========================================================
        # VALIDATE DATES
        # ========================================================

        (
            from_date,
            to_date,
            validation_error,
        ) = self.get_report_dates(
            request
        )

        if validation_error:
            return validation_error

        # ========================================================
        # FARM SETTINGS
        # ========================================================

        farm_settings = (
            self.get_farm_settings()
        )

        farm_name = farm_settings[
            "farm_name"
        ]

        owner_name = farm_settings[
            "owner_name"
        ]

        phone = farm_settings[
            "phone"
        ]

        email = farm_settings[
            "email"
        ]

        location = farm_settings[
            "location"
        ]

        address = farm_settings[
            "address"
        ]

        date_format = farm_settings[
            "date_format"
        ]

        farm_timezone = farm_settings[
            "farm_timezone"
        ]

        logo = farm_settings[
            "logo"
        ]

        # ========================================================
        # QUERY PRODUCTION
        #
        # IMPORTANT:
        # EggProduction.date is a DateField.
        #
        # CORRECT:
        #     date__gte
        #     date__lte
        #
        # NOT:
        #     date__date__gte
        #     date__date__lte
        # ========================================================

        queryset = (
            EggProduction.objects
            .select_related("flock")
            .all()
        )

        if from_date:
            queryset = queryset.filter(
                date__gte=from_date
            )

        if to_date:
            queryset = queryset.filter(
                date__lte=to_date
            )

        queryset = queryset.order_by(
            "date",
            "id",
        )

        # ========================================================
        # CALCULATE TOTALS
        # ========================================================

        total_collected = Decimal("0")
        total_broken = Decimal("0")
        total_rejected = Decimal("0")
        total_trays = Decimal("0")

        for production in queryset:
            total_collected += (
                self.to_decimal(
                    production.eggs_collected
                )
            )

            total_broken += (
                self.to_decimal(
                    production.broken_eggs
                )
            )

            total_rejected += (
                self.to_decimal(
                    production.rejected_eggs
                )
            )

            total_trays += (
                self.to_decimal(
                    production.trays
                )
            )

        # ========================================================
        # QUALITY CALCULATIONS
        # ========================================================

        total_lost = (
            total_broken
            + total_rejected
        )

        good_eggs = (
            total_collected
            - total_lost
        )

        if good_eggs < 0:
            good_eggs = Decimal("0")

        good_trays = (
            good_eggs
            / self.EGGS_PER_TRAY
        )

        if total_collected > 0:
            good_percentage = (
                good_eggs
                / total_collected
                * Decimal("100")
            )

            loss_percentage = (
                total_lost
                / total_collected
                * Decimal("100")
            )

        else:
            good_percentage = Decimal("0")
            loss_percentage = Decimal("0")

        # ========================================================
        # RECORD COUNT
        # ========================================================

        record_count = queryset.count()

        if record_count:
            average_production = (
                total_collected
                / Decimal(record_count)
            )

        else:
            average_production = Decimal("0")

        # ========================================================
        # GENERATED TIME
        # ========================================================

        generated_at = (
            timezone.now()
            .astimezone(
                farm_timezone
            )
        )

        # ========================================================
        # HTTP RESPONSE
        # ========================================================

        response = HttpResponse(
            content_type="application/pdf"
        )

        response[
            "Content-Disposition"
        ] = (
            'inline; '
            'filename="egg-production-report.pdf"'
        )

        # ========================================================
        # PDF DOCUMENT
        # ========================================================

        doc = SimpleDocTemplate(
            response,
            pagesize=landscape(A4),

            rightMargin=15 * mm,
            leftMargin=15 * mm,

            topMargin=15 * mm,
            bottomMargin=17 * mm,

            title=(
                f"{farm_name} "
                "- Egg Production Report"
            ),

            author="KukuFarm",
        )

        styles = self.get_styles(
            "Production"
        )

        title_style = styles[
            "title"
        ]

        subtitle_style = styles[
            "subtitle"
        ]

        section_style = styles[
            "section"
        ]

        normal_style = styles[
            "normal"
        ]

        small_style = styles[
            "small"
        ]

        # ========================================================
        # STORY
        # ========================================================

        story = []

        # ========================================================
        # HEADER
        #
        # IMPORTANT:
        # The logo is NOT inserted here.
        #
        # The logo is displayed as a watermark on every page
        # through the canvas callback.
        # ========================================================

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
                "EGG PRODUCTION REPORT",
                subtitle_style,
            )
        )

        period_text = (
            self.get_period_text(
                from_date,
                to_date,
                date_format,
                "All production records",
            )
        )

        story.append(
            Paragraph(
                self.escape_text(
                    period_text
                ),
                subtitle_style,
            )
        )

        # ========================================================
        # PRODUCTION SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Production Summary",
                section_style,
            )
        )

        summary_data = [
            [
                "Total Collected",
                "Good Eggs",
                "Broken",
                "Rejected",
                "Good Trays",
            ],
            [
                self.format_number(
                    total_collected
                ),

                self.format_number(
                    good_eggs
                ),

                self.format_number(
                    total_broken
                ),

                self.format_number(
                    total_rejected
                ),

                self.format_number(
                    good_trays,
                    1,
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                48 * mm,
                48 * mm,
                40 * mm,
                40 * mm,
                48 * mm,
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
                            "#E5E7EB"
                        ),
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#374151"
                        ),
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, 1),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
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
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor(
                            "#D1D5DB"
                        ),
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

        # ========================================================
        # QUALITY SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Egg Quality Summary",
                section_style,
            )
        )

        quality_data = [
            [
                "Good Eggs",
                "Lost Eggs",
                "Good %",
                "Loss %",
                "Average / Record",
                "Production Records",
            ],
            [
                self.format_number(
                    good_eggs
                ),

                self.format_number(
                    total_lost
                ),

                self.format_percentage(
                    good_percentage
                ),

                self.format_percentage(
                    loss_percentage
                ),

                self.format_number(
                    average_production,
                    1,
                ),

                self.format_number(
                    record_count
                ),
            ],
        ]

        quality_table = Table(
            quality_data,
            colWidths=[
                42 * mm,
                42 * mm,
                35 * mm,
                35 * mm,
                48 * mm,
                48 * mm,
            ],
        )

        quality_table.setStyle(
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
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, 1),
                        "Helvetica",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
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
            quality_table
        )

        # ========================================================
        # PRODUCTION DETAILS
        # ========================================================

        story.append(
            Paragraph(
                "Production Details",
                section_style,
            )
        )

        detail_data = [
            [
                "Date",
                "Flock",
                "Collected",
                "Broken",
                "Rejected",
                "Good Eggs",
                "Trays",
                "Notes",
            ]
        ]

        for production in queryset:
            collected = self.to_decimal(
                production.eggs_collected
            )

            broken = self.to_decimal(
                production.broken_eggs
            )

            rejected = self.to_decimal(
                production.rejected_eggs
            )

            good = (
                collected
                - broken
                - rejected
            )

            if good < 0:
                good = Decimal("0")

            # ----------------------------------------------------
            # FLOCK NAME
            # ----------------------------------------------------

            flock_name = ""

            try:
                flock_name = (
                    getattr(
                        production.flock,
                        "name",
                        None,
                    )

                    or getattr(
                        production.flock,
                        "flock_name",
                        None,
                    )

                    or str(
                        production.flock
                    )
                )

            except Exception:
                flock_name = "-"

            # ----------------------------------------------------
            # NOTES
            # ----------------------------------------------------

            notes = (
                getattr(
                    production,
                    "notes",
                    None,
                )
                or ""
            )

            detail_data.append(
                [
                    self.format_report_date(
                        production.date,
                        date_format,
                    ),

                    Paragraph(
                        self.escape_text(
                            flock_name
                        ),
                        small_style,
                    ),

                    self.format_number(
                        collected
                    ),

                    self.format_number(
                        broken
                    ),

                    self.format_number(
                        rejected
                    ),

                    self.format_number(
                        good
                    ),

                    self.format_number(
                        production.trays
                    ),

                    Paragraph(
                        self.escape_text(
                            notes
                        ),
                        small_style,
                    ),
                ]
            )

        detail_table = Table(
            detail_data,
            repeatRows=1,
            colWidths=[
                28 * mm,
                42 * mm,
                30 * mm,
                28 * mm,
                30 * mm,
                30 * mm,
                25 * mm,
                55 * mm,
            ],
        )

        detail_table.setStyle(
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
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, 0),
                        7.5,
                    ),

                    (
                        "FONTSIZE",
                        (0, 1),
                        (-1, -1),
                        7,
                    ),

                    (
                        "ALIGN",
                        (2, 1),
                        (6, -1),
                        "RIGHT",
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
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
            detail_table
        )

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        # ========================================================
        # TOTALS
        # ========================================================

        totals_data = [
            [
                "TOTAL",
                self.format_number(
                    total_collected
                ),
                self.format_number(
                    total_broken
                ),
                self.format_number(
                    total_rejected
                ),
                self.format_number(
                    good_eggs
                ),
                self.format_number(
                    total_trays
                ),
            ]
        ]

        totals_table = Table(
            totals_data,
            colWidths=[
                55 * mm,
                40 * mm,
                35 * mm,
                35 * mm,
                40 * mm,
                35 * mm,
            ],
        )

        totals_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor(
                            "#E5E7EB"
                        ),
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, -1),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),

                    (
                        "ALIGN",
                        (1, 0),
                        (-1, -1),
                        "RIGHT",
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor(
                            "#9CA3AF"
                        ),
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
            totals_table
        )

        # ========================================================
        # REPORT INFORMATION
        # ========================================================

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        story.append(
            Paragraph(
                "Report Information",
                section_style,
            )
        )

        generated_text = (
            generated_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        info_data = [
            [
                Paragraph(
                    "<b>Farm:</b> "
                    + self.escape_text(
                        farm_name
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Owner:</b> "
                    + self.escape_text(
                        owner_name
                    ),
                    normal_style,
                ),
            ],

            [
                Paragraph(
                    "<b>Phone:</b> "
                    + self.escape_text(
                        phone
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Email:</b> "
                    + self.escape_text(
                        email
                    ),
                    normal_style,
                ),
            ],

            [
                Paragraph(
                    "<b>Location:</b> "
                    + self.escape_text(
                        location
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Address:</b> "
                    + self.escape_text(
                        address
                    ),
                    normal_style,
                ),
            ],

            [
                Paragraph(
                    "<b>Generated:</b> "
                    + self.escape_text(
                        generated_text
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Records:</b> "
                    + self.format_number(
                        record_count
                    ),
                    normal_style,
                ),
            ],
        ]

        info_table = Table(
            info_data,
            colWidths=[
                125 * mm,
                125 * mm,
            ],
        )

        info_table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor(
                            "#E5E7EB"
                        ),
                    ),

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor(
                            "#F9FAFB"
                        ),
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
            info_table
        )

        # ========================================================
        # BUILD
        #
        # Watermark is applied through onPage callbacks.
        # ========================================================

        doc.build(
            story,

            onFirstPage=lambda canvas, doc: (
                self._draw_page_elements(
                    canvas,
                    doc,
                    farm_name,
                    logo,
                )
            ),

            onLaterPages=lambda canvas, doc: (
                self._draw_page_elements(
                    canvas,
                    doc,
                    farm_name,
                    logo,
                )
            ),
        )

        return response


# =================================================================
# EGG INVENTORY PDF REPORT
# =================================================================

class EggInventoryPDFReportView(
    BaseEggPDFReportView
):
    """
    Professional PDF report for egg inventory.

    Endpoint:
        /api/reports/egg-inventory/pdf/

    Query parameters:
        from_date=YYYY-MM-DD
        to_date=YYYY-MM-DD
    """

    # ============================================================
    # SALES MODEL
    # ============================================================

    @staticmethod
    def get_sales_model():
        """
        Safely load the Sale model.
        """

        try:
            from apps.sales.models import Sale

            return Sale

        except (
            ImportError,
            AttributeError,
        ):
            return None

    # ============================================================
    # GET SOLD EGGS
    # ============================================================

    def get_sold_eggs(
        self,
        from_date=None,
        to_date=None,
    ):
        """
        Calculate eggs sold from Sale.

        Supports common Sale model structures.

        If your actual sales system stores egg quantities
        inside SaleItem/SaleDetail, this method should be
        aligned directly with that model.
        """

        Sale = self.get_sales_model()

        if Sale is None:
            return Decimal("0")

        try:
            queryset = Sale.objects.all()

            # ====================================================
            # AVAILABLE SALE FIELDS
            # ====================================================

            sale_field_names = {
                field.name
                for field in Sale._meta.get_fields()
            }

            # ====================================================
            # DATE FIELD
            # ====================================================

            sale_date_field = None

            possible_date_fields = [
                "date",
                "sale_date",
                "transaction_date",
                "created_at",
                "created",
            ]

            for field_name in possible_date_fields:

                if (
                    field_name
                    in sale_field_names
                ):
                    sale_date_field = field_name
                    break

            if sale_date_field:

                field = Sale._meta.get_field(
                    sale_date_field
                )

                internal_type = (
                    field.get_internal_type()
                )

                # ------------------------------------------------
                # DATETIME FIELD
                # ------------------------------------------------

                if (
                    internal_type
                    == "DateTimeField"
                ):

                    if from_date:
                        queryset = queryset.filter(
                            **{
                                (
                                    f"{sale_date_field}"
                                    "__date__gte"
                                ): from_date
                            }
                        )

                    if to_date:
                        queryset = queryset.filter(
                            **{
                                (
                                    f"{sale_date_field}"
                                    "__date__lte"
                                ): to_date
                            }
                        )

                # ------------------------------------------------
                # DATE FIELD
                # ------------------------------------------------

                else:

                    if from_date:
                        queryset = queryset.filter(
                            **{
                                (
                                    f"{sale_date_field}"
                                    "__gte"
                                ): from_date
                            }
                        )

                    if to_date:
                        queryset = queryset.filter(
                            **{
                                (
                                    f"{sale_date_field}"
                                    "__lte"
                                ): to_date
                            }
                        )

            # ====================================================
            # EGG FLAG
            # ====================================================

            egg_flag_field = None

            possible_egg_flags = [
                "egg_item",
                "is_egg",
                "is_egg_sale",
                "egg_sale",
                "egg",
            ]

            for field_name in possible_egg_flags:

                if (
                    field_name
                    in sale_field_names
                ):
                    egg_flag_field = field_name
                    break

            if egg_flag_field:

                try:
                    queryset = queryset.filter(
                        **{
                            egg_flag_field: True
                        }
                    )

                except Exception:
                    pass

            # ====================================================
            # DIRECT EGG QUANTITY
            # ====================================================

            egg_quantity_fields = [
                "egg_quantity",
                "eggs_quantity",
                "eggs_sold",
                "egg_quantity_sold",
                "quantity_eggs",
                "total_eggs",
                "eggs",
            ]

            for field_name in (
                egg_quantity_fields
            ):

                if (
                    field_name
                    in sale_field_names
                ):

                    try:

                        total = Decimal("0")

                        for sale in queryset:

                            value = getattr(
                                sale,
                                field_name,
                                None,
                            )

                            total += (
                                self.to_decimal(
                                    value
                                )
                            )

                        return total

                    except Exception:
                        pass

            # ====================================================
            # TRAY QUANTITY
            # ====================================================

            tray_fields = [
                "trays",
                "tray_quantity",
                "egg_trays",
                "trays_sold",
            ]

            for field_name in tray_fields:

                if (
                    field_name
                    in sale_field_names
                ):

                    try:

                        total_trays = Decimal(
                            "0"
                        )

                        for sale in queryset:

                            value = getattr(
                                sale,
                                field_name,
                                None,
                            )

                            total_trays += (
                                self.to_decimal(
                                    value
                                )
                            )

                        return (
                            total_trays
                            * self.EGGS_PER_TRAY
                        )

                    except Exception:
                        pass

        except Exception:
            return Decimal("0")

        return Decimal("0")

    # ============================================================
    # GET
    # ============================================================

    def get(self, request):

        # ========================================================
        # VALIDATE DATES
        # ========================================================

        (
            from_date,
            to_date,
            validation_error,
        ) = self.get_report_dates(
            request
        )

        if validation_error:
            return validation_error

        # ========================================================
        # FARM SETTINGS
        # ========================================================

        farm_settings = (
            self.get_farm_settings()
        )

        farm_name = farm_settings[
            "farm_name"
        ]

        owner_name = farm_settings[
            "owner_name"
        ]

        phone = farm_settings[
            "phone"
        ]

        email = farm_settings[
            "email"
        ]

        location = farm_settings[
            "location"
        ]

        address = farm_settings[
            "address"
        ]

        date_format = farm_settings[
            "date_format"
        ]

        farm_timezone = farm_settings[
            "farm_timezone"
        ]

        logo = farm_settings[
            "logo"
        ]

        # ========================================================
        # PRODUCTION QUERY
        #
        # EggProduction.date is DateField.
        #
        # Correct:
        #     date__gte
        #     date__lte
        # ========================================================

        queryset = (
            EggProduction.objects
            .select_related("flock")
            .all()
        )

        if from_date:
            queryset = queryset.filter(
                date__gte=from_date
            )

        if to_date:
            queryset = queryset.filter(
                date__lte=to_date
            )

        queryset = queryset.order_by(
            "date",
            "id",
        )

        # ========================================================
        # PRODUCTION TOTALS
        # ========================================================

        total_collected = Decimal("0")
        total_broken = Decimal("0")
        total_rejected = Decimal("0")
        total_recorded_trays = Decimal("0")

        for production in queryset:

            total_collected += (
                self.to_decimal(
                    production.eggs_collected
                )
            )

            total_broken += (
                self.to_decimal(
                    production.broken_eggs
                )
            )

            total_rejected += (
                self.to_decimal(
                    production.rejected_eggs
                )
            )

            total_recorded_trays += (
                self.to_decimal(
                    production.trays
                )
            )

        # ========================================================
        # GOOD EGGS
        # ========================================================

        total_lost = (
            total_broken
            + total_rejected
        )

        good_eggs = (
            total_collected
            - total_lost
        )

        if good_eggs < 0:
            good_eggs = Decimal("0")

        good_trays = (
            good_eggs
            / self.EGGS_PER_TRAY
        )

        # ========================================================
        # SOLD EGGS
        # ========================================================

        total_sold = (
            self.get_sold_eggs(
                from_date=from_date,
                to_date=to_date,
            )
        )

        if total_sold < 0:
            total_sold = Decimal("0")

        # ========================================================
        # CURRENT STOCK
        # ========================================================

        if total_sold > good_eggs:

            current_stock = Decimal(
                "0"
            )

        else:

            current_stock = (
                good_eggs
                - total_sold
            )

        # ========================================================
        # TRAY CALCULATIONS
        # ========================================================

        sold_trays = (
            total_sold
            / self.EGGS_PER_TRAY
        )

        current_stock_trays = (
            current_stock
            / self.EGGS_PER_TRAY
        )

        lost_trays = (
            total_lost
            / self.EGGS_PER_TRAY
        )

        # ========================================================
        # PERCENTAGES
        # ========================================================

        if total_collected > 0:

            good_percentage = (
                good_eggs
                / total_collected
                * Decimal("100")
            )

            loss_percentage = (
                total_lost
                / total_collected
                * Decimal("100")
            )

        else:

            good_percentage = Decimal(
                "0"
            )

            loss_percentage = Decimal(
                "0"
            )

        # ========================================================
        # RECORD COUNT
        # ========================================================

        record_count = queryset.count()

        if record_count:

            average_production = (
                total_collected
                / Decimal(record_count)
            )

        else:

            average_production = Decimal(
                "0"
            )

        # ========================================================
        # GENERATED TIME
        # ========================================================

        generated_at = (
            timezone.now()
            .astimezone(
                farm_timezone
            )
        )

        # ========================================================
        # RESPONSE
        # ========================================================

        response = HttpResponse(
            content_type="application/pdf"
        )

        response[
            "Content-Disposition"
        ] = (
            'inline; '
            'filename="egg-inventory-report.pdf"'
        )

        # ========================================================
        # DOCUMENT
        # ========================================================

        doc = SimpleDocTemplate(
            response,
            pagesize=landscape(A4),

            rightMargin=15 * mm,
            leftMargin=15 * mm,

            topMargin=15 * mm,
            bottomMargin=17 * mm,

            title=(
                f"{farm_name} "
                "- Egg Inventory Report"
            ),

            author="KukuFarm",
        )

        styles = self.get_styles(
            "Inventory"
        )

        title_style = styles[
            "title"
        ]

        subtitle_style = styles[
            "subtitle"
        ]

        section_style = styles[
            "section"
        ]

        normal_style = styles[
            "normal"
        ]

        small_style = styles[
            "small"
        ]

        # ========================================================
        # STORY
        # ========================================================

        story = []

        # ========================================================
        # HEADER
        #
        # Logo is intentionally NOT inserted here.
        # It is a page watermark.
        # ========================================================

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
                "EGG INVENTORY REPORT",
                subtitle_style,
            )
        )

        period_text = (
            self.get_period_text(
                from_date,
                to_date,
                date_format,
                "All inventory records",
            )
        )

        story.append(
            Paragraph(
                self.escape_text(
                    period_text
                ),
                subtitle_style,
            )
        )

        # ========================================================
        # INVENTORY SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Inventory Summary",
                section_style,
            )
        )

        summary_data = [
            [
                "Current Stock",
                "Eggs Sold",
                "Good Eggs",
                "Collected",
                "Lost",
                "Current Trays",
            ],

            [
                self.format_number(
                    current_stock
                ),

                self.format_number(
                    total_sold
                ),

                self.format_number(
                    good_eggs
                ),

                self.format_number(
                    total_collected
                ),

                self.format_number(
                    total_lost
                ),

                self.format_number(
                    current_stock_trays,
                    1,
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                43 * mm,
                43 * mm,
                43 * mm,
                43 * mm,
                43 * mm,
                43 * mm,
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
                            "#E5E7EB"
                        ),
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, 1),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
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

        # ========================================================
        # STOCK POSITION
        # ========================================================

        story.append(
            Paragraph(
                "Stock Position",
                section_style,
            )
        )

        stock_data = [
            [
                "Good Eggs",
                "Sold Eggs",
                "Current Stock",
                "Good Trays",
                "Sold Trays",
                "Current Trays",
            ],

            [
                self.format_number(
                    good_eggs
                ),

                self.format_number(
                    total_sold
                ),

                self.format_number(
                    current_stock
                ),

                self.format_number(
                    good_trays,
                    1,
                ),

                self.format_number(
                    sold_trays,
                    1,
                ),

                self.format_number(
                    current_stock_trays,
                    1,
                ),
            ],
        ]

        stock_table = Table(
            stock_data,
            colWidths=[
                42 * mm,
                42 * mm,
                42 * mm,
                42 * mm,
                42 * mm,
                42 * mm,
            ],
        )

        stock_table.setStyle(
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
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, 1),
                        "Helvetica",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
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
            stock_table
        )

        # ========================================================
        # QUALITY SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Egg Quality Summary",
                section_style,
            )
        )

        quality_data = [
            [
                "Collected",
                "Broken",
                "Rejected",
                "Lost",
                "Good %",
                "Loss %",
            ],

            [
                self.format_number(
                    total_collected
                ),

                self.format_number(
                    total_broken
                ),

                self.format_number(
                    total_rejected
                ),

                self.format_number(
                    total_lost
                ),

                self.format_percentage(
                    good_percentage
                ),

                self.format_percentage(
                    loss_percentage
                ),
            ],
        ]

        quality_table = Table(
            quality_data,
            colWidths=[
                42 * mm,
                42 * mm,
                42 * mm,
                42 * mm,
                42 * mm,
                42 * mm,
            ],
        )

        quality_table.setStyle(
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
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
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
            quality_table
        )

        # ========================================================
        # PRODUCTION & INVENTORY DETAILS
        # ========================================================

        story.append(
            Paragraph(
                "Production & Inventory Details",
                section_style,
            )
        )

        detail_data = [
            [
                "Date",
                "Flock",
                "Collected",
                "Broken",
                "Rejected",
                "Good Eggs",
                "Recorded Trays",
                "Notes",
            ]
        ]

        for production in queryset:

            collected = self.to_decimal(
                production.eggs_collected
            )

            broken = self.to_decimal(
                production.broken_eggs
            )

            rejected = self.to_decimal(
                production.rejected_eggs
            )

            good = (
                collected
                - broken
                - rejected
            )

            if good < 0:
                good = Decimal("0")

            # ----------------------------------------------------
            # FLOCK
            # ----------------------------------------------------

            flock_name = ""

            try:

                flock_name = (
                    getattr(
                        production.flock,
                        "name",
                        None,
                    )

                    or getattr(
                        production.flock,
                        "flock_name",
                        None,
                    )

                    or str(
                        production.flock
                    )
                )

            except Exception:
                flock_name = "-"

            # ----------------------------------------------------
            # NOTES
            # ----------------------------------------------------

            notes = (
                getattr(
                    production,
                    "notes",
                    None,
                )
                or ""
            )

            detail_data.append(
                [
                    self.format_report_date(
                        production.date,
                        date_format,
                    ),

                    Paragraph(
                        self.escape_text(
                            flock_name
                        ),
                        small_style,
                    ),

                    self.format_number(
                        collected
                    ),

                    self.format_number(
                        broken
                    ),

                    self.format_number(
                        rejected
                    ),

                    self.format_number(
                        good
                    ),

                    self.format_number(
                        production.trays
                    ),

                    Paragraph(
                        self.escape_text(
                            notes
                        ),
                        small_style,
                    ),
                ]
            )

        detail_table = Table(
            detail_data,
            repeatRows=1,
            colWidths=[
                28 * mm,
                42 * mm,
                30 * mm,
                28 * mm,
                30 * mm,
                30 * mm,
                35 * mm,
                52 * mm,
            ],
        )

        detail_table.setStyle(
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
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, 0),
                        7.5,
                    ),

                    (
                        "FONTSIZE",
                        (0, 1),
                        (-1, -1),
                        7,
                    ),

                    (
                        "ALIGN",
                        (2, 1),
                        (6, -1),
                        "RIGHT",
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
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
            detail_table
        )

        # ========================================================
        # STOCK CALCULATION
        # ========================================================

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        story.append(
            Paragraph(
                "Current Stock Calculation",
                section_style,
            )
        )

        calculation_text = (
            "Good Eggs ("
            + self.format_number(
                good_eggs
            )
            + ") - Sold Eggs ("
            + self.format_number(
                total_sold
            )
            + ") = Current Stock ("
            + self.format_number(
                current_stock
            )
            + ")"
        )

        story.append(
            Paragraph(
                self.escape_text(
                    calculation_text
                ),
                normal_style,
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
                "1 tray = 30 eggs.",
                small_style,
            )
        )

        # ========================================================
        # REPORT INFORMATION
        # ========================================================

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        story.append(
            Paragraph(
                "Report Information",
                section_style,
            )
        )

        generated_text = (
            generated_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        info_data = [
            [
                Paragraph(
                    "<b>Farm:</b> "
                    + self.escape_text(
                        farm_name
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Owner:</b> "
                    + self.escape_text(
                        owner_name
                    ),
                    normal_style,
                ),
            ],

            [
                Paragraph(
                    "<b>Phone:</b> "
                    + self.escape_text(
                        phone
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Email:</b> "
                    + self.escape_text(
                        email
                    ),
                    normal_style,
                ),
            ],

            [
                Paragraph(
                    "<b>Location:</b> "
                    + self.escape_text(
                        location
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Address:</b> "
                    + self.escape_text(
                        address
                    ),
                    normal_style,
                ),
            ],

            [
                Paragraph(
                    "<b>Generated:</b> "
                    + self.escape_text(
                        generated_text
                    ),
                    normal_style,
                ),

                Paragraph(
                    "<b>Production Records:</b> "
                    + self.format_number(
                        record_count
                    ),
                    normal_style,
                ),
            ],
        ]

        info_table = Table(
            info_data,
            colWidths=[
                125 * mm,
                125 * mm,
            ],
        )

        info_table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor(
                            "#E5E7EB"
                        ),
                    ),

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor(
                            "#F9FAFB"
                        ),
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
            info_table
        )

        # ========================================================
        # BUILD PDF
        #
        # Watermark is applied to EVERY PAGE.
        # ========================================================

        doc.build(
            story,

            onFirstPage=lambda canvas, doc: (
                self._draw_page_elements(
                    canvas,
                    doc,
                    farm_name,
                    logo,
                )
            ),

            onLaterPages=lambda canvas, doc: (
                self._draw_page_elements(
                    canvas,
                    doc,
                    farm_name,
                    logo,
                )
            ),
        )

        return response