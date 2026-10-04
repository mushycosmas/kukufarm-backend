from datetime import datetime
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import permissions
from rest_framework.views import APIView

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
    PageBreak,
)

from apps.suppliers.models import Supplier

try:
    from apps.settings.models import FarmSettings
except ImportError:
    FarmSettings = None


class SupplierPDFReportView(APIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get(self, request):
        from_date = request.query_params.get(
            "from_date"
        )

        to_date = request.query_params.get(
            "to_date"
        )

        supplier_id = request.query_params.get(
            "supplier_id"
        )

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
        # SUPPLIERS
        # =========================================================

        suppliers = (
            Supplier.objects
            .all()
            .order_by("name")
        )

        if supplier_id:
            suppliers = suppliers.filter(
                id=supplier_id
            )

        suppliers = list(
            suppliers
        )

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

        filename = (
            "supplier_report.pdf"
        )

        if (
            supplier_id
            and suppliers
        ):
            supplier = suppliers[0]

            safe_name = "".join(
                char
                if char.isalnum()
                else "_"
                for char in supplier.name
            )

            filename = (
                f"supplier_report_"
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
            title="Supplier Report",
            author=farm_name,
        )

        styles = getSampleStyleSheet()

        # =========================================================
        # STYLES
        # =========================================================

        title_style = ParagraphStyle(
            "SupplierReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=5,
        )

        subtitle_style = ParagraphStyle(
            "SupplierReportSubtitle",
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
            "SupplierReportSection",
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
            "SupplierReportNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )

        small_style = ParagraphStyle(
            "SupplierReportSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        )

        right_style = ParagraphStyle(
            "SupplierReportRight",
            parent=small_style,
            alignment=TA_RIGHT,
        )

        center_style = ParagraphStyle(
            "SupplierReportCenter",
            parent=small_style,
            alignment=TA_CENTER,
        )

        left_style = ParagraphStyle(
            "SupplierReportLeft",
            parent=small_style,
            alignment=TA_LEFT,
        )

        story = []

        # =========================================================
        # HELPERS
        # =========================================================

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
                "All available supplier records"
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
            """

            # -----------------------------------------------------
            # WATERMARK
            # -----------------------------------------------------

            draw_watermark(
                canvas,
                doc,
            )

            # -----------------------------------------------------
            # FOOTER
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
                "SUPPLIER REPORT",
                ParagraphStyle(
                    "SupplierReportHeading",
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

        total_suppliers = len(
            suppliers
        )

        active_suppliers = sum(
            1
            for supplier in suppliers
            if supplier.active
        )

        inactive_suppliers = sum(
            1
            for supplier in suppliers
            if not supplier.active
        )

        suppliers_with_email = sum(
            1
            for supplier in suppliers
            if supplier.email
        )

        suppliers_with_phone = sum(
            1
            for supplier in suppliers
            if supplier.phone
        )

        suppliers_with_contact_person = sum(
            1
            for supplier in suppliers
            if supplier.contact_person
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
                    "TOTAL SUPPLIERS",
                    center_style,
                ),
                paragraph(
                    "ACTIVE SUPPLIERS",
                    center_style,
                ),
                paragraph(
                    "INACTIVE SUPPLIERS",
                    center_style,
                ),
                paragraph(
                    "WITH PHONE",
                    center_style,
                ),
            ],
            [
                paragraph(
                    str(
                        total_suppliers
                    ),
                    summary_value_style(
                        "SummaryValue1"
                    ),
                ),
                paragraph(
                    str(
                        active_suppliers
                    ),
                    summary_value_style(
                        "SummaryValue2"
                    ),
                ),
                paragraph(
                    str(
                        inactive_suppliers
                    ),
                    summary_value_style(
                        "SummaryValue3"
                    ),
                ),
                paragraph(
                    str(
                        suppliers_with_phone
                    ),
                    summary_value_style(
                        "SummaryValue4"
                    ),
                ),
            ],
            [
                paragraph(
                    "WITH EMAIL",
                    center_style,
                ),
                paragraph(
                    "WITH CONTACT PERSON",
                    center_style,
                ),
                paragraph(
                    "REPORT PERIOD",
                    center_style,
                ),
                paragraph(
                    "RECORD STATUS",
                    center_style,
                ),
            ],
            [
                paragraph(
                    str(
                        suppliers_with_email
                    ),
                    summary_value_style(
                        "SummaryValue5"
                    ),
                ),
                paragraph(
                    str(
                        suppliers_with_contact_person
                    ),
                    summary_value_style(
                        "SummaryValue6"
                    ),
                ),
                paragraph(
                    safe(
                        report_period_text()
                    ),
                    summary_value_style(
                        "SummaryValue7"
                    ),
                ),
                paragraph(
                    (
                        f"{active_suppliers} Active / "
                        f"{inactive_suppliers} Inactive"
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
            Spacer(
                1,
                5 * mm,
            )
        )

        # =========================================================
        # SUPPLIER OVERVIEW
        # =========================================================

        story.append(
            Paragraph(
                "SUPPLIER OVERVIEW",
                section_style,
            )
        )

        supplier_rows = [
            [
                paragraph(
                    "Supplier",
                    center_style,
                ),
                paragraph(
                    "Contact Person",
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
                    "Address",
                    center_style,
                ),
                paragraph(
                    "Status",
                    center_style,
                ),
            ]
        ]

        for supplier in suppliers:

            status = (
                "Active"
                if supplier.active
                else "Inactive"
            )

            supplier_rows.append(
                [
                    paragraph(
                        supplier.name,
                        left_style,
                    ),
                    paragraph(
                        supplier.contact_person
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        supplier.phone
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        supplier.email
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        supplier.address
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        status,
                        center_style,
                    ),
                ]
            )

        if len(supplier_rows) > 1:

            supplier_table = Table(
                supplier_rows,
                colWidths=[
                    35 * mm,
                    32 * mm,
                    27 * mm,
                    38 * mm,
                    40 * mm,
                    20 * mm,
                ],
                repeatRows=1,
            )

            supplier_table.setStyle(
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
                supplier_table
            )

        else:

            story.append(
                Paragraph(
                    (
                        "No suppliers found "
                        "for the selected period."
                    ),
                    normal_style,
                )
            )

        # =========================================================
        # SUPPLIER DIRECTORY
        # =========================================================

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "SUPPLIER DIRECTORY",
                section_style,
            )
        )

        directory_rows = [
            [
                paragraph(
                    "#",
                    center_style,
                ),
                paragraph(
                    "Supplier",
                    center_style,
                ),
                paragraph(
                    "Contact Person",
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
                    "Address",
                    center_style,
                ),
                paragraph(
                    "Status",
                    center_style,
                ),
            ]
        ]

        for index, supplier in enumerate(
            suppliers,
            start=1,
        ):

            status = (
                "Active"
                if supplier.active
                else "Inactive"
            )

            directory_rows.append(
                [
                    paragraph(
                        str(index),
                        center_style,
                    ),
                    paragraph(
                        supplier.name,
                        left_style,
                    ),
                    paragraph(
                        supplier.contact_person
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        supplier.phone
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        supplier.email
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        supplier.address
                        or "-",
                        left_style,
                    ),
                    paragraph(
                        status,
                        center_style,
                    ),
                ]
            )

        if len(directory_rows) > 1:

            directory_table = Table(
                directory_rows,
                colWidths=[
                    10 * mm,
                    32 * mm,
                    32 * mm,
                    27 * mm,
                    38 * mm,
                    38 * mm,
                    20 * mm,
                ],
                repeatRows=1,
            )

            directory_table.setStyle(
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
                directory_table
            )

        else:

            story.append(
                Paragraph(
                    "No suppliers available.",
                    normal_style,
                )
            )

        # =========================================================
        # SUPPLIER PROFILES
        # =========================================================

        for supplier in suppliers:

            story.append(
                PageBreak()
            )

            story.append(
                Paragraph(
                    (
                        "SUPPLIER PROFILE: "
                        f"{safe(supplier.name).upper()}"
                    ),
                    section_style,
                )
            )

            # -----------------------------------------------------
            # Supplier information
            # -----------------------------------------------------

            supplier_info = [
                [
                    paragraph(
                        "<b>Supplier</b>",
                        normal_style,
                    ),
                    paragraph(
                        supplier.name,
                        normal_style,
                    ),
                    paragraph(
                        "<b>Status</b>",
                        normal_style,
                    ),
                    paragraph(
                        (
                            "Active"
                            if supplier.active
                            else "Inactive"
                        ),
                        normal_style,
                    ),
                ],
                [
                    paragraph(
                        "<b>Contact Person</b>",
                        normal_style,
                    ),
                    paragraph(
                        supplier.contact_person
                        or "-",
                        normal_style,
                    ),
                    paragraph(
                        "<b>Phone</b>",
                        normal_style,
                    ),
                    paragraph(
                        supplier.phone
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
                        supplier.email
                        or "-",
                        normal_style,
                    ),
                    paragraph(
                        "<b>Address</b>",
                        normal_style,
                    ),
                    paragraph(
                        supplier.address
                        or "-",
                        normal_style,
                    ),
                ],
            ]

            supplier_info_table = Table(
                supplier_info,
                colWidths=[
                    30 * mm,
                    60 * mm,
                    30 * mm,
                    60 * mm,
                ],
            )

            supplier_info_table.setStyle(
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
                supplier_info_table
            )

            story.append(
                Spacer(
                    1,
                    5 * mm,
                )
            )

            # -----------------------------------------------------
            # Supplier contact summary
            # -----------------------------------------------------

            supplier_contact_summary = Table(
                [
                    [
                        paragraph(
                            "CONTACT PERSON",
                            center_style,
                        ),
                        paragraph(
                            "PHONE",
                            center_style,
                        ),
                        paragraph(
                            "EMAIL",
                            center_style,
                        ),
                        paragraph(
                            "STATUS",
                            center_style,
                        ),
                    ],
                    [
                        paragraph(
                            supplier.contact_person
                            or "-",
                            summary_value_style(
                                "SupplierContactPerson"
                            ),
                        ),
                        paragraph(
                            supplier.phone
                            or "-",
                            summary_value_style(
                                "SupplierPhone"
                            ),
                        ),
                        paragraph(
                            supplier.email
                            or "-",
                            summary_value_style(
                                "SupplierEmail"
                            ),
                        ),
                        paragraph(
                            (
                                "Active"
                                if supplier.active
                                else "Inactive"
                            ),
                            summary_value_style(
                                "SupplierStatus"
                            ),
                        ),
                    ],
                ],
                colWidths=[
                    45 * mm,
                    45 * mm,
                    60 * mm,
                    30 * mm,
                ],
            )

            supplier_contact_summary.setStyle(
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
                supplier_contact_summary
            )

            story.append(
                Spacer(
                    1,
                    6 * mm,
                )
            )

            # -----------------------------------------------------
            # Supplier notes / record status
            # -----------------------------------------------------

            story.append(
                Paragraph(
                    "SUPPLIER RECORD",
                    section_style,
                )
            )

            supplier_record_rows = [
                [
                    paragraph(
                        "Supplier Name",
                        center_style,
                    ),
                    paragraph(
                        "Status",
                        center_style,
                    ),
                    paragraph(
                        "Contact Available",
                        center_style,
                    ),
                    paragraph(
                        "Communication",
                        center_style,
                    ),
                ],
                [
                    paragraph(
                        supplier.name,
                        left_style,
                    ),
                    paragraph(
                        (
                            "Active"
                            if supplier.active
                            else "Inactive"
                        ),
                        center_style,
                    ),
                    paragraph(
                        (
                            "Yes"
                            if supplier.contact_person
                            else "No"
                        ),
                        center_style,
                    ),
                    paragraph(
                        (
                            "Phone + Email"
                            if (
                                supplier.phone
                                and supplier.email
                            )
                            else (
                                "Phone"
                                if supplier.phone
                                else (
                                    "Email"
                                    if supplier.email
                                    else "Not provided"
                                )
                            )
                        ),
                        center_style,
                    ),
                ],
            ]

            supplier_record_table = Table(
                supplier_record_rows,
                colWidths=[
                    55 * mm,
                    35 * mm,
                    45 * mm,
                    45 * mm,
                ],
                repeatRows=1,
            )

            supplier_record_table.setStyle(
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
                supplier_record_table
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