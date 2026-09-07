class ShopProduct {
  const ShopProduct({
    required this.id,
    required this.modelName,
    required this.categoryName,
    required this.capacity,
    required this.sellingPrice,
    required this.monthlyRent,
    required this.installationCharge,
    required this.securityDeposit,
    required this.businessType,
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
  final double monthlyRent;
  final double installationCharge;
  final double securityDeposit;
  final String businessType;
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
      sellingPrice:
          double.tryParse(json['selling_price']?.toString() ?? '') ?? 0,
      monthlyRent: double.tryParse(json['monthly_rent']?.toString() ?? '') ?? 0,
      installationCharge:
          double.tryParse(json['installation_charge']?.toString() ?? '') ?? 0,
      securityDeposit:
          double.tryParse(json['security_deposit']?.toString() ?? '') ?? 0,
      businessType: json['business_type']?.toString() ?? 'SALE',
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
          .map(
            (item) =>
                (item as Map<String, dynamic>)['image_url']?.toString() ?? '',
          )
          .where((url) => url.isNotEmpty)
          .toList(),
    );
  }
}
