from django.contrib import admin
from django.http import HttpResponse

from reportlab.lib.colors import black
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import (
    EngineerBagItem,
    InventoryItem,
    PartStockAudit,
    PartStockAuditLine,
    PartStockAuditScan,
)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("id", "part", "serial_number", "status")
    search_fields = ("serial_number", "barcode", "part__code", "part__name")
    list_filter = ("status", "part")
    actions = ["generate_qr_codes", "print_qr_codes"]

    @admin.action(description="Generate / Regenerate QR Codes")
    def generate_qr_codes(self, request, queryset):
        import qrcode
        from io import BytesIO
        from django.core.files import File

        total = 0
        for item in queryset:
            if not item.serial_number:
                continue
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(item.serial_number)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            filename = f"{item.serial_number}.png"
            item.qr_code.save(filename, File(buffer), save=True)
            total += 1
        self.message_user(request, f"{total} QR Codes Generated Successfully.")

    @admin.action(description="Print Selected QR Codes (24 Per Page)")
    def print_qr_codes(self, request, queryset):
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="ARI_QR_CODES.pdf"'
        pdf = canvas.Canvas(response)
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
            if current != 0 and current % (columns * rows) == 0:
                pdf.showPage()
            index = current % (columns * rows)
            row = index // columns
            col = index % columns
            x = margin_x + col * (card_width + gap_x)
            y = 297 * mm - margin_y - ((row + 1) * card_height) - (row * gap_y)
            pdf.setStrokeColor(black)
            pdf.roundRect(x, y, card_width, card_height, 3)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawCentredString(x + card_width / 2, y + card_height - 6 * mm, "ARI SMART RO")
            qr = ImageReader(item.qr_code.path)
            qr_size = 24 * mm
            pdf.drawImage(
                qr,
                x + (card_width - qr_size) / 2,
                y + 13 * mm,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask="auto",
            )
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawCentredString(x + card_width / 2, y + 10 * mm, item.serial_number or "")
            pdf.setFont("Helvetica", 7)
            pdf.drawCentredString(x + card_width / 2, y + 6 * mm, str(item.part))
            current += 1
        pdf.save()
        return response


@admin.register(EngineerBagItem)
class EngineerBagItemAdmin(admin.ModelAdmin):
    list_display = ("engineer", "inventory_item", "status", "issue_date")
    list_filter = ("status", "engineer")
    search_fields = ("inventory_item__serial_number",)


class PartStockAuditLineInline(admin.TabularInline):
    model = PartStockAuditLine
    extra = 0
    fields = (
        "part",
        "is_serialized",
        "expected_quantity",
        "counted_quantity",
        "difference_display",
        "verified_at",
        "verified_by",
        "remarks",
    )
    readonly_fields = fields
    can_delete = False

    @admin.display(description="Difference")
    def difference_display(self, obj):
        return obj.difference


@admin.register(PartStockAudit)
class PartStockAuditAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "status",
        "started_by",
        "started_at",
        "completed_at",
        "difference_lines",
    )
    list_filter = ("status", "started_at")
    search_fields = ("reference", "notes")
    readonly_fields = ("reference", "started_by", "started_at", "completed_at")
    inlines = [PartStockAuditLineInline]

    @admin.display(description="Differences")
    def difference_lines(self, obj):
        return sum(1 for line in obj.lines.all() if line.difference != 0)


@admin.register(PartStockAuditLine)
class PartStockAuditLineAdmin(admin.ModelAdmin):
    list_display = (
        "audit",
        "part",
        "is_serialized",
        "expected_quantity",
        "counted_quantity",
        "difference_display",
        "verified_at",
    )
    list_filter = ("is_serialized", "audit__status")
    search_fields = ("audit__reference", "part__code", "part__name")
    readonly_fields = (
        "audit",
        "part",
        "is_serialized",
        "expected_quantity",
        "counted_quantity",
        "verified_by",
        "verified_at",
    )

    @admin.display(description="Difference")
    def difference_display(self, obj):
        return obj.difference


@admin.register(PartStockAuditScan)
class PartStockAuditScanAdmin(admin.ModelAdmin):
    list_display = ("audit_line", "inventory_item", "scanned_by", "scanned_at")
    search_fields = (
        "audit_line__audit__reference",
        "inventory_item__serial_number",
        "inventory_item__part__code",
    )
    readonly_fields = [field.name for field in PartStockAuditScan._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
