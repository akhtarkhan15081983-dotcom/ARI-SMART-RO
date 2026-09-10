from django.contrib import admin
from django import forms

from .models import (
    ProductCategory,
    ROModel,
    ROModelPart,
    ROModelImage,
)


class ROModelImageInline(admin.TabularInline):
    model = ROModelImage
    extra = 1
    fields = ("image", "alt_text", "sort_order")


class ROModelAdminForm(forms.ModelForm):
    class Meta:
        model = ROModel
        exclude = ("business_type",)

    def clean(self):
        cleaned = super().clean()
        for_sale = cleaned.get("available_for_sale")
        for_rent = cleaned.get("available_for_rent")
        if not for_sale and not for_rent:
            raise forms.ValidationError("Select at least one Store option: Sale or Rent.")
        if for_sale and (cleaned.get("selling_price") or 0) <= 0:
            self.add_error("selling_price", "Enter a selling price when Sale is enabled.")
        if for_rent and (cleaned.get("monthly_rent") or 0) <= 0:
            self.add_error("monthly_rent", "Enter monthly rent when Rent is enabled.")
        return cleaned


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "is_active",
    )

    search_fields = (
        "name",
    )

    list_filter = (
        "is_active",
    )


@admin.register(ROModel)
class ROModelAdmin(admin.ModelAdmin):

    form = ROModelAdminForm
    inlines = [ROModelImageInline]

    list_display = (
        "id",
        "model_name",
        "category",
        "available_for_sale",
        "available_for_rent",
        "monthly_rent",
        "selling_price",
        "stock_quantity",
        "is_active",
    )

    search_fields = (
        "model_name",
    )

    list_filter = (
        "category",
        "available_for_sale",
        "available_for_rent",
        "is_active",
    )

    def save_model(self, request, obj, form, change):
        obj.business_type = "SALE" if obj.available_for_sale else "RENT"
        super().save_model(request, obj, form, change)


@admin.register(ROModelPart)
class ROModelPartAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "ro_model",
        "part",
        "quantity",
        "is_mandatory",
    )

    search_fields = (
        "ro_model__model_name",
        "part__name",
    )

    list_filter = (
        "is_mandatory",
    )
