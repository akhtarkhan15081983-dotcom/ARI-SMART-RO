import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/models/shop_product_model.dart';

void main() {
  test('ShopProduct parses catalog JSON', () {
    final product = ShopProduct.fromJson({
      'id': 7,
      'model_name': 'ARI Aqua 12',
      'category_name': 'Domestic RO',
      'capacity': '12 LPH',
      'selling_price': '14999.00',
      'warranty_months': 12,
    });

    expect(product.id, 7);
    expect(product.modelName, 'ARI Aqua 12');
    expect(product.categoryName, 'Domestic RO');
    expect(product.capacity, '12 LPH');
    expect(product.sellingPrice, 14999);
    expect(product.warrantyMonths, 12);
  });

  test('ShopProduct safely defaults malformed optional values', () {
    final product = ShopProduct.fromJson(const {});
    expect(product.id, 0);
    expect(product.modelName, '');
    expect(product.sellingPrice, 0);
    expect(product.warrantyMonths, 0);
  });
}
