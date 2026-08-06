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

  static List<DashboardItem> admin = [
    ...engineer,

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

  static List<DashboardItem> manager = admin;

  static List<DashboardItem> office = admin;
}