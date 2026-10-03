from datetime import datetime
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

from ..models import Flock


class FlockPDFReportView(APIView):
    """
    Generate a professional PDF flock report
    for a selected arrival date range.

    Endpoint:
        GET /api/reports/flocks/pdf/

    Parameters:
        from_date=YYYY-MM-DD
        to_date=YYYY-MM-DD

    Example:
        /api/reports/flocks/pdf/
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
        # GET FLOCKS
        # =====================================================

        flocks = (
            Flock.objects
            .filter(
                arrival_date__gte=start_date,
                arrival_date__lte=end_date,
            )
            .order_by(
                "arrival_date",
                "id",
            )
        )

        # Convert queryset to list so it is evaluated once
        flocks = list(flocks)

        # =====================================================
        # CALCULATE TOTALS
        # =====================================================

        total_flocks = len(flocks)

        active_flocks = sum(
            1
            for flock in flocks
            if str(flock.status or "").lower() == "active"
        )

        sold_flocks = sum(
            1
            for flock in flocks
            if str(flock.status or "").lower() == "sold"
        )

        closed_flocks = sum(
            1
            for flock in flocks
            if str(flock.status or "").lower() == "closed"
        )

        total_initial_quantity = sum(
            int(flock.initial_quantity or 0)
            for flock in flocks
        )

        total_current_quantity = sum(
            int(flock.current_quantity or 0)
            for flock in flocks
        )

        total_birds_lost = (
            total_initial_quantity
            - total_current_quantity
        )

        # Prevent negative loss caused by inconsistent data.
        if total_birds_lost < 0:
            total_birds_lost = 0

        if total_initial_quantity > 0:
            loss_percentage = (
                total_birds_lost
                / total_initial_quantity
            ) * 100
        else:
            loss_percentage = 0

        # =====================================================
        # PDF FILE NAME
        # =====================================================

        filename = (
            f"kukufarm-flock-report-"
            f"{from_date}-to-{to_date}.pdf"
        )

        # =====================================================
        # HTTP RESPONSE
        # =====================================================

        response = HttpResponse(
            content_type="application/pdf"
        )

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
            title="KukuFarm Flock Report",
            author="KukuFarm Farming Management System",
            subject="Farm Flock Report",
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
                "FLOCK REPORT",
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
                "Flock Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "<b>Total Flocks</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Active</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Sold</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Closed</b>",
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    str(total_flocks),
                    center_style,
                ),
                Paragraph(
                    str(active_flocks),
                    center_style,
                ),
                Paragraph(
                    str(sold_flocks),
                    center_style,
                ),
                Paragraph(
                    str(closed_flocks),
                    center_style,
                ),
            ],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[
                40 * mm,
                40 * mm,
                40 * mm,
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

        story.append(summary_table)

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        # =====================================================
        # BIRD SUMMARY
        # =====================================================

        bird_summary_data = [
            [
                Paragraph(
                    "<b>Initial Birds</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Current Birds</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Birds Lost</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Loss %</b>",
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    f"{total_initial_quantity:,}",
                    center_style,
                ),
                Paragraph(
                    f"{total_current_quantity:,}",
                    center_style,
                ),
                Paragraph(
                    f"{total_birds_lost:,}",
                    center_style,
                ),
                Paragraph(
                    f"{loss_percentage:.2f}%",
                    center_style,
                ),
            ],
        ]

        bird_summary_table = Table(
            bird_summary_data,
            colWidths=[
                40 * mm,
                40 * mm,
                40 * mm,
                40 * mm,
            ],
        )

        bird_summary_table.setStyle(
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

        story.append(bird_summary_table)

        story.append(
            Spacer(
                1,
                6 * mm,
            )
        )

        # =====================================================
        # FLOCK DETAILS
        # =====================================================

        story.append(
            Paragraph(
                "Flock Details",
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
                    "<b>Code</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Flock Name</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Breed</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Source</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Arrival Date</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Initial Qty</b>",
                    right_style,
                ),
                Paragraph(
                    "<b>Current Qty</b>",
                    right_style,
                ),
                Paragraph(
                    "<b>Age (Weeks)</b>",
                    center_style,
                ),
                Paragraph(
                    "<b>House</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Status</b>",
                    center_style,
                ),
            ]
        ]

        # =====================================================
        # FLOCK ROWS
        # =====================================================

        for index, flock in enumerate(
            flocks,
            start=1,
        ):
            code = escape(
                str(flock.code or "-")
            )

            name = escape(
                str(flock.name or "-")
            )

            breed = escape(
                str(flock.breed or "-")
            )

            source = escape(
                str(flock.source or "-")
            )

            house = escape(
                str(flock.house or "-")
            )

            status = escape(
                str(flock.status or "-").title()
            )

            flock_date = (
                flock.arrival_date.strftime(
                    "%d/%m/%Y"
                )
                if flock.arrival_date
                else "-"
            )

            initial_quantity = int(
                flock.initial_quantity or 0
            )

            current_quantity = int(
                flock.current_quantity or 0
            )

            age_weeks = int(
                flock.age_weeks or 0
            )

            table_data.append(
                [
                    Paragraph(
                        str(index),
                        center_style,
                    ),
                    Paragraph(
                        code,
                        normal_style,
                    ),
                    Paragraph(
                        name,
                        normal_style,
                    ),
                    Paragraph(
                        breed,
                        normal_style,
                    ),
                    Paragraph(
                        source,
                        normal_style,
                    ),
                    Paragraph(
                        flock_date,
                        normal_style,
                    ),
                    Paragraph(
                        f"{initial_quantity:,}",
                        right_style,
                    ),
                    Paragraph(
                        f"{current_quantity:,}",
                        right_style,
                    ),
                    Paragraph(
                        str(age_weeks),
                        center_style,
                    ),
                    Paragraph(
                        house,
                        normal_style,
                    ),
                    Paragraph(
                        status,
                        center_style,
                    ),
                ]
            )

        # =====================================================
        # EMPTY REPORT
        # =====================================================

        if total_flocks == 0:
            table_data.append(
                [
                    "",
                    "",
                    Paragraph(
                        "No flocks found for the selected date range.",
                        center_style,
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

        # =====================================================
        # TOTAL ROW
        # =====================================================

        table_data.append(
            [
                "",
                "",
                "",
                "",
                "",
                Paragraph(
                    "<b>TOTAL</b>",
                    right_style,
                ),
                Paragraph(
                    f"<b>{total_initial_quantity:,}</b>",
                    right_style,
                ),
                Paragraph(
                    f"<b>{total_current_quantity:,}</b>",
                    right_style,
                ),
                "",
                "",
                "",
            ]
        )

        # =====================================================
        # FLOCK TABLE
        # =====================================================

        flock_table = Table(
            table_data,
            colWidths=[
                8 * mm,
                20 * mm,
                31 * mm,
                25 * mm,
                25 * mm,
                25 * mm,
                23 * mm,
                23 * mm,
                22 * mm,
                25 * mm,
                22 * mm,
            ],
            repeatRows=1,
            repeatCols=0,
        )

        flock_table.setStyle(
            TableStyle(
                [
                    # Header
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

                    # Grid
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#cccccc"),
                    ),

                    # Alignment
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (0, -1),
                        "CENTER",
                    ),
                    (
                        "ALIGN",
                        (5, 1),
                        (8, -1),
                        "CENTER",
                    ),
                    (
                        "ALIGN",
                        (10, 1),
                        (10, -1),
                        "CENTER",
                    ),

                    # Padding
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

                    # Alternating rows
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -2),
                        [
                            colors.white,
                            colors.HexColor("#f8f9fa"),
                        ],
                    ),

                    # Total row
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

        story.append(flock_table)

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
