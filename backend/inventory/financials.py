from collections import Counter
from decimal import Decimal

from .models import InventoryItem
from purchase.models import PurchaseItem


ZERO = Decimal("0.00")


def inventory_financial_snapshot(company_id):
    """Return quantity/value reconciliation for one tenant.

    Purchase value is quantity * unit price. Physical-state values are derived
    from InventoryItem rows, where each row represents one purchased unit.
    """
    purchase_items = PurchaseItem.objects.filter(company_id=company_id).only(
        "quantity", "purchase_price"
    )
    purchased_units = 0
    purchased_value = ZERO
    for row in purchase_items.iterator():
        purchased_units += row.quantity
        purchased_value += Decimal(row.purchase_price) * row.quantity

    inventory = InventoryItem.objects.filter(company_id=company_id).select_related(
        "purchase_item"
    )
    counts = Counter()
    values = Counter()
    for item in inventory.iterator():
        status = item.status
        price = Decimal(item.purchase_item.purchase_price)
        counts[status] += 1
        values[status] += price

    physical_units = sum(counts.values())
    received_units = physical_units - counts["PENDING_RECEIPT"]
    received_value = sum(
        value for status, value in values.items() if status != "PENDING_RECEIPT"
    )
    warehouse_units = counts["IN_STOCK"] + counts["RETURNED"]
    warehouse_value = values["IN_STOCK"] + values["RETURNED"]

    return {
        "purchased_units": purchased_units,
        "physical_units": physical_units,
        "unit_gap": purchased_units - physical_units,
        "purchased_value": purchased_value,
        "received_units": received_units,
        "received_value": received_value,
        "pending_receipt": counts["PENDING_RECEIPT"],
        "in_stock": counts["IN_STOCK"],
        "issued": counts["ISSUED"],
        "installed": counts["INSTALLED"],
        "returned": counts["RETURNED"],
        "scrap": counts["SCRAP"],
        "warehouse_units": warehouse_units,
        "warehouse_stock_value": warehouse_value,
        "issued_value": values["ISSUED"],
        "installed_value": values["INSTALLED"],
        "scrap_value": values["SCRAP"],
    }
