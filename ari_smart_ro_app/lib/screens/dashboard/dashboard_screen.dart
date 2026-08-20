import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../models/attendance_model.dart';
import '../../services/api_service.dart';
import '../../services/attendance_service.dart';
import '../../services/live_location_service.dart';
import '../admin/face_security_admin_screen.dart';
import '../admin/attendance_security_test_screen.dart';
import '../admin/attendance_review_admin_screen.dart';
import '../attendance/attendance_screen.dart';
import '../assigned_customers/assigned_customers_screen.dart';
import '../bag/my_bag_screen.dart';
import '../bag/part_request_screen.dart';
import '../engineer/map_screen.dart';
import '../jobs/my_jobs_screen.dart';
import '../qr/qr_scanner_screen.dart';
import '../walkin/walkin_customer_screen.dart';
import '../customer/customer_list_screen.dart';
import '../customer/my_ro_screen.dart';
import '../customer/customer_history_screen.dart';
import '../customer/referral_screen.dart';
import '../rent/rent_payment_screen.dart';
import '../rent/rent_management_screen.dart';
import '../rent/payment_history_screen.dart';
import '../service/service_list_screen.dart';
import '../complaint/complaint_list_screen.dart';
import '../profile/profile_screen.dart';
import '../login/login_screen.dart';
import '../shop/shop_screen.dart';
import 'dashboard_card.dart';
import 'dashboard_items.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final AttendanceService _attendanceService = AttendanceService();
  final LiveLocationService _liveLocationService = LiveLocationService();

  static const List<DashboardItem> _customerItems = [
    DashboardItem(title: 'My RO', icon: Icons.water_drop, route: 'my_ro'),
    DashboardItem(title: 'Rent & Payment', icon: Icons.payments, route: 'rent'),
    DashboardItem(title: 'Service', icon: Icons.miscellaneous_services, route: 'service'),
    DashboardItem(title: 'Complaint', icon: Icons.report_problem, route: 'complaint'),
    DashboardItem(title: 'Referral', icon: Icons.card_giftcard, route: 'referral'),
    DashboardItem(title: 'Shop', icon: Icons.shopping_cart, route: 'shop'),
    DashboardItem(title: 'History', icon: Icons.history, route: 'history'),
    DashboardItem(title: 'Profile', icon: Icons.person, route: 'profile'),
  ];

  AttendanceModel? _todayAttendance;
  String _role = 'CUSTOMER';
  bool _isLoadingAttendance = true;
  bool _isLoadingRole = true;
  bool _isExitDialogShowing = false;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
    _startLiveLocationIfRequired();
  }

  Future<void> _startLiveLocationIfRequired() async {
    try {
      final role = await ApiService.getRole();
      if (_normaliseRole(role) == 'ENGINEER') _liveLocationService.startTracking();
    } catch (e) { debugPrint('LIVE LOCATION START ERROR: $e'); }
  }

  Future<void> _loadDashboard() async {
    await _loadRole();
    if (_role != 'CUSTOMER') await _loadAttendance();
    else if (mounted) setState(() => _isLoadingAttendance = false);
  }

  Future<void> _loadAttendance() async {
    try {
      final attendance = await _attendanceService.todayAttendance();
      if (!mounted) return;
      setState(() { _todayAttendance = attendance; _isLoadingAttendance = false; });
    } catch (e) {
      debugPrint('ATTENDANCE ERROR: $e');
      if (mounted) setState(() { _todayAttendance = null; _isLoadingAttendance = false; });
    }
  }

  Future<void> _loadRole() async {
    try {
      final storedRole = await ApiService.getRole();
      if (!mounted) return;
      setState(() { _role = _normaliseRole(storedRole); _isLoadingRole = false; });
    } catch (_) {
      if (mounted) setState(() { _role = 'CUSTOMER'; _isLoadingRole = false; });
    }
  }

  String _normaliseRole(String? role) {
    final value = role?.trim().toUpperCase().replaceAll('ROLE_', '');
    switch (value) {
      case 'ADMIN': case 'MANAGER': case 'OFFICE': case 'ENGINEER': case 'CUSTOMER': return value!;
      default: return 'CUSTOMER';
    }
  }

  List<DashboardItem> get _dashboardItems {
    switch (_role) {
      case 'ADMIN': return DashboardItems.admin;
      case 'MANAGER': return DashboardItems.manager;
      case 'OFFICE': return DashboardItems.office;
      case 'ENGINEER': return DashboardItems.engineer;
      default: return _customerItems;
    }
  }

  bool get _engineerMissingCheckIn =>
      _role == 'ENGINEER' && !_isLoadingAttendance && _todayAttendance == null;

  bool get _engineerReviewRejected =>
      _role == 'ENGINEER' &&
      !_isLoadingAttendance &&
      _todayAttendance?.isReviewRejected == true;

  bool get _engineerCheckedOut =>
      _role == 'ENGINEER' &&
      !_isLoadingAttendance &&
      _todayAttendance?.checkOut != null;

  bool get _engineerWorkLocked =>
      _engineerMissingCheckIn || _engineerReviewRejected || _engineerCheckedOut;

  bool _allowedWhenLocked(String route) => route == 'attendance' || route == 'profile';

  String get _engineerLockMessage {
    if (_engineerReviewRejected) {
      final note = _todayAttendance?.identityReviewNote?.trim();
      return note == null || note.isEmpty
          ? 'Today\'s attendance selfie review was rejected by admin. Work modules are locked. Contact admin.'
          : 'Today\'s attendance selfie review was rejected by admin: $note';
    }
    if (_engineerCheckedOut) {
      return 'You have checked out for today. Work modules are locked.';
    }
    return 'Please check in first to use work modules.';
  }

  void _showWorkLocked() => ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_engineerLockMessage), behavior: SnackBarBehavior.floating),
      );

  Future<void> _logout() async {
    final confirm = await showDialog<bool>(context: context, builder: (_) => AlertDialog(title: const Text('Logout'), content: const Text('Are you sure you want to logout?'), actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')), ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Logout'))]));
    if (confirm != true) return;
    await ApiService.logout();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const LoginScreen()), (route) => false);
  }

  Future<void> _handleDashboardBack() async {
    if (_isExitDialogShowing) return;
    _isExitDialogShowing = true;
    final shouldExit = await showDialog<bool>(context: context, barrierDismissible: false, builder: (dialogContext) => AlertDialog(title: const Text('Exit App?'), content: const Text('Are you sure you want to exit the app?'), actions: [TextButton(onPressed: () => Navigator.of(dialogContext).pop(false), child: const Text('Cancel')), ElevatedButton(onPressed: () => Navigator.of(dialogContext).pop(true), child: const Text('Exit'))]));
    _isExitDialogShowing = false;
    if (shouldExit == true) await SystemNavigator.pop();
  }

  void _push(Widget screen) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));

  Future<void> _handleItemTap(DashboardItem item) async {
    // Re-check the server before every engineer work-module launch so an admin
    // rejection takes effect without requiring a fresh login.
    if (_role == 'ENGINEER' && !_allowedWhenLocked(item.route)) {
      setState(() => _isLoadingAttendance = true);
      await _loadAttendance();
      if (!mounted) return;
      if (_engineerWorkLocked) { _showWorkLocked(); return; }
    }

    switch (item.route) {
      case 'face_security_admin':
        if (_role == 'ADMIN') _push(const FaceSecurityAdminScreen());
        else _showComingSoon('Restricted', 'Only admin can manage face and device re-enrollment.');
        return;
      case 'attendance_review_admin':
        if (_role == 'ADMIN') _push(const AttendanceReviewAdminScreen());
        else _showComingSoon('Restricted', 'Only admin can review attendance selfies.');
        return;
      case 'attendance_security_test':
        if (_role == 'ADMIN') _push(const AttendanceSecurityTestScreen());
        else _showComingSoon('Restricted', 'Only admin can run attendance security tests.');
        return;
      case 'attendance':
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AttendanceScreen())).then((_) => _loadAttendance()); return;
      case 'jobs': _push(const MyJobsScreen()); return;
      case 'assigned_customers': _push(const AssignedCustomersScreen()); return;
      case 'bag': _push(MyBagScreen()); return;
      case 'request': _push(const PartRequestScreen()); return;
      case 'qr': _push(const QRScanScreen(jobId: 0)); return;
      case 'map': case 'engineer_map': _push(const EngineerMapScreen()); return;
      case 'walkin': _push(const WalkInCustomerScreen()); return;
      case 'service': _push(const ServiceListScreen()); return;
      case 'complaint': _push(const ComplaintListScreen()); return;
      case 'customers': _push(const CustomerListScreen()); return;
      case 'my_ro': _push(const MyROScreen()); return;
      case 'rent': _push(const RentPaymentScreen()); return;
      case 'rent_management': _push(const RentManagementScreen()); return;
      case 'payment_history': _push(const PaymentHistoryScreen()); return;
      case 'shop': _push(const ShopScreen()); return;
      case 'referral': _push(const ReferralScreen()); return;
      case 'history': _push(const CustomerHistoryScreen()); return;
      case 'profile': _push(const ProfileScreen()); return;
      default: _showComingSoon(item.title, '${item.title} module is being prepared.');
    }
  }

  void _showComingSoon(String title, String message) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message), behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    if (_isLoadingRole) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final items = _dashboardItems;
    final isCustomer = _role == 'CUSTOMER';
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) { if (!didPop) _handleDashboardBack(); },
      child: Scaffold(
        appBar: AppBar(title: Text(isCustomer ? 'ARI Smart RO' : '$_role Dashboard'), actions: [IconButton(onPressed: _logout, icon: const Icon(Icons.logout), tooltip: 'Logout')]),
        body: RefreshIndicator(
          onRefresh: _loadDashboard,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.all(16),
            children: [
              if (_role == 'ENGINEER' && _engineerWorkLocked) ...[
                Card(
                  color: _engineerReviewRejected ? const Color(0xFFFFE7E7) : const Color(0xFFFFF4E5),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Icon(_engineerReviewRejected ? Icons.gpp_bad_outlined : Icons.lock_clock_outlined, color: _engineerReviewRejected ? const Color(0xFFB42318) : const Color(0xFFB26A00)),
                      const SizedBox(width: 12),
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(_engineerReviewRejected ? 'Attendance review rejected' : 'Work modules locked', style: const TextStyle(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 4),
                        Text(_engineerLockMessage),
                      ])),
                    ]),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (!isCustomer) ...[
                Card(child: Padding(padding: const EdgeInsets.all(16), child: _isLoadingAttendance
                    ? const Center(child: CircularProgressIndicator())
                    : Text(_todayAttendance == null
                        ? 'Attendance not marked today'
                        : _todayAttendance!.isReviewRejected
                            ? 'Attendance review: REJECTED'
                            : _todayAttendance!.isReviewApproved
                                ? 'Attendance review: APPROVED'
                                : 'Attendance review: PENDING'))),
                const SizedBox(height: 16),
              ],
              GridView.builder(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 1.15), itemCount: items.length, itemBuilder: (context, index) { final item = items[index]; return DashboardCard(title: item.title, icon: item.icon, onTap: () => _handleItemTap(item)); }),
            ],
          ),
        ),
      ),
    );
  }
}
