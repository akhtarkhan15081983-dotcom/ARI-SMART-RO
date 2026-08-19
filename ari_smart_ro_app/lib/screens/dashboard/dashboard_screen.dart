import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../models/attendance_model.dart';

import '../../services/api_service.dart';
import '../../services/attendance_service.dart';
import '../../services/live_location_service.dart';

import '../attendance/attendance_screen.dart';
import '../assigned_customers/assigned_customers_screen.dart';
import '../bag/my_bag_screen.dart';
import '../engineer/map_screen.dart';
import '../jobs/my_jobs_screen.dart';
import '../qr/qr_scanner_screen.dart';
import '../walkin/walkin_customer_screen.dart';
import '../customer/customer_list_screen.dart';
import '../customer/my_ro_screen.dart';
import '../rent/rent_payment_screen.dart';
import '../rent/rent_management_screen.dart';
import '../rent/payment_history_screen.dart';

import '../service/service_list_screen.dart';
import '../complaint/complaint_list_screen.dart';

import '../profile/profile_screen.dart';
import '../login/login_screen.dart';

import 'dashboard_card.dart';
import 'dashboard_items.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
  });

  @override
  State<DashboardScreen> createState() =>
      _DashboardScreenState();
}

class _DashboardScreenState
    extends State<DashboardScreen> {
  // ============================================================
  // SERVICES
  // ============================================================

  final AttendanceService _attendanceService =
      AttendanceService();

  final LiveLocationService _liveLocationService =
      LiveLocationService();

  // ============================================================
  // CUSTOMER DASHBOARD ITEMS
  // ============================================================

  static const List<DashboardItem> _customerItems = [
    DashboardItem(
      title: 'My RO',
      icon: Icons.water_drop,
      route: 'my_ro',
    ),

    DashboardItem(
      title: 'Rent & Payment',
      icon: Icons.payments,
      route: 'rent',
    ),

    DashboardItem(
      title: 'Service',
      icon: Icons.miscellaneous_services,
      route: 'service',
    ),

    DashboardItem(
      title: 'Complaint',
      icon: Icons.report_problem,
      route: 'complaint',
    ),

    DashboardItem(
      title: 'Referral',
      icon: Icons.card_giftcard,
      route: 'referral',
    ),

    DashboardItem(
      title: 'Shop',
      icon: Icons.shopping_cart,
      route: 'shop',
    ),

    DashboardItem(
      title: 'History',
      icon: Icons.history,
      route: 'history',
    ),

    DashboardItem(
      title: 'Profile',
      icon: Icons.person,
      route: 'profile',
    ),
  ];

  // ============================================================
  // STATE
  // ============================================================

  AttendanceModel? _todayAttendance;

  String _role = 'CUSTOMER';

  bool _isLoadingAttendance = true;

  bool _isLoadingRole = true;

  // Prevent multiple exit dialogs from opening.
  bool _isExitDialogShowing = false;

  // ============================================================
  // INIT
  // ============================================================

  @override
  void initState() {
    super.initState();

    _loadDashboard();

    _startLiveLocationIfRequired();
  }

  // ============================================================
  // START LIVE LOCATION
  // ============================================================

  Future<void> _startLiveLocationIfRequired() async {
    try {
      final role =
          await ApiService.getRole();

      final normalisedRole =
          _normaliseRole(role);

      if (normalisedRole == 'ENGINEER') {
        _liveLocationService.startTracking();
      }
    } catch (e) {
      debugPrint(
        "LIVE LOCATION START ERROR: $e",
      );
    }
  }

  // ============================================================
  // LOAD DASHBOARD
  // ============================================================

  Future<void> _loadDashboard() async {
    await _loadRole();

    if (_role != 'CUSTOMER') {
      await _loadAttendance();
    } else {
      if (mounted) {
        setState(() {
          _isLoadingAttendance = false;
        });
      }
    }
  }

  // ============================================================
  // LOAD ATTENDANCE
  // ============================================================

  Future<void> _loadAttendance() async {
    try {
      final attendance =
          await _attendanceService
              .todayAttendance();

      if (!mounted) return;

      setState(() {
        _todayAttendance = attendance;

        _isLoadingAttendance = false;
      });
    } catch (e) {
      debugPrint(
        "ATTENDANCE ERROR: $e",
      );

      if (!mounted) return;

      setState(() {
        _isLoadingAttendance = false;
      });
    }
  }

  // ============================================================
  // LOAD ROLE
  // ============================================================

  Future<void> _loadRole() async {
    try {
      final storedRole =
          await ApiService.getRole();

      if (!mounted) return;

      setState(() {
        _role = _normaliseRole(
          storedRole,
        );

        _isLoadingRole = false;
      });
    } catch (e) {
      debugPrint(
        "ROLE LOAD ERROR: $e",
      );

      if (!mounted) return;

      setState(() {
        _role = 'CUSTOMER';

        _isLoadingRole = false;
      });
    }
  }

  // ============================================================
  // NORMALISE ROLE
  // ============================================================

  String _normaliseRole(
    String? role,
  ) {
    final value =
        role
            ?.trim()
            .toUpperCase()
            .replaceAll(
              'ROLE_',
              '',
            );

    switch (value) {
      case 'ADMIN':
        return 'ADMIN';

      case 'MANAGER':
        return 'MANAGER';

      case 'OFFICE':
        return 'OFFICE';

      case 'ENGINEER':
        return 'ENGINEER';

      case 'CUSTOMER':
        return 'CUSTOMER';

      default:
        return 'CUSTOMER';
    }
  }

  // ============================================================
  // DASHBOARD ITEMS
  // ============================================================

  List<DashboardItem> get _dashboardItems {
    switch (_role) {
      case 'ADMIN':
        return DashboardItems.admin;

      case 'MANAGER':
        return DashboardItems.manager;

      case 'OFFICE':
        return DashboardItems.office;

      case 'ENGINEER':
        return DashboardItems.engineer;

      case 'CUSTOMER':
      default:
        return _customerItems;
    }
  }

  // ============================================================
  // LOGOUT
  // ============================================================

  Future<void> _logout() async {
    final confirm =
        await showDialog<bool>(
      context: context,
      builder: (_) {
        return AlertDialog(
          title: const Text(
            "Logout",
          ),
          content: const Text(
            "Are you sure you want to logout?",
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(
                  context,
                  false,
                );
              },
              child: const Text(
                "Cancel",
              ),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(
                  context,
                  true,
                );
              },
              child: const Text(
                "Logout",
              ),
            ),
          ],
        );
      },
    );

    if (confirm != true) {
      return;
    }

    await ApiService.logout();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (_) =>
            const LoginScreen(),
      ),
      (route) => false,
    );
  }

  // ============================================================
  // EXIT APP CONFIRMATION
  // ============================================================

  Future<void> _handleDashboardBack() async {
    // Prevent duplicate dialogs.
    if (_isExitDialogShowing) {
      return;
    }

    _isExitDialogShowing = true;

    final shouldExit =
        await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text(
            "Exit App?",
          ),
          content: const Text(
            "Are you sure you want to exit the app?",
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(
                  dialogContext,
                ).pop(false);
              },
              child: const Text(
                "Cancel",
              ),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.of(
                  dialogContext,
                ).pop(true);
              },
              child: const Text(
                "Exit",
              ),
            ),
          ],
        );
      },
    );

    _isExitDialogShowing = false;

    if (shouldExit == true) {
      // Close the application.
      await SystemNavigator.pop();
    }
  }

  // ============================================================
  // DASHBOARD ITEM TAP
  // ============================================================

  void _handleItemTap(
    DashboardItem item,
  ) {
    switch (item.route) {
      // ========================================================
      // ATTENDANCE
      // ========================================================

      case 'attendance':
        Navigator.of(context)
            .push(
          MaterialPageRoute(
            builder: (_) =>
                const AttendanceScreen(),
          ),
        )
            .then((_) {
          _loadAttendance();
        });

        return;

      // ========================================================
      // MY JOBS
      // ========================================================

      case 'jobs':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const MyJobsScreen(),
          ),
        );

        return;

      // ========================================================
      // ASSIGNED CUSTOMERS
      // ========================================================

      case 'assigned_customers':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const AssignedCustomersScreen(),
          ),
        );

        return;

      // ========================================================
      // ENGINEER BAG
      // ========================================================

      case 'bag':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                MyBagScreen(),
          ),
        );

        return;

      // ========================================================
      // QR
      // ========================================================

      case 'qr':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const QRScanScreen(
              jobId: 0,
            ),
          ),
        );

        return;

      // ========================================================
      // MAP
      // ========================================================

      case 'map':
      case 'engineer_map':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const EngineerMapScreen(),
          ),
        );

        return;

      // ========================================================
      // WALK-IN
      // ========================================================

      case 'walkin':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const WalkInCustomerScreen(),
          ),
        );

        return;

      // ========================================================
      // SERVICE
      // ========================================================

      case 'service':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const ServiceListScreen(),
          ),
        );

        return;

      // ========================================================
      // COMPLAINT
      // ========================================================

      case 'complaint':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const ComplaintListScreen(),
          ),
        );

        return;

      // ========================================================
      // CUSTOMER MANAGEMENT
      // ========================================================

      case 'customers':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const CustomerListScreen(),
          ),
        );

        return;

      // ========================================================
      // CUSTOMER - MY RO
      // ========================================================

      case 'my_ro':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const MyROScreen(),
          ),
        );

        return;

      // ========================================================
      // CUSTOMER - RENT & PAYMENT
      // ========================================================

      case 'rent':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const RentPaymentScreen(),
          ),
        );

        return;

      // ========================================================
      // ADMIN / MANAGER / OFFICE
      // RENT MANAGEMENT
      // ========================================================

      case 'rent_management':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const RentManagementScreen(),
          ),
        );

        return;

      // ========================================================
      // ADMIN / MANAGER / OFFICE
      // PAYMENT HISTORY
      // ========================================================

      case 'payment_history':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const PaymentHistoryScreen(),
          ),
        );

        return;

      // ========================================================
      // CUSTOMER - REFERRAL
      // ========================================================

      case 'referral':
        _showComingSoon(
          "Referral",
          "Referral module is being prepared.",
        );

        return;

      // ========================================================
      // CUSTOMER - SHOP
      // ========================================================

      case 'shop':
        _showComingSoon(
          "Shop",
          "RO and parts shop is being prepared.",
        );

        return;

      // ========================================================
      // CUSTOMER - HISTORY
      // ========================================================

      case 'history':
        _showComingSoon(
          "History",
          "Rent and service history is being prepared.",
        );

        return;

      // ========================================================
      // PROFILE
      // ========================================================

      case 'profile':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) =>
                const ProfileScreen(),
          ),
        );

        return;

      // ========================================================
      // DEFAULT
      // ========================================================

      default:
        _showComingSoon(
          item.title,
          "${item.title} module is being prepared.",
        );
    }
  }

  // ============================================================
  // COMING SOON
  // ============================================================

  void _showComingSoon(
    String title,
    String message,
  ) {
    ScaffoldMessenger.of(context)
        .showSnackBar(
      SnackBar(
        content: Text(
          message,
        ),
        behavior:
            SnackBarBehavior.floating,
      ),
    );
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(
    BuildContext context,
  ) {
    if (_isLoadingRole) {
      return const Scaffold(
        body: Center(
          child:
              CircularProgressIndicator(),
        ),
      );
    }

    final items =
        _dashboardItems;

    final isCustomer =
        _role == 'CUSTOMER';

    return PopScope(
      // --------------------------------------------------------
      // IMPORTANT:
      // Dashboard is the root screen.
      // Phone Back must NOT trigger logout.
      // --------------------------------------------------------

      canPop: false,

      onPopInvokedWithResult:
          (didPop, result) {
        if (didPop) {
          return;
        }

        _handleDashboardBack();
      },

      child: Scaffold(
        // ======================================================
        // APP BAR
        // ======================================================

        appBar: AppBar(
          title: const Text(
            "ARI SMART RO",
          ),

          centerTitle: true,

          actions: [
            IconButton(
              tooltip: "Logout",
              icon: const Icon(
                Icons.logout,
              ),
              onPressed: _logout,
            ),
          ],
        ),

        // ======================================================
        // BODY
        // ======================================================

        body: Column(
          children: [
            // ====================================================
            // ATTENDANCE
            // ====================================================

            if (!isCustomer)
              _AttendanceCard(
                attendance:
                    _todayAttendance,
                isLoading:
                    _isLoadingAttendance,
              ),

            // ====================================================
            // CUSTOMER WELCOME
            // ====================================================

            if (isCustomer)
              Container(
                width:
                    double.infinity,

                margin:
                    const EdgeInsets.fromLTRB(
                  12,
                  12,
                  12,
                  4,
                ),

                padding:
                    const EdgeInsets.all(
                  18,
                ),

                decoration:
                    BoxDecoration(
                  borderRadius:
                      BorderRadius.circular(
                    16,
                  ),

                  gradient:
                      const LinearGradient(
                    colors: [
                      Color(
                        0xFF2196F3,
                      ),
                      Color(
                        0xFF42A5F5,
                      ),
                    ],
                    begin:
                        Alignment.topLeft,
                    end:
                        Alignment.bottomRight,
                  ),
                ),

                child: const Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Welcome to ARI SMART RO",
                      style: TextStyle(
                        color:
                            Colors.white,
                        fontSize: 20,
                        fontWeight:
                            FontWeight.bold,
                      ),
                    ),

                    SizedBox(
                      height: 6,
                    ),

                    Text(
                      "Manage your RO, rent, service and more.",
                      style: TextStyle(
                        color:
                            Colors.white,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),

            // ====================================================
            // DASHBOARD GRID
            // ====================================================

            Expanded(
              child:
                  GridView.builder(
                padding:
                    const EdgeInsets.all(
                  16,
                ),

                itemCount:
                    items.length,

                gridDelegate:
                    const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,

                  childAspectRatio:
                      1.05,

                  crossAxisSpacing:
                      15,

                  mainAxisSpacing:
                      15,
                ),

                itemBuilder:
                    (context, index) {
                  final item =
                      items[index];

                  return DashboardCard(
                    title:
                        item.title,

                    icon:
                        item.icon,

                    onTap: () {
                      _handleItemTap(
                        item,
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // DISPOSE
  // ============================================================

  @override
  void dispose() {
    _liveLocationService
        .stopTracking();

    super.dispose();
  }
}

// =================================================================
// ATTENDANCE CARD
// =================================================================

class _AttendanceCard
    extends StatelessWidget {
  const _AttendanceCard({
    required this.attendance,
    required this.isLoading,
  });

  final AttendanceModel?
      attendance;

  final bool isLoading;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Card(
      margin:
          const EdgeInsets.all(
        12,
      ),

      elevation: 4,

      child: Padding(
        padding:
            const EdgeInsets.all(
          15,
        ),

        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,

          children: [
            const Text(
              "Today's Attendance",
              style: TextStyle(
                fontSize: 18,
                fontWeight:
                    FontWeight.bold,
              ),
            ),

            const SizedBox(
              height: 10,
            ),

            if (isLoading)
              const Center(
                child:
                    CircularProgressIndicator(),
              )
            else if (attendance ==
                null)
              const Text(
                'No Attendance Today',
              )
            else ...[
              Text(
                'Status : ${attendance!.status}',
              ),

              const SizedBox(
                height: 5,
              ),

              Text(
                'Check In : '
                '${attendance!.checkIn ?? '-'}',
              ),

              Text(
                'Check Out : '
                '${attendance!.checkOut ?? '-'}',
              ),

              Text(
                'Working Hours : '
                '${attendance!.workingHours}',
              ),
            ],
          ],
        ),
      ),
    );
  }
}