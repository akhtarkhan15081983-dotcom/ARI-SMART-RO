import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/utils/complaint_customer_scope.dart';

void main() {
  group('complaint customer scope', () {
    test('office staff can register complaints for all customers', () {
      expect(
        complaintCustomerScopeForRole('OFFICE'),
        ComplaintCustomerScope.all,
      );
    });

    test('engineers remain limited to assigned customers', () {
      expect(
        complaintCustomerScopeForRole('ENGINEER'),
        ComplaintCustomerScope.assigned,
      );
    });

    test('customers remain limited to their own customer record', () {
      expect(
        complaintCustomerScopeForRole('CUSTOMER'),
        ComplaintCustomerScope.own,
      );
    });

    test('admin and manager retain all-customer access', () {
      expect(
        complaintCustomerScopeForRole('ADMIN'),
        ComplaintCustomerScope.all,
      );
      expect(
        complaintCustomerScopeForRole('MANAGER'),
        ComplaintCustomerScope.all,
      );
    });
  });
}
