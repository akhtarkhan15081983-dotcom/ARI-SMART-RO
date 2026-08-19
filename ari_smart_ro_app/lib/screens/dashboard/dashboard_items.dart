import 'package:flutter/material.dart';

class DashboardItem {
  final String title;
  final IconData icon;
  final String route;

  const DashboardItem({
    required this.title,
    required this.icon,
    required this.route,
  });
}

class DashboardItems {
  // ============================================================
  // ENGINEER DASHBOARD
  // ============================================================

  static List<DashboardItem> engineer = [
    const DashboardItem(
      title: "Attendance",
      icon: Icons.fingerprint,
      route: "attendance",
    ),

    const DashboardItem(
      title: "My Jobs",
      icon: Icons.work,
      route: "jobs",
    ),

    const DashboardItem(
      title: "Assigned Customers",
      icon: Icons.people_alt,
      route: "assigned_customers",
    ),

    // ----------------------------------------------------------
    // CUSTOMER SEARCH
    // ----------------------------------------------------------

    const DashboardItem(
      title: "Customers",
      icon: Icons.people,
      route: "customers",
    ),

    const DashboardItem(
      title: "Walk-In Installation",
      icon: Icons.person_add_alt_1,
      route: "walkin",
    ),

    const DashboardItem(
      title: "Service",
      icon: Icons.miscellaneous_services,
      route: "service",
    ),

    const DashboardItem(
      title: "Engineer Bag",
      icon: Icons.backpack,
      route: "bag",
    ),

    const DashboardItem(
      title: "Part Request",
      icon: Icons.inventory_2,
      route: "request",
    ),

    const DashboardItem(
      title: "QR Verification",
      icon: Icons.qr_code_scanner,
      route: "qr",
    ),

    const DashboardItem(
      title: "Rent Collection",
      icon: Icons.payments,
      route: "rent",
    ),

    const DashboardItem(
      title: "Complaint",
      icon: Icons.report_problem,
      route: "complaint",
    ),

    const DashboardItem(
      title: "Profile",
      icon: Icons.person,
      route: "profile",
    ),
  ];

  // ============================================================
  // ADMIN DASHBOARD
  // ============================================================

  static List<DashboardItem> admin = [
    // ----------------------------------------------------------
    // CUSTOMER MANAGEMENT
    // ----------------------------------------------------------

    const DashboardItem(
      title: "Customers",
      icon: Icons.people,
      route: "customers",
    ),

    // ----------------------------------------------------------
    // RENT MANAGEMENT
    // ----------------------------------------------------------

    const DashboardItem(
      title: "Rent Management",
      icon: Icons.account_balance_wallet,
      route: "rent_management",
    ),

    // ----------------------------------------------------------
    // PAYMENT HISTORY
    // ----------------------------------------------------------

    const DashboardItem(
      title: "Payment History",
      icon: Icons.receipt_long,
      route: "payment_history",
    ),

    // ----------------------------------------------------------
    // ENGINEER MODULES
    // ----------------------------------------------------------

    ...engineer,

    // ----------------------------------------------------------
    // LIVE MAP
    // ----------------------------------------------------------

    const DashboardItem(
      title: "Live Map",
      icon: Icons.map,
      route: "map",
    ),

    const DashboardItem(
      title: "Engineer Live Location",
      icon: Icons.location_on,
      route: "engineer_map",
    ),
  ];

  // ============================================================
  // MANAGER DASHBOARD
  // ============================================================

  static List<DashboardItem> manager = [
    ...admin,
  ];

  // ============================================================
  // OFFICE DASHBOARD
  // ============================================================

  static List<DashboardItem> office = [
    const DashboardItem(
      title: "Customers",
      icon: Icons.people,
      route: "customers",
    ),

    const DashboardItem(
      title: "Rent Management",
      icon: Icons.account_balance_wallet,
      route: "rent_management",
    ),

    // ----------------------------------------------------------
    // PAYMENT HISTORY
    // ----------------------------------------------------------

    const DashboardItem(
      title: "Payment History",
      icon: Icons.receipt_long,
      route: "payment_history",
    ),

    const DashboardItem(
      title: "Walk-In Customer",
      icon: Icons.person_add_alt_1,
      route: "walkin",
    ),

    const DashboardItem(
      title: "Live Map",
      icon: Icons.map,
      route: "map",
    ),

    const DashboardItem(
      title: "Engineer Live",
      icon: Icons.location_on,
      route: "engineer_map",
    ),
  ];
}