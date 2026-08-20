import 'package:flutter/material.dart';

class DashboardItem {
  final String title;
  final IconData icon;
  final String route;
  const DashboardItem({required this.title, required this.icon, required this.route});
}

class DashboardItems {
  static const DashboardItem andy = DashboardItem(title: "ANDY AI", icon: Icons.auto_awesome, route: "andy");

  static List<DashboardItem> engineer = [
    andy,
    const DashboardItem(title: "Attendance", icon: Icons.fingerprint, route: "attendance"),
    const DashboardItem(title: "My Jobs", icon: Icons.work, route: "jobs"),
    const DashboardItem(title: "Assigned Customers", icon: Icons.people_alt, route: "assigned_customers"),
    const DashboardItem(title: "Customers", icon: Icons.people, route: "customers"),
    const DashboardItem(title: "Walk-In Installation", icon: Icons.person_add_alt_1, route: "walkin"),
    const DashboardItem(title: "Service", icon: Icons.miscellaneous_services, route: "service"),
    const DashboardItem(title: "Engineer Bag", icon: Icons.backpack, route: "bag"),
    const DashboardItem(title: "Part Request", icon: Icons.inventory_2, route: "request"),
    const DashboardItem(title: "QR Verification", icon: Icons.qr_code_scanner, route: "qr"),
    const DashboardItem(title: "Rent Collection", icon: Icons.payments, route: "rent"),
    const DashboardItem(title: "Complaint", icon: Icons.report_problem, route: "complaint"),
    const DashboardItem(title: "Profile", icon: Icons.person, route: "profile"),
  ];

  static List<DashboardItem> admin = [
    andy,
    const DashboardItem(title: "Customers", icon: Icons.people, route: "customers"),
    const DashboardItem(title: "Rent Management", icon: Icons.account_balance_wallet, route: "rent_management"),
    const DashboardItem(title: "Payment History", icon: Icons.receipt_long, route: "payment_history"),
    const DashboardItem(title: "Face & Device Security", icon: Icons.admin_panel_settings, route: "face_security_admin"),
    const DashboardItem(title: "Attendance Selfie Review", icon: Icons.fact_check_outlined, route: "attendance_review_admin"),
    const DashboardItem(title: "Attendance Security Test", icon: Icons.verified_user, route: "attendance_security_test"),
    ...engineer.where((item) => item.route != "andy"),
    const DashboardItem(title: "Live Map", icon: Icons.map, route: "map"),
    const DashboardItem(title: "Engineer Live Location", icon: Icons.location_on, route: "engineer_map"),
  ];

  static List<DashboardItem> manager = [...admin];

  static List<DashboardItem> office = [
    andy,
    const DashboardItem(title: "Customers", icon: Icons.people, route: "customers"),
    const DashboardItem(title: "Rent Management", icon: Icons.account_balance_wallet, route: "rent_management"),
    const DashboardItem(title: "Payment History", icon: Icons.receipt_long, route: "payment_history"),
    const DashboardItem(title: "Walk-In Customer", icon: Icons.person_add_alt_1, route: "walkin"),
    const DashboardItem(title: "Live Map", icon: Icons.map, route: "map"),
    const DashboardItem(title: "Engineer Live", icon: Icons.location_on, route: "engineer_map"),
  ];
}
