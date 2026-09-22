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
  static const DashboardItem andy = DashboardItem(
    title: "ANDY AI\nComing Soon",
    icon: Icons.auto_awesome,
    route: "andy",
  );
  static const DashboardItem reports = DashboardItem(
    title: "Business Reports",
    icon: Icons.analytics_outlined,
    route: "reports",
  );
  static const DashboardItem referral = DashboardItem(
    title: "Refer & Wallet",
    icon: Icons.card_giftcard,
    route: "referral",
  );

  static List<DashboardItem> engineer = [
    andy,
    const DashboardItem(
      title: "Attendance",
      icon: Icons.fingerprint,
      route: "attendance",
    ),
    const DashboardItem(
      title: "Employee HRMS",
      icon: Icons.badge_outlined,
      route: "hrms",
    ),
    const DashboardItem(
      title: "Training",
      icon: Icons.school_rounded,
      route: "training",
    ),
    const DashboardItem(
      title: "Work Calendar",
      icon: Icons.calendar_month,
      route: "work_calendar",
    ),
    const DashboardItem(
      title: "Work Route",
      icon: Icons.route,
      route: "work_route",
    ),
    const DashboardItem(title: "My Jobs", icon: Icons.work, route: "jobs"),
    const DashboardItem(
      title: "Assigned Customers",
      icon: Icons.people_alt,
      route: "assigned_customers",
    ),
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
      route: "rent_management",
    ),
    const DashboardItem(
      title: "Complaint",
      icon: Icons.report_problem,
      route: "complaint",
    ),
    referral,
    const DashboardItem(title: "Profile", icon: Icons.person, route: "profile"),
  ];

  static List<DashboardItem> admin = [
    andy,
    const DashboardItem(
      title: "Employees",
      icon: Icons.badge_rounded,
      route: "employee_management",
    ),
    const DashboardItem(
      title: "Inventory Control",
      icon: Icons.qr_code_2_rounded,
      route: "inventory_workflow",
    ),
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
    const DashboardItem(
      title: "Payment History",
      icon: Icons.receipt_long,
      route: "payment_history",
    ),
    reports,
    const DashboardItem(
      title: "Face & Device Security",
      icon: Icons.admin_panel_settings,
      route: "face_security_admin",
    ),
    const DashboardItem(
      title: "Password Reset Approvals",
      icon: Icons.lock_reset_rounded,
      route: "password_reset_approvals",
    ),
    const DashboardItem(
      title: "Role Access Control",
      icon: Icons.manage_accounts_rounded,
      route: "role_access_control",
    ),
    const DashboardItem(
      title: "Notifications & Offers",
      icon: Icons.notifications_active_rounded,
      route: "notification_offer_admin",
    ),
    const DashboardItem(
      title: "Attendance Selfie Review",
      icon: Icons.fact_check_outlined,
      route: "attendance_review_admin",
    ),
    const DashboardItem(
      title: "Attendance Security Test",
      icon: Icons.verified_user,
      route: "attendance_security_test",
    ),
    const DashboardItem(
      title: "Device Health Center",
      icon: Icons.health_and_safety_outlined,
      route: "device_health_admin",
    ),
    ...engineer.where(
      (item) =>
          item.route != "andy" &&
          item.route != "customers" &&
          item.route != "rent_management",
    ),
    const DashboardItem(title: "Live Map", icon: Icons.map, route: "map"),
    const DashboardItem(
      title: "Engineer Live Location",
      icon: Icons.location_on,
      route: "engineer_map",
    ),
  ];

  static List<DashboardItem> manager = [...admin];

  static List<DashboardItem> office = [
    const DashboardItem(
      title: "Attendance",
      icon: Icons.fingerprint,
      route: "attendance",
    ),
    const DashboardItem(
      title: "Employee HRMS",
      icon: Icons.badge_outlined,
      route: "hrms",
    ),
    const DashboardItem(
      title: "Training",
      icon: Icons.school_rounded,
      route: "training",
    ),
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
      title: "Rent Management",
      icon: Icons.account_balance_wallet,
      route: "rent_management",
    ),
    const DashboardItem(
      title: "Payment History",
      icon: Icons.receipt_long,
      route: "payment_history",
    ),
    const DashboardItem(
      title: "Business Reports",
      icon: Icons.analytics_outlined,
      route: "reports",
    ),
    const DashboardItem(
      title: "Inventory Control",
      icon: Icons.qr_code_2_rounded,
      route: "inventory_workflow",
    ),
    const DashboardItem(
      title: "Work Calendar",
      icon: Icons.calendar_month,
      route: "work_calendar",
    ),
    const DashboardItem(
      title: "Work Route",
      icon: Icons.route,
      route: "work_route",
    ),
    const DashboardItem(
      title: "Complaint",
      icon: Icons.report_problem,
      route: "complaint",
    ),
    referral,
    const DashboardItem(title: "Profile", icon: Icons.person, route: "profile"),
  ];

  static List<DashboardItem> calling = [
    const DashboardItem(
      title: "Attendance",
      icon: Icons.fingerprint,
      route: "attendance",
    ),
    const DashboardItem(
      title: "Employee HRMS",
      icon: Icons.badge_outlined,
      route: "hrms",
    ),
    const DashboardItem(
      title: "Training",
      icon: Icons.school_rounded,
      route: "training",
    ),
    const DashboardItem(
      title: "Calling Desk",
      icon: Icons.headset_mic_rounded,
      route: "calling_desk",
    ),
    const DashboardItem(title: "Profile", icon: Icons.person, route: "profile"),
  ];
}
