class ShopProduct {
  const ShopProduct({
    required this.id,
    required this.modelName,
    required this.categoryName,
    required this.capacity,
    required this.sellingPrice,
    required this.warrantyMonths,
    required this.mrp,
    required this.stockQuantity,
    required this.description,
    required this.features,
    required this.imageUrls,
  });

  final int id;
  final String modelName;
  final String categoryName;
  final String capacity;
  final double sellingPrice;
  final int warrantyMonths;
  final double mrp;
  final int stockQuantity;
  final String description;
  final List<String> features;
  final List<String> imageUrls;

  factory ShopProduct.fromJson(Map<String, dynamic> json) {
    return ShopProduct(
      id: (json['id'] as num?)?.toInt() ?? 0,
      modelName: json['model_name']?.toString() ?? '',
      categoryName: json['category_name']?.toString() ?? '',
      capacity: json['capacity']?.toString() ?? '',
      sellingPrice: double.tryParse(json['selling_price']?.toString() ?? '') ?? 0,
      warrantyMonths: (json['warranty_months'] as num?)?.toInt() ?? 0,
      mrp: double.tryParse(json['mrp']?.toString() ?? '') ?? 0,
      stockQuantity: (json['stock_quantity'] as num?)?.toInt() ?? 0,
      description: json['description']?.toString() ?? '',
      features: (json['features']?.toString() ?? '')
          .split('\n')
          .map((item) => item.trim())
          .where((item) => item.isNotEmpty)
          .toList(),
      imageUrls: (json['images'] as List<dynamic>? ?? const [])
          .map((item) => (item as Map<String, dynamic>)['image_url']?.toString() ?? '')
          .where((url) => url.isNotEmpty)
          .toList(),
    );
  }
}
