import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/screens/hrms/employee_lifecycle_screen.dart';

void main() {
  group('EmployeeLifecycleScreen widget contract', () {
    testWidgets('supports employee-focused lifecycle workspace construction', (tester) async {
      const screen = EmployeeLifecycleScreen(initialEmployeeId: 42);
      expect(screen, isA<EmployeeLifecycleScreen>());
      expect(screen.initialEmployeeId, 42);
    });

    testWidgets('supports command-center construction without an employee focus', (tester) async {
      const screen = EmployeeLifecycleScreen();
      expect(screen.initialEmployeeId, isNull);
    });
  });
}
