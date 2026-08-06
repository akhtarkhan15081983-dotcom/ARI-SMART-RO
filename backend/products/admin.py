from django.contrib import admin
from .models import ProductCategory, ROModel, ROModelPart


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "is_active",
    )

    search_fields = (
        "name",
    )


class ROModelPartInline(admin.TabularInline):
    model = ROModelPart
    extra = 1

@admin.register(ROModel)
class ROModelAdmin(admin.ModelAdmin):

    inlines = [ROModelPartInline]
    
    list_display = (
        "model_name",
        "category",
        "business_type",
        "capacity",
        "monthly_rent",
        "installation_charge",
        "is_active",
    )

    list_filter = (
        "category",
        "business_type",
        "is_active",
    )

    search_fields = (
        "model_name",
    )