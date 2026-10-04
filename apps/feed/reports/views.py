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
    Feed,
    FeedStock,
    FeedStockMovement,
    FeedConsumption,
)

from apps.settings.models import FarmSettings


class FeedPDFReportView(APIView):
    """
    Generate a professional PDF feed management report
    for a selected date range.

    Endpoint:

        GET /api/reports/feed/pdf/

    Parameters:

        from_date=YYYY-MM-DD
        to_date=YYYY-MM-DD

    Example:

        /api/reports/feed/pdf/
        ?from_date=2026-10-01
        &to_date=2026-10-03

    Features:

        - Farm settings
        - Farm logo watermark
        - Farm contact information
        - Configurable date format
        - Farm timezone
        - Feed inventory summary
        - Current feed stock
        - Stock movement summary
        - Stock movement details
        - Feed consumption summary
        - Feed consumption details
        - Total stock in
        - Total consumed
        - Current stock
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

        return escape(
            str(value)
        )

    @staticmethod
    def to_decimal(value):
        """
        Safely convert a numeric value to Decimal.
        """

        if value is None:
            return Decimal("0")

        try:
            return Decimal(
                str(value)
            )

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
    def get_farm_timezone(
        farm_settings,
    ):
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
        """

        if not value:
            return ""

        if isinstance(
            value,
            datetime,
        ):
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

        if hasattr(
            value,
            "strftime",
        ):
            return value.strftime(
                python_format
            )

        if isinstance(
            value,
            str,
        ):
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
                    parsed_date = (
                        datetime.strptime(
                            value,
                            input_format,
                        ).date()
                    )

                    return parsed_date.strftime(
                        python_format
                    )

                except ValueError:
                    continue

            return value

        return str(value)

    @staticmethod
    def get_movement_label(
        movement_type,
    ):
        """
        Convert movement type code into
        a readable label.
        """

        labels = {
            "STOCK_IN": "Stock In",
            "OPENING_STOCK": "Opening Stock",
            "ADJUSTMENT": "Adjustment",
            "CONSUMPTION": "Consumption",
        }

        return labels.get(
            movement_type,
            movement_type or "-",
        )

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

        canvas.setStrokeColor(
            colors.HexColor(
                "#D9D9D9"
            )
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
            colors.HexColor(
                "#666666"
            )
        )

        canvas.drawString(
            15 * mm,
            8 * mm,
            str(farm_name),
        )

        canvas.drawCentredString(
            page_width / 2,
            8 * mm,
            generated_text,
        )

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
        # GET FEEDS
        # =====================================================

        feeds = (
            Feed.objects
            .filter(
                active=True,
            )
            .select_related(
                "stock",
            )
            .order_by(
                "name",
            )
        )

        feeds = list(
            feeds
        )

        # =====================================================
        # GET CURRENT STOCK
        # =====================================================

        feed_stocks = (
            FeedStock.objects
            .select_related(
                "feed",
            )
            .order_by(
                "feed__name",
            )
        )

        feed_stocks = list(
            feed_stocks
        )

        # =====================================================
        # GET STOCK MOVEMENTS
        # =====================================================

        stock_movements = (
            FeedStockMovement.objects
            .filter(
                date__gte=start_date,
                date__lte=end_date,
            )
            .select_related(
                "feed",
                "flock",
                "created_by",
            )
            .order_by(
                "date",
                "id",
            )
        )

        stock_movements = list(
            stock_movements
        )

        # =====================================================
        # GET CONSUMPTION
        # =====================================================

        consumptions = (
            FeedConsumption.objects
            .filter(
                date__gte=start_date,
                date__lte=end_date,
            )
            .select_related(
                "feed",
                "flock",
                "created_by",
            )
            .order_by(
                "date",
                "id",
            )
        )

        consumptions = list(
            consumptions
        )

        # =====================================================
        # CALCULATE CURRENT STOCK
        # =====================================================

        total_current_stock = Decimal(
            "0.00"
        )

        low_stock_count = 0

        out_of_stock_count = 0

        for stock in feed_stocks:
            quantity = self.to_decimal(
                stock.quantity
            )

            total_current_stock += quantity

            minimum_stock = (
                self.to_decimal(
                    stock.feed.minimum_stock
                )
            )

            if quantity <= 0:
                out_of_stock_count += 1

            elif (
                minimum_stock > 0
                and quantity <= minimum_stock
            ):
                low_stock_count += 1

        # =====================================================
        # CALCULATE STOCK IN
        # =====================================================

        total_stock_in = Decimal(
            "0.00"
        )

        total_opening_stock = Decimal(
            "0.00"
        )

        total_adjustment = Decimal(
            "0.00"
        )

        for movement in stock_movements:
            quantity = self.to_decimal(
                movement.quantity
            )

            if (
                movement.movement_type
                == "STOCK_IN"
            ):
                total_stock_in += quantity

            elif (
                movement.movement_type
                == "OPENING_STOCK"
            ):
                total_opening_stock += (
                    quantity
                )

            elif (
                movement.movement_type
                == "ADJUSTMENT"
            ):
                total_adjustment += (
                    quantity
                )

        # =====================================================
        # CALCULATE CONSUMPTION
        # =====================================================

        total_consumed = Decimal(
            "0.00"
        )

        for consumption in consumptions:
            total_consumed += (
                self.to_decimal(
                    consumption.quantity
                )
            )

        # =====================================================
        # RECORD COUNTS
        # =====================================================

        feed_count = len(
            feeds
        )

        stock_movement_count = len(
            stock_movements
        )

        consumption_count = len(
            consumptions
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
            f"kukufarm-feed-report-"
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
                f"{farm_name} - Feed Report"
            ),
            author=str(
                farm_name
            ),
            subject="Farm Feed Management Report",
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

        # =====================================================
        # GET FARM LOGO
        # =====================================================

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
            "FeedReportTitle",
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
            "FeedReportSubtitle",
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
            "FeedReportSection",
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
            "FeedReportNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10,
        )

        center_style = ParagraphStyle(
            "FeedReportCenter",
            parent=normal_style,
            alignment=TA_CENTER,
        )

        right_style = ParagraphStyle(
            "FeedReportRight",
            parent=normal_style,
            alignment=TA_RIGHT,
        )

        small_style = ParagraphStyle(
            "FeedReportSmall",
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
                "FEED MANAGEMENT REPORT",
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
        # FEED SUMMARY
        # =====================================================

        story.append(
            Paragraph(
                "Feed Summary",
                section_style,
            )
        )

        summary_data = [
            [
                Paragraph(
                    "<b>Feed Types</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Current Stock</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Total Stock In</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Total Consumed</b>",
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    str(feed_count),
                    center_style,
                ),
                Paragraph(
                    f"{total_current_stock:,.2f}",
                    right_style,
                ),
                Paragraph(
                    f"{total_stock_in:,.2f}",
                    right_style,
                ),
                Paragraph(
                    f"{total_consumed:,.2f}",
                    right_style,
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
        # STOCK STATUS SUMMARY
        # =====================================================

        story.append(
            Paragraph(
                "Stock Status",
                section_style,
            )
        )

        stock_status_data = [
            [
                Paragraph(
                    "<b>Total Feed Types</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Low Stock</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Out of Stock</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Adjustments</b>",
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    str(feed_count),
                    center_style,
                ),
                Paragraph(
                    str(low_stock_count),
                    center_style,
                ),
                Paragraph(
                    str(out_of_stock_count),
                    center_style,
                ),
                Paragraph(
                    f"{total_adjustment:,.2f}",
                    right_style,
                ),
            ],
        ]

        stock_status_table = Table(
            stock_status_data,
            colWidths=[
                40 * mm,
                40 * mm,
                40 * mm,
                40 * mm,
            ],
        )

        stock_status_table.setStyle(
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
            stock_status_table
        )

        story.append(
            Spacer(
                1,
                6 * mm,
            )
        )

        # =====================================================
        # CURRENT FEED INVENTORY
        # =====================================================

        story.append(
            Paragraph(
                "Current Feed Inventory",
                section_style,
            )
        )

        inventory_data = [
            [
                Paragraph(
                    "<b>#</b>",
                    center_style,
                ),
                Paragraph(
                    "<b>Feed</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Unit</b>",
                    center_style,
                ),
                Paragraph(
                    "<b>Minimum</b>",
                    right_style,
                ),
                Paragraph(
                    "<b>Current Stock</b>",
                    right_style,
                ),
                Paragraph(
                    "<b>Status</b>",
                    center_style,
                ),
            ]
        ]

        for index, stock in enumerate(
            feed_stocks,
            start=1,
        ):
            feed = stock.feed

            quantity = self.to_decimal(
                stock.quantity
            )

            minimum_stock = (
                self.to_decimal(
                    feed.minimum_stock
                )
            )

            if quantity <= 0:
                status = "OUT OF STOCK"

            elif (
                minimum_stock > 0
                and quantity <= minimum_stock
            ):
                status = "LOW STOCK"

            else:
                status = "AVAILABLE"

            inventory_data.append(
                [
                    Paragraph(
                        str(index),
                        center_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            feed.name
                        ),
                        normal_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            feed.unit
                        ),
                        center_style,
                    ),
                    Paragraph(
                        f"{minimum_stock:,.2f}",
                        right_style,
                    ),
                    Paragraph(
                        f"{quantity:,.2f}",
                        right_style,
                    ),
                    Paragraph(
                        status,
                        center_style,
                    ),
                ]
            )

        if not feed_stocks:
            inventory_data.append(
                [
                    "",
                    Paragraph(
                        "No feed stock records found.",
                        center_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                ]
            )

        inventory_table = Table(
            inventory_data,
            colWidths=[
                10 * mm,
                55 * mm,
                20 * mm,
                30 * mm,
                35 * mm,
                30 * mm,
            ],
            repeatRows=1,
        )

        inventory_table.setStyle(
            TableStyle(
                [
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
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
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
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#f8f9fa"
                            ),
                        ],
                    ),
                ]
            )
        )

        story.append(
            inventory_table
        )

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        # =====================================================
        # STOCK MOVEMENTS
        # =====================================================

        story.append(
            Paragraph(
                "Feed Stock Movements",
                section_style,
            )
        )

        movement_data = [
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
                    "<b>Feed</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Movement</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Quantity</b>",
                    right_style,
                ),
                Paragraph(
                    "<b>Reference</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Notes</b>",
                    normal_style,
                ),
            ]
        ]

        for index, movement in enumerate(
            stock_movements,
            start=1,
        ):
            feed_name = (
                movement.feed.name
                if movement.feed
                else "-"
            )

            movement_label = (
                self.get_movement_label(
                    movement.movement_type
                )
            )

            reference = (
                movement.reference
                or "-"
            )

            notes = (
                movement.notes
                or "-"
            )

            movement_date = (
                self.format_report_date(
                    movement.date,
                    date_format,
                )
                if movement.date
                else "-"
            )

            quantity = self.to_decimal(
                movement.quantity
            )

            movement_data.append(
                [
                    Paragraph(
                        str(index),
                        center_style,
                    ),
                    Paragraph(
                        movement_date,
                        normal_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            feed_name
                        ),
                        normal_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            movement_label
                        ),
                        normal_style,
                    ),
                    Paragraph(
                        f"{quantity:,.2f}",
                        right_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            reference
                        ),
                        normal_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            notes
                        ),
                        normal_style,
                    ),
                ]
            )

        if not stock_movements:
            movement_data.append(
                [
                    "",
                    "",
                    Paragraph(
                        "No feed stock movements found for the selected date range.",
                        center_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                ]
            )

        movement_table = Table(
            movement_data,
            colWidths=[
                8 * mm,
                23 * mm,
                35 * mm,
                30 * mm,
                25 * mm,
                28 * mm,
                41 * mm,
            ],
            repeatRows=1,
        )

        movement_table.setStyle(
            TableStyle(
                [
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
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
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
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor(
                                "#f8f9fa"
                            ),
                        ],
                    ),
                ]
            )
        )

        story.append(
            movement_table
        )

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        # =====================================================
        # FEED CONSUMPTION
        # =====================================================

        story.append(
            Paragraph(
                "Feed Consumption",
                section_style,
            )
        )

        consumption_data = [
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
                    "<b>Feed</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Flock</b>",
                    normal_style,
                ),
                Paragraph(
                    "<b>Quantity</b>",
                    right_style,
                ),
                Paragraph(
                    "<b>Notes</b>",
                    normal_style,
                ),
            ]
        ]

        for index, consumption in enumerate(
            consumptions,
            start=1,
        ):
            feed_name = (
                consumption.feed.name
                if consumption.feed
                else "-"
            )

            flock_name = (
                str(
                    consumption.flock
                )
                if consumption.flock
                else "-"
            )

            notes = (
                consumption.notes
                or "-"
            )

            consumption_date = (
                self.format_report_date(
                    consumption.date,
                    date_format,
                )
                if consumption.date
                else "-"
            )

            quantity = self.to_decimal(
                consumption.quantity
            )

            consumption_data.append(
                [
                    Paragraph(
                        str(index),
                        center_style,
                    ),
                    Paragraph(
                        consumption_date,
                        normal_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            feed_name
                        ),
                        normal_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            flock_name
                        ),
                        normal_style,
                    ),
                    Paragraph(
                        f"{quantity:,.2f}",
                        right_style,
                    ),
                    Paragraph(
                        self.escape_text(
                            notes
                        ),
                        normal_style,
                    ),
                ]
            )

        if not consumptions:
            consumption_data.append(
                [
                    "",
                    "",
                    Paragraph(
                        "No feed consumption records found for the selected date range.",
                        center_style,
                    ),
                    "",
                    "",
                    "",
                ]
            )

        consumption_data.append(
            [
                "",
                "",
                "",
                Paragraph(
                    "<b>TOTAL CONSUMED</b>",
                    right_style,
                ),
                Paragraph(
                    f"<b>{total_consumed:,.2f}</b>",
                    right_style,
                ),
                "",
            ]
        )

        consumption_table = Table(
            consumption_data,
            colWidths=[
                10 * mm,
                25 * mm,
                45 * mm,
                35 * mm,
                30 * mm,
                35 * mm,
            ],
            repeatRows=1,
        )

        consumption_table.setStyle(
            TableStyle(
                [
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
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
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
            consumption_table
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
            "This report contains feed inventory, "
            "stock movements and feed consumption "
            "records within the selected date range. "
            "Current stock represents the physical "
            "feed quantity currently recorded in "
            "the FeedStock records. Feed consumption "
            "is reported separately from stock movements "
            "to avoid double counting."
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
