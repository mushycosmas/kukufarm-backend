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

from ..models import (
    HealthRecord,
    Vaccination,
    Mortality,
)

from apps.settings.models import FarmSettings


class HealthPDFReportView(APIView):
    """
    Generate a professional PDF report for:

        - Health Records
        - Vaccinations
        - Mortality

    Report is filtered by date range.
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
    def to_decimal(value):
        if value is None:
            return Decimal("0")

        return Decimal(str(value))

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
            value = value.astimezone(tz)

        except Exception:
            pass

        return value.strftime(
            "%d %B %Y %H:%M"
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
        # WATERMARK LOGO
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
                    )
                    / 2,
                    (
                        height
                        - watermark_size
                    )
                    / 2,
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
            farm_settings = FarmSettings.objects.first()

        except Exception:
            farm_settings = None

        # --------------------------------------------------------
        # HEALTH RECORDS
        # --------------------------------------------------------

        health_records = (
            HealthRecord.objects
            .filter(
                date__gte=from_date,
                date__lte=to_date,
            )
            .select_related(
                "flock"
            )
            .order_by(
                "date",
                "flock_id",
            )
        )

        # --------------------------------------------------------
        # VACCINATIONS
        # --------------------------------------------------------

        vaccinations = (
            Vaccination.objects
            .filter(
                date__gte=from_date,
                date__lte=to_date,
            )
            .select_related(
                "flock"
            )
            .order_by(
                "date",
                "flock_id",
            )
        )

        # --------------------------------------------------------
        # MORTALITY
        # --------------------------------------------------------

        mortalities = (
            Mortality.objects
            .filter(
                date__gte=from_date,
                date__lte=to_date,
            )
            .select_related(
                "flock"
            )
            .order_by(
                "date",
                "flock_id",
            )
        )

        # --------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------

        health_count = health_records.count()

        vaccination_count = vaccinations.count()

        mortality_count = mortalities.count()

        total_mortality = sum(
            (
                item.quantity
                for item in mortalities
            ),
            0,
        )

        # Unique flocks represented
        flock_ids = set()

        for item in health_records:
            if item.flock_id:
                flock_ids.add(
                    item.flock_id
                )

        for item in vaccinations:
            if item.flock_id:
                flock_ids.add(
                    item.flock_id
                )

        for item in mortalities:
            if item.flock_id:
                flock_ids.add(
                    item.flock_id
                )

        affected_flocks = len(
            flock_ids
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

        generated_at = generated_at.astimezone(
            farm_timezone
        )

        # --------------------------------------------------------
        # RESPONSE
        # --------------------------------------------------------

        filename = (
            "kukufarm-health-report-"
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
            title="Health Report",
            author="KukuFarm",
        )

        styles = getSampleStyleSheet()

        # --------------------------------------------------------
        # CUSTOM STYLES
        # --------------------------------------------------------

        title_style = ParagraphStyle(
            "HealthTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=5,
        )

        subtitle_style = ParagraphStyle(
            "HealthSubtitle",
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
            "HealthSection",
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

        normal_style = ParagraphStyle(
            "HealthNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )

        small_style = ParagraphStyle(
            "HealthSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        )

        right_style = ParagraphStyle(
            "HealthRight",
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
                "HEALTH & LIVESTOCK REPORT",
                title_style,
            )
        )

        story.append(
            Paragraph(
                (
                    "Health Records, Vaccinations "
                    "and Mortality"
                ),
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
                f"Tel: "
                f"{self.escape_text(farm_phone)}"
            )

        if farm_email:
            farm_info.append(
                f"Email: "
                f"{self.escape_text(farm_email)}"
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
        # EXECUTIVE SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Health Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "<b>Health Records</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Vaccinations</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Mortality Records</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Birds Lost</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Flocks Affected</b>",
                    small_style,
                ),
            ],
            [
                Paragraph(
                    str(health_count),
                    right_style,
                ),
                Paragraph(
                    str(vaccination_count),
                    right_style,
                ),
                Paragraph(
                    str(mortality_count),
                    right_style,
                ),
                Paragraph(
                    f"{total_mortality:,}",
                    right_style,
                ),
                Paragraph(
                    str(affected_flocks),
                    right_style,
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                35 * mm,
                35 * mm,
                38 * mm,
                30 * mm,
                32 * mm,
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
        # HEALTH RECORDS
        # ========================================================

        story.append(
            Paragraph(
                "Health Records",
                section_style,
            )
        )

        health_data = [
            [
                Paragraph(
                    "<b>Date</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Flock</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Condition</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Symptoms</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Treatment</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Medicine</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Veterinarian</b>",
                    small_style,
                ),
            ]
        ]

        for record in health_records:

            flock_name = (
                getattr(
                    record.flock,
                    "name",
                    None,
                )
                or str(
                    record.flock
                )
                if record.flock
                else "-"
            )

            health_data.append(
                [
                    Paragraph(
                        record.date.strftime(
                            "%d/%m/%Y"
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            flock_name
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            record.condition
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            record.symptoms
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            record.treatment
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            record.medicine
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            record.veterinarian
                        ),
                        small_style,
                    ),
                ]
            )

        if len(health_data) == 1:

            health_data.append(
                [
                    Paragraph(
                        "No health records found.",
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

        health_table = Table(
            health_data,
            repeatRows=1,
            colWidths=[
                20 * mm,
                25 * mm,
                28 * mm,
                38 * mm,
                38 * mm,
                28 * mm,
                28 * mm,
            ],
        )

        health_table.setStyle(
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
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
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
            health_table
        )

        # ========================================================
        # VACCINATIONS
        # ========================================================

        story.append(
            Paragraph(
                "Vaccination Records",
                section_style,
            )
        )

        vaccination_data = [
            [
                Paragraph(
                    "<b>Date</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Flock</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Vaccine</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Next Due</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Dosage</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Administered By</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Notes</b>",
                    small_style,
                ),
            ]
        ]

        for vaccination in vaccinations:

            flock_name = (
                getattr(
                    vaccination.flock,
                    "name",
                    None,
                )
                or str(
                    vaccination.flock
                )
                if vaccination.flock
                else "-"
            )

            next_due = "-"

            if vaccination.next_due_date:
                next_due = (
                    vaccination.next_due_date.strftime(
                        "%d/%m/%Y"
                    )
                )

            vaccination_data.append(
                [
                    Paragraph(
                        vaccination.date.strftime(
                            "%d/%m/%Y"
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            flock_name
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            vaccination.vaccine
                        ),
                        small_style,
                    ),
                    Paragraph(
                        next_due,
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            vaccination.dosage
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            vaccination.administered_by
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            vaccination.notes
                        ),
                        small_style,
                    ),
                ]
            )

        if len(vaccination_data) == 1:

            vaccination_data.append(
                [
                    Paragraph(
                        "No vaccination records found.",
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

        vaccination_table = Table(
            vaccination_data,
            repeatRows=1,
            colWidths=[
                20 * mm,
                25 * mm,
                32 * mm,
                25 * mm,
                28 * mm,
                35 * mm,
                35 * mm,
            ],
        )

        vaccination_table.setStyle(
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
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
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
            vaccination_table
        )

        # ========================================================
        # MORTALITY
        # ========================================================

        story.append(
            Paragraph(
                "Mortality Records",
                section_style,
            )
        )

        mortality_data = [
            [
                Paragraph(
                    "<b>Date</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Flock</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Quantity</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Cause</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Notes</b>",
                    small_style,
                ),
            ]
        ]

        for mortality in mortalities:

            flock_name = (
                getattr(
                    mortality.flock,
                    "name",
                    None,
                )
                or str(
                    mortality.flock
                )
                if mortality.flock
                else "-"
            )

            mortality_data.append(
                [
                    Paragraph(
                        mortality.date.strftime(
                            "%d/%m/%Y"
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            flock_name
                        ),
                        small_style,
                    ),
                    Paragraph(
                        f"{mortality.quantity:,}",
                        right_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            mortality.cause
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            mortality.notes
                        ),
                        small_style,
                    ),
                ]
            )

        if len(mortality_data) == 1:

            mortality_data.append(
                [
                    Paragraph(
                        "No mortality records found.",
                        small_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                ]
            )

        mortality_table = Table(
            mortality_data,
            repeatRows=1,
            colWidths=[
                25 * mm,
                35 * mm,
                25 * mm,
                45 * mm,
                55 * mm,
            ],
        )

        mortality_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#990000"
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
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
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
            mortality_table
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
                "Health records show health conditions, "
                "symptoms, treatment and veterinary "
                "information recorded during the selected "
                "period."
            ),
            (
                "Vaccination records show vaccines "
                "administered to flocks during the selected "
                "period, including the next scheduled due "
                "date where available."
            ),
            (
                "Mortality represents the number of birds "
                "recorded as deceased during the selected "
                "period."
            ),
            (
                "This report is generated from the records "
                "stored in the KukuFarm system."
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
        # BUILD PDF
        # ========================================================

        logo_path = None

        if farm_settings:

            logo_path = getattr(
                farm_settings,
                "logo",
                None,
            )

            if logo_path:

                try:
                    logo_path = logo_path.path

                except Exception:
                    logo_path = None

        document.build(
            story,
            onFirstPage=lambda canvas, doc: self._add_page_footer(
                canvas,
                doc,
                farm_settings,
                logo_path,
            ),
            onLaterPages=lambda canvas, doc: self._add_page_footer(
                canvas,
                doc,
                farm_settings,
                logo_path,
            ),
        )

        return response