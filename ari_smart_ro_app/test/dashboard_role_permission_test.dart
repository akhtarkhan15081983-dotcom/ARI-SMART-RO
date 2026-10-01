import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/screens/dashboard/dashboard_items.dart';

void main() {
  test('CALLING role can gain Rent Management card through RBAC grant', () {
    final resolved = DashboardItems.resolvePermissions(
      role: 'CALLING',
      allowedFeatures: const {
        'attendance',
        'hrms',
        'training',
        'calling_desk',
        'profile',
        'rent_management',
      },
      baseItems: DashboardItems.calling,
    );

    expect(
      resolved.any((item) => item.route == 'rent_management'),
      isTrue,
    );
  });

  test('CALLING role does not see Rent Management when permission is absent', () {
    final resolved = DashboardItems.resolvePermissions(
      role: 'CALLING',
      allowedFeatures: const {
        'attendance',
        'hrms',
        'training',
        'calling_desk',
        'profile',
      },
      baseItems: DashboardItems.calling,
    );

    expect(
      resolved.any((item) => item.route == 'rent_management'),
      isFalse,
    );
  });
}
