import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ari_smart_ro_app/screens/customer/customer_history_screen.dart';

void main() {
  testWidgets('customer history hub exposes all required history domains',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: CustomerHistoryScreen()),
    );

    expect(find.text('My History'), findsOneWidget);
    expect(find.text('Rent & Payment History'), findsOneWidget);
    expect(find.text('Service History'), findsOneWidget);
    expect(find.text('Complaint History'), findsOneWidget);

    expect(
      find.text('Rent, service and complaint records are available from one place.'),
      findsOneWidget,
    );
  });
}
