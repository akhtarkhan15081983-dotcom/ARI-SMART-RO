from django.contrib import admin
from django.http import HttpResponse

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black

from .models import InventoryItem, EngineerBagItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "part",
        "serial_number",
        "status",
    )

    search_fields = (
        "serial_number",
    )

    list_filter = (
        "status",
        "part",
    )

    actions = [
        "generate_qr_codes",
        "print_qr_codes",
    ]
    def generate_qr_codes(self, request, queryset):

        import qrcode
        from io import BytesIO
        from django.core.files import File

        total = 0

        for item in queryset:

            if not item.serial_number:
                continue

            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=4,
            )

            qr.add_data(item.serial_number)
            qr.make(fit=True)

            img = qr.make_image(
                fill_color="black",
                back_color="white",
            )

            buffer = BytesIO()

            img.save(buffer, format="PNG")

            filename = f"{item.serial_number}.png"

            item.qr_code.save(
                filename,
                File(buffer),
                save=True,
            )

            total += 1

        self.message_user(
            request,
            f"{total} QR Codes Generated Successfully."
        )

    generate_qr_codes.short_description = "Generate / Regenerate QR Codes"
    def print_qr_codes(self, request, queryset):

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="ARI_QR_CODES.pdf"'
        )

        pdf = canvas.Canvas(response)

        # ===========================
        # PAGE SETTINGS
        # ===========================

        card_width = 45 * mm
        card_height = 45 * mm

        margin_x = 10 * mm
        margin_y = 10 * mm

        gap_x = 5 * mm
        gap_y = 5 * mm

        columns = 4
        rows = 6

        current = 0

        for item in queryset:

            if not item.qr_code:
                continue

            page = current // (columns * rows)

            if current != 0 and current % (columns * rows) == 0:
                pdf.showPage()

            index = current % (columns * rows)

            row = index // columns
            col = index % columns

            x = margin_x + col * (card_width + gap_x)

            y = (
                297 * mm
                - margin_y
                - ((row + 1) * card_height)
                - (row * gap_y)
            )

            # ===========================
            # CARD BORDER
            # ===========================

            pdf.setStrokeColor(black)

            pdf.roundRect(
                x,
                y,
                card_width,
                card_height,
                3,
            )

            # ===========================
            # HEADER
            # ===========================

            pdf.setFont("Helvetica-Bold", 8)

            pdf.drawCentredString(
                x + card_width / 2,
                y + card_height - 6 * mm,
                "ARI SMART RO",
            )

            # ===========================
            # QR IMAGE
            # ===========================

            qr = ImageReader(item.qr_code.path)

            qr_size = 24 * mm

            pdf.drawImage(
                qr,
                x + (card_width - qr_size) / 2,
                y + 13 * mm,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask='auto',
            )
                        # ===========================
            # SERIAL NUMBER
            # ===========================

            pdf.setFont("Helvetica-Bold", 8)

            pdf.drawCentredString(
                x + card_width / 2,
                y + 10 * mm,
                item.serial_number or "",
            )

            # ===========================
            # PART NAME
            # ===========================

            pdf.setFont("Helvetica", 7)

            pdf.drawCentredString(
                x + card_width / 2,
                y + 6 * mm,
                str(item.part),
            )

            current += 1

        pdf.save()

        return response

    print_qr_codes.short_description = (
        "Print Selected QR Codes (24 Per Page)"
    )


@admin.register(EngineerBagItem)
class EngineerBagItemAdmin(admin.ModelAdmin):

    list_display = (
        "engineer",
        "inventory_item",
        "status",
        "issue_date",
    )

    list_filter = (
        "status",
        "engineer",
    )

    search_fields = (
        "inventory_item__serial_number",
    )