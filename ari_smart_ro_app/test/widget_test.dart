import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ari_smart_ro_app/screens/dashboard/dashboard_card.dart';

void main() {
  testWidgets('Dashboard card renders and handles tap', (WidgetTester tester) async {
    var tapped = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DashboardCard(
            title: 'Profile',
            icon: Icons.person,
            onTap: () {
              tapped = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('Profile'), findsOneWidget);
    expect(find.byIcon(Icons.person), findsOneWidget);

    await tester.tap(find.text('Profile'));
    await tester.pump();

    expect(tapped, isTrue);
  });
}
