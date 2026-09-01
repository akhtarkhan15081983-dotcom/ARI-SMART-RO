import 'package:ari_smart_ro_app/screens/dashboard/dashboard_items.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('role dashboards do not contain duplicate tools', () {
    final dashboards = {
      'admin': DashboardItems.admin,
      'manager': DashboardItems.manager,
      'engineer': DashboardItems.engineer,
      'office': DashboardItems.office,
    };

    for (final entry in dashboards.entries) {
      final routes = entry.value.map((item) => item.route).toList();
      expect(
        routes.toSet().length,
        routes.length,
        reason: '${entry.key} has duplicate tools',
      );
    }
  });
}
