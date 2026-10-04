from collections import defaultdict
from datetime import datetime
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

from ..models import Mortality

from apps.settings.models import FarmSettings


class MortalityPDFReportView(APIView):
    """
    Generate a professional mortality PDF report.

    Includes:

        - Mortality summary
        - Mortality by flock
        - Mortality by cause
        - Detailed mortality records
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
            farm_settings = FarmSettings.objects.first()

        except Exception:
            farm_settings = None

        # --------------------------------------------------------
        # MORTALITY RECORDS
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

        mortality_count = mortalities.count()

        total_birds_lost = sum(
            (
                item.quantity
                for item in mortalities
            ),
            0,
        )

        flock_ids = set()

        for item in mortalities:
            if item.flock_id:
                flock_ids.add(
                    item.flock_id
                )

        affected_flocks = len(
            flock_ids
        )

        # --------------------------------------------------------
        # GROUP BY FLOCK
        # --------------------------------------------------------

        flock_summary = defaultdict(
            lambda: {
                "flock": "",
                "records": 0,
                "quantity": 0,
            }
        )

        for item in mortalities:

            flock_name = "-"

            if item.flock:

                flock_name = (
                    getattr(
                        item.flock,
                        "name",
                        None,
                    )
                    or str(
                        item.flock
                    )
                )

            key = item.flock_id

            flock_summary[key][
                "flock"
            ] = flock_name

            flock_summary[key][
                "records"
            ] += 1

            flock_summary[key][
                "quantity"
            ] += item.quantity

        # --------------------------------------------------------
        # GROUP BY CAUSE
        # --------------------------------------------------------

        cause_summary = defaultdict(
            lambda: {
                "cause": "",
                "records": 0,
                "quantity": 0,
            }
        )

        for item in mortalities:

            cause = (
                item.cause.strip()
                if item.cause
                else "Unknown / Not Specified"
            )

            cause_summary[cause][
                "cause"
            ] = cause

            cause_summary[cause][
                "records"
            ] += 1

            cause_summary[cause][
                "quantity"
            ] += item.quantity

        # --------------------------------------------------------
        # SORT SUMMARIES
        # --------------------------------------------------------

        flock_summary_rows = sorted(
            flock_summary.values(),
            key=lambda x: x["quantity"],
            reverse=True,
        )

        cause_summary_rows = sorted(
            cause_summary.values(),
            key=lambda x: x["quantity"],
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
            "kukufarm-mortality-report-"
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
            title="Mortality Report",
            author="KukuFarm",
        )

        styles = getSampleStyleSheet()

        # --------------------------------------------------------
        # STYLES
        # --------------------------------------------------------

        title_style = ParagraphStyle(
            "MortalityTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=5,
        )

        subtitle_style = ParagraphStyle(
            "MortalitySubtitle",
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
            "MortalitySection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(
                "#990000"
            ),
            spaceBefore=8,
            spaceAfter=6,
        )

        small_style = ParagraphStyle(
            "MortalitySmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        )

        right_style = ParagraphStyle(
            "MortalityRight",
            parent=small_style,
            alignment=TA_RIGHT,
        )

        # --------------------------------------------------------
        # STORY
        # --------------------------------------------------------

        story = []

        # ========================================================
        # FARM HEADER
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
                "MORTALITY REPORT",
                title_style,
            )
        )

        story.append(
            Paragraph(
                "Poultry Mortality Analysis",
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
                            "#FCE4E4"
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
        # SUMMARY
        # ========================================================

        story.append(
            Paragraph(
                "Mortality Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "<b>Mortality Records</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Birds Lost</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Affected Flocks</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Average / Record</b>",
                    small_style,
                ),
            ]
        ]

        average = 0

        if mortality_count:
            average = (
                total_birds_lost
                / mortality_count
            )

        summary_data.append(
            [
                Paragraph(
                    f"{mortality_count:,}",
                    right_style,
                ),
                Paragraph(
                    f"{total_birds_lost:,}",
                    right_style,
                ),
                Paragraph(
                    f"{affected_flocks:,}",
                    right_style,
                ),
                Paragraph(
                    f"{average:.2f}",
                    right_style,
                ),
            ]
        )

        summary_table = Table(
            summary_data,
            colWidths=[
                45 * mm,
                45 * mm,
                45 * mm,
                45 * mm,
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
                        "BACKGROUND",
                        (0, 1),
                        (-1, 1),
                        colors.HexColor(
                            "#FFF5F5"
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
        # MORTALITY BY FLOCK
        # ========================================================

        story.append(
            Paragraph(
                "Mortality by Flock",
                section_style,
            )
        )

        flock_data = [
            [
                Paragraph(
                    "<b>Rank</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Flock</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Records</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Birds Lost</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Share</b>",
                    small_style,
                ),
            ]
        ]

        for index, row in enumerate(
            flock_summary_rows,
            start=1,
        ):

            share = 0

            if total_birds_lost:
                share = (
                    row["quantity"]
                    / total_birds_lost
                ) * 100

            flock_data.append(
                [
                    Paragraph(
                        str(index),
                        right_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            row["flock"]
                        ),
                        small_style,
                    ),
                    Paragraph(
                        f'{row["records"]:,}',
                        right_style,
                    ),
                    Paragraph(
                        f'{row["quantity"]:,}',
                        right_style,
                    ),
                    Paragraph(
                        f"{share:.2f}%",
                        right_style,
                    ),
                ]
            )

        if len(flock_data) == 1:

            flock_data.append(
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

        flock_table = Table(
            flock_data,
            repeatRows=1,
            colWidths=[
                20 * mm,
                65 * mm,
                30 * mm,
                35 * mm,
                30 * mm,
            ],
        )

        flock_table.setStyle(
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
            flock_table
        )

        # ========================================================
        # MORTALITY BY CAUSE
        # ========================================================

        story.append(
            Paragraph(
                "Mortality by Cause",
                section_style,
            )
        )

        cause_data = [
            [
                Paragraph(
                    "<b>Rank</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Cause</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Records</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Birds Lost</b>",
                    small_style,
                ),
                Paragraph(
                    "<b>Share</b>",
                    small_style,
                ),
            ]
        ]

        for index, row in enumerate(
            cause_summary_rows,
            start=1,
        ):

            share = 0

            if total_birds_lost:
                share = (
                    row["quantity"]
                    / total_birds_lost
                ) * 100

            cause_data.append(
                [
                    Paragraph(
                        str(index),
                        right_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            row["cause"]
                        ),
                        small_style,
                    ),
                    Paragraph(
                        f'{row["records"]:,}',
                        right_style,
                    ),
                    Paragraph(
                        f'{row["quantity"]:,}',
                        right_style,
                    ),
                    Paragraph(
                        f"{share:.2f}%",
                        right_style,
                    ),
                ]
            )

        if len(cause_data) == 1:

            cause_data.append(
                [
                    Paragraph(
                        "No mortality causes found.",
                        small_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                ]
            )

        cause_table = Table(
            cause_data,
            repeatRows=1,
            colWidths=[
                20 * mm,
                65 * mm,
                30 * mm,
                35 * mm,
                30 * mm,
            ],
        )

        cause_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#7F0000"
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
            cause_table
        )

        # ========================================================
        # DETAILED RECORDS
        # ========================================================

        story.append(
            Paragraph(
                "Detailed Mortality Records",
                section_style,
            )
        )

        detail_data = [
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

            flock_name = "-"

            if mortality.flock:

                flock_name = (
                    getattr(
                        mortality.flock,
                        "name",
                        None,
                    )
                    or str(
                        mortality.flock
                    )
                )

            cause = (
                mortality.cause
                if mortality.cause
                else "Not Specified"
            )

            notes = (
                mortality.notes
                if mortality.notes
                else "-"
            )

            detail_data.append(
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
                            cause
                        ),
                        small_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            notes
                        ),
                        small_style,
                    ),
                ]
            )

        if len(detail_data) == 1:

            detail_data.append(
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

        detail_table = Table(
            detail_data,
            repeatRows=1,
            colWidths=[
                25 * mm,
                40 * mm,
                25 * mm,
                45 * mm,
                50 * mm,
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
            detail_table
        )

        # ========================================================
        # NOTES
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
                "Birds Lost represents the total quantity "
                "recorded in mortality records within the "
                "selected period."
            ),
            (
                "Mortality by Flock ranks flocks according "
                "to the number of birds lost."
            ),
            (
                "Mortality by Cause groups records using "
                "the cause entered by the user."
            ),
            (
                "Records without a specified cause are "
                "classified as Unknown / Not Specified."
            ),
            (
                "This report is generated directly from "
                "the KukuFarm mortality records."
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
        # BUILD
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