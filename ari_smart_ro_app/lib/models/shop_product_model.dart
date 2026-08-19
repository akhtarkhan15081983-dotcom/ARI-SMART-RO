class ShopProduct {
  const ShopProduct({
    required this.id,
    required this.modelName,
    required this.categoryName,
    required this.capacity,
    required this.sellingPrice,
    required this.warrantyMonths,
  });

  final int id;
  final String modelName;
  final String categoryName;
  final String capacity;
  final double sellingPrice;
  final int warrantyMonths;

  factory ShopProduct.fromJson(Map<String, dynamic> json) {
    return ShopProduct(
      id: (json['id'] as num?)?.toInt() ?? 0,
      modelName: json['model_name']?.toString() ?? '',
      categoryName: json['category_name']?.toString() ?? '',
      capacity: json['capacity']?.toString() ?? '',
      sellingPrice: double.tryParse(json['selling_price']?.toString() ?? '') ?? 0,
      warrantyMonths: (json['warranty_months'] as num?)?.toInt() ?? 0,
    );
  }
}
