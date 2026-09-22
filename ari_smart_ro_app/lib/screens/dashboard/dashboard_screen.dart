import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../models/attendance_model.dart';
import '../../services/api_service.dart';
import '../../services/attendance_service.dart';
import '../../services/live_location_service.dart';
import '../../services/saas_admin_service.dart';
import '../../services/role_permission_service.dart';
import '../../services/notification_center_service.dart';
import '../../utils/search_utils.dart';
import '../admin/face_security_admin_screen.dart';
import '../admin/attendance_security_test_screen.dart';
import '../admin/attendance_review_admin_screen.dart';
import '../admin/engineer_bag_admin_screen.dart';
import '../admin/saas_super_admin_screen.dart';
import '../admin/password_reset_approval_screen.dart';
import '../admin/role_access_control_screen.dart';
import '../admin/notification_offer_admin_screen.dart';
import '../notifications/notification_center_screen.dart';
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
import '../reports/reports_screen.dart';
import '../service/service_list_screen.dart';
import '../complaint/complaint_list_screen.dart';
import '../profile/profile_screen.dart';
import '../login/login_screen.dart';
import '../shop/shop_screen.dart';
import '../work_planner/work_calendar_screen.dart';
import '../work_planner/work_route_screen.dart';
import '../hrms/hrms_screen.dart';
import '../hrms/training_screen.dart';
import '../hrms/employee_management_screen.dart';
import '../inventory/inventory_workflow_screen.dart';
import '../calling/calling_desk_screen.dart';
import 'dashboard_card.dart';
import 'dashboard_items.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with WidgetsBindingObserver {
  final AttendanceService _attendanceService = AttendanceService();
  final LiveLocationService _liveLocationService = LiveLocationService();
  final SaasAdminService _saasAdminService = const SaasAdminService();
  final RolePermissionService _rolePermissionService =
      const RolePermissionService();
  final NotificationCenterService _notificationCenterService =
      const NotificationCenterService();
  static const List<DashboardItem> _customerItems = [
    DashboardItems.andy,
    DashboardItem(title: 'My RO', icon: Icons.water_drop, route: 'my_ro'),
    DashboardItem(title: 'Rent & Payment', icon: Icons.payments, route: 'rent'),
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
    DashboardItems.referral,
    DashboardItem(title: 'Shop', icon: Icons.shopping_cart, route: 'shop'),
    DashboardItem(title: 'History', icon: Icons.history, route: 'history'),
    DashboardItem(title: 'Profile', icon: Icons.person, route: 'profile'),
  ];
  AttendanceModel? _todayAttendance;
  String _role = 'CUSTOMER';
  bool _isPlatformSuperAdmin = false;
  Set<String> _allowedFeatures = const {};
  int _notificationUnread = 0;
  bool _isLoadingAttendance = true,
      _isLoadingRole = true,
      _isExitDialogShowing = false;

  Timer? _dashboardRefreshTimer;
  final _toolSearchController = TextEditingController();
  String _toolQuery = '';
  String? _locationComplianceError;
  String? _windowsWorkspace;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadDashboard();
    _dashboardRefreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      if (mounted) _refreshSessionAndDashboard();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && mounted) {
      _refreshSessionAndDashboard();
    }
  }

  Future<void> _refreshSessionAndDashboard() async {
    await ApiService.ensureValidSession();
    if (mounted) await _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    await _loadRole();
    if (_role == 'ADMIN') {
      final allowed = await _saasAdminService.canAccess();
      if (mounted) setState(() => _isPlatformSuperAdmin = allowed);
    }
    if (_role != 'CUSTOMER') {
      try {
        final data = await _rolePermissionService.getPermissions(role: _role);
        final allowed = (data['allowed_features'] as List<dynamic>? ?? const [])
            .map((e) => e.toString())
            .toSet();
        if (mounted) setState(() => _allowedFeatures = allowed);
      } catch (_) {
        if (mounted) setState(() => _allowedFeatures = const {});
      }
    }
    if (_role != 'CUSTOMER') {
      await _loadAttendance();
    } else if (mounted) {
      setState(() => _isLoadingAttendance = false);
    }
    try {
      final notifications = await _notificationCenterService.fetch();
      if (mounted) setState(() => _notificationUnread = notifications.unreadCount);
    } catch (_) {
      // Notification center must never block the dashboard.
    }
  }

  Future<void> _loadAttendance() async {
    try {
      final a = await _attendanceService.todayAttendance();
      if (mounted) {
        setState(() {
          _todayAttendance = a;
          _isLoadingAttendance = false;
        });
      }
      await _syncLiveLocationWithAttendance(a);
    } catch (e) {
      if (mounted) {
        setState(() {
          _todayAttendance = null;
          _isLoadingAttendance = false;
        });
      }
      await _liveLocationService.stopTracking();
    }
  }

  bool _hasActiveOvertime(AttendanceModel attendance) {
    final overtime = attendance.overtime;
    if (overtime == null) return false;
    return (overtime['status'] ?? '').toString().toUpperCase() == 'APPROVED' &&
        overtime['started_at'] != null &&
        overtime['ended_at'] == null;
  }

  Future<void> _syncLiveLocationWithAttendance(
    AttendanceModel? attendance,
  ) async {
    final shouldTrack = attendance != null &&
        attendance.checkIn != null &&
        (attendance.checkOut == null || _hasActiveOvertime(attendance));
    try {
      if (shouldTrack) {
        await _liveLocationService.startTracking(requestPermissions: true);
      } else {
        await _liveLocationService.stopTracking();
      }
      if (mounted && _locationComplianceError != null) {
        setState(() => _locationComplianceError = null);
      }
    } on LiveLocationException catch (e) {
      debugPrint('LIVE LOCATION ATTENDANCE SYNC ERROR: $e');
      if (mounted) setState(() => _locationComplianceError = e.message);
    } catch (e) {
      debugPrint('LIVE LOCATION ATTENDANCE SYNC ERROR: $e');
      if (mounted) {
        setState(() {
          _locationComplianceError =
              'Live location could not start. Turn on GPS and allow location all the time.';
        });
      }
    }
  }

  Future<void> _loadRole() async {
    try {
      final r = await ApiService.getRole();
      if (mounted) {
        setState(() {
          _role = _normaliseRole(r);
          _isLoadingRole = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _role = 'CUSTOMER';
          _isLoadingRole = false;
        });
      }
    }
  }

  String _normaliseRole(String? role) {
    final v = role?.trim().toUpperCase().replaceAll('ROLE_', '');
    return {'ADMIN', 'MANAGER', 'OFFICE', 'CALLING', 'ENGINEER', 'CUSTOMER'}.contains(v)
        ? v!
        : 'CUSTOMER';
  }

  List<DashboardItem> _applyRolePermissions(List<DashboardItem> items) {
    if (_role == 'ADMIN' || _role == 'CUSTOMER') return items;
    if (_allowedFeatures.isEmpty) return const [];
    const alwaysVisible = {'andy'};
    return items
        .where(
          (item) =>
              alwaysVisible.contains(item.route) ||
              _allowedFeatures.contains(item.route),
        )
        .toList();
  }

  List<DashboardItem> get _dashboardItems {
    switch (_role) {
      case 'ADMIN':
        return [
          if (_isPlatformSuperAdmin)
            const DashboardItem(
              title: 'SaaS Command Center',
              icon: Icons.public_rounded,
              route: 'saas_super_admin',
            ),
          ...DashboardItems.admin,
        ];
      case 'MANAGER':
        return _applyRolePermissions(DashboardItems.manager);
      case 'OFFICE':
        return _applyRolePermissions(DashboardItems.office);
      case 'CALLING':
        return _applyRolePermissions(DashboardItems.calling);
      case 'ENGINEER':
        return _applyRolePermissions(DashboardItems.engineer);
      default:
        return _customerItems;
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
  bool get _engineerLocationBlocked =>
      _role == 'ENGINEER' &&
      !_isLoadingAttendance &&
      _todayAttendance?.checkIn != null &&
      _todayAttendance?.checkOut == null &&
      _locationComplianceError != null;
  bool get _engineerWorkLocked =>
      _engineerMissingCheckIn ||
      _engineerReviewRejected ||
      _engineerCheckedOut ||
      _engineerLocationBlocked;
  bool _allowedWhenLocked(String route) =>
      route == 'attendance' ||
      route == 'profile' ||
      route == 'training' ||
      route == 'andy';
  String get _engineerLockMessage {
    if (_engineerLocationBlocked) {
      return '${_locationComplianceError!} Work modules stay locked until live location is restored.';
    }
    if (_engineerReviewRejected) {
      final n = _todayAttendance?.identityReviewNote?.trim();
      return n == null || n.isEmpty
          ? 'Today\'s attendance selfie review was rejected by admin. Work modules are locked. Contact admin.'
          : 'Today\'s attendance selfie review was rejected by admin: $n';
    }
    if (_engineerCheckedOut) {
      return 'You have checked out for today. Work modules are locked.';
    }
    return 'Please check in first to use work modules.';
  }

  void _showWorkLocked() => ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(_engineerLockMessage),
      behavior: SnackBarBehavior.floating,
    ),
  );
  Future<void> _logout() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Logout'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await _liveLocationService.stopTracking();
    await ApiService.logout();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  Future<void> _handleDashboardBack() async {
    if (_isExitDialogShowing) return;
    _isExitDialogShowing = true;
    final exit = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (c) => AlertDialog(
        title: const Text('Exit App?'),
        content: const Text('Are you sure you want to exit the app?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Exit'),
          ),
        ],
      ),
    );
    _isExitDialogShowing = false;
    if (exit == true) await SystemNavigator.pop();
  }

  void _push(Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));

  Future<void> _handleItemTap(DashboardItem item) async {
    if (_role == 'ENGINEER' && !_allowedWhenLocked(item.route)) {
      setState(() => _isLoadingAttendance = true);
      await _loadAttendance();
      if (!mounted) return;
      if (_engineerWorkLocked) {
        _showWorkLocked();
        return;
      }
    }
    switch (item.route) {
      case 'saas_super_admin':
        if (_isPlatformSuperAdmin) {
          _push(const SaasSuperAdminScreen());
        } else {
          _showComingSoon('Platform super-admin access is required.');
        }
        return;
      case 'andy':
        _showComingSoon(
          'ANDY AI voice assistant is coming soon. Baaki ARI SMART RO services abhi available hain.',
        );
        return;
      case 'face_security_admin':
        if (_role == 'ADMIN') {
          _push(const FaceSecurityAdminScreen());
        } else {
          _showComingSoon('Restricted');
        }
        return;
      case 'password_reset_approvals':
        if (_role == 'ADMIN') {
          _push(const PasswordResetApprovalScreen());
        } else {
          _showComingSoon('Restricted');
        }
        return;
      case 'role_access_control':
        if (_role == 'ADMIN') {
          _push(const RoleAccessControlScreen());
        } else {
          _showComingSoon('Only admin can control role access.');
        }
        return;
      case 'notification_offer_admin':
        if (_role == 'ADMIN') {
          _push(const NotificationOfferAdminScreen());
        } else {
          _showComingSoon('Only admin can manage notifications and offers.');
        }
        return;
      case 'attendance_review_admin':
        if (_role == 'ADMIN') {
          _push(const AttendanceReviewAdminScreen());
        } else {
          _showComingSoon('Restricted');
        }
        return;
      case 'attendance_security_test':
        if (_role == 'ADMIN') {
          _push(const AttendanceSecurityTestScreen());
        } else {
          _showComingSoon('Restricted');
        }
        return;
      case 'attendance':
        Navigator.of(context)
            .push(MaterialPageRoute(builder: (_) => const AttendanceScreen()))
            .then((_) => _loadAttendance());
        return;
      case 'calling_desk':
        if (_role == 'ADMIN' || _allowedFeatures.contains('calling_desk')) {
          _push(const CallingDeskScreen());
        } else {
          _showComingSoon('Calling desk permission is required.');
        }
        return;
      case 'jobs':
        _push(const MyJobsScreen());
        return;
      case 'assigned_customers':
        _push(const AssignedCustomersScreen());
        return;
      case 'work_calendar':
        _push(const WorkCalendarScreen());
        return;
      case 'work_route':
        _push(WorkRouteScreen(date: DateTime.now()));
        return;
      case 'hrms':
        _push(const HrmsScreen());
        return;
      case 'training':
        _push(const TrainingScreen());
        return;
      case 'employee_management':
        if (_role == 'ADMIN' || _allowedFeatures.contains('employee_management')) {
          _push(const EmployeeManagementScreen());
        } else {
          _showComingSoon('Employee management permission is required.');
        }
        return;
      case 'inventory_workflow':
        if (_role == 'ADMIN' || _allowedFeatures.contains('inventory_workflow')) {
          _push(const InventoryWorkflowScreen());
        } else {
          _showComingSoon('Inventory control permission is required.');
        }
        return;
      case 'bag':
        if (_role == 'ADMIN' || _role == 'MANAGER') {
          _push(const EngineerBagAdminScreen());
        } else {
          _push(MyBagScreen());
        }
        return;
      case 'request':
        _push(const PartRequestScreen());
        return;
      case 'qr':
        _push(const QRScanScreen(jobId: 0));
        return;
      case 'map':
      case 'engineer_map':
        _push(const EngineerMapScreen());
        return;
      case 'walkin':
        _push(const WalkInCustomerScreen());
        return;
      case 'service':
        _push(const ServiceListScreen());
        return;
      case 'complaint':
        _push(const ComplaintListScreen());
        return;
      case 'customers':
        _push(const CustomerListScreen());
        return;
      case 'my_ro':
        _push(const MyROScreen());
        return;
      case 'rent':
        _push(const RentPaymentScreen());
        return;
      case 'rent_management':
        _push(const RentManagementScreen());
        return;
      case 'payment_history':
        _push(const PaymentHistoryScreen());
        return;
      case 'shop':
        _push(const ShopScreen());
        return;
      case 'referral':
        _push(const ReferralScreen());
        return;
      case 'history':
        _push(const CustomerHistoryScreen());
        return;
      case 'reports':
        _push(const ReportsScreen());
        return;
      case 'profile':
        _push(const ProfileScreen());
        return;
      default:
        _showComingSoon('${item.title} is being prepared.');
    }
  }

  void _showComingSoon(String message) =>
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
      );

  List<_DashboardGroup> _dashboardGroups(List<DashboardItem> items) {
    const routes = <String, Set<String>>{
      'Customers': {
        'customers',
        'assigned_customers',
        'walkin',
        'referral',
        'history',
      },
      'Operations': {
        'jobs',
        'work_calendar',
        'work_route',
        'service',
        'complaint',
        'map',
        'engineer_map',
        'calling_desk',
      },
      'Finance': {
        'rent',
        'rent_management',
        'payment_history',
        'reports',
        'qr',
      },
      'Employees': {
        'employee_management',
        'hrms',
        'attendance',
        'attendance_review_admin',
        'attendance_security_test',
        'face_security_admin',
      },
      'Inventory': {
        'inventory_workflow',
        'bag',
        'request',
        'asset_selection',
        'installation',
        'shop',
      },
    };
    final definitions = [
      ('Customers', Icons.groups_rounded, const Color(0xFF2563EB)),
      ('Operations', Icons.route_rounded, const Color(0xFF0891B2)),
      (
        'Finance',
        Icons.account_balance_wallet_rounded,
        const Color(0xFF059669),
      ),
      ('Employees', Icons.badge_rounded, const Color(0xFF7C3AED)),
      ('Inventory', Icons.inventory_2_rounded, const Color(0xFFEA580C)),
      ('Control', Icons.admin_panel_settings_rounded, const Color(0xFF334155)),
    ];
    final assigned = routes.values.expand((set) => set).toSet();
    return definitions
        .map((definition) {
          final groupItems = definition.$1 == 'Control'
              ? items.where((item) => !assigned.contains(item.route)).toList()
              : items
                    .where(
                      (item) => routes[definition.$1]!.contains(item.route),
                    )
                    .toList();
          return _DashboardGroup(
            title: definition.$1,
            icon: definition.$2,
            color: definition.$3,
            items: groupItems,
          );
        })
        .where((group) => group.items.isNotEmpty)
        .toList();
  }

  Future<void> _openDashboardGroup(_DashboardGroup group) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(sheetContext).height * .72,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
                child: Row(
                  children: [
                    CircleAvatar(
                      backgroundColor: group.color.withValues(alpha: .12),
                      child: Icon(group.icon, color: group.color),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          group.title,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Text('${group.items.length} tools'),
                      ],
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 1.35,
                  ),
                  itemCount: group.items.length,
                  itemBuilder: (_, index) {
                    final item = group.items[index];
                    return DashboardCard(
                      title: item.title,
                      icon: item.icon,
                      onTap: () {
                        Navigator.pop(sheetContext);
                        Future<void>.delayed(
                          const Duration(milliseconds: 300),
                          () => _handleItemTap(item),
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _dashboardRefreshTimer?.cancel();
    _toolSearchController.dispose();
    WidgetsBinding.instance.removeObserver(this);
    _liveLocationService.stopTracking();
    super.dispose();
  }

  Widget _buildWindowsDashboard({
    required List<DashboardItem> items,
    required bool isCustomer,
  }) {
    final groups = _dashboardGroups(items);
    final selected = groups.isEmpty
        ? null
        : groups.where((group) => group.title == _windowsWorkspace).firstOrNull ??
            groups.first;

    return ColoredBox(
      color: const Color(0xFFF4F7FB),
      child: Row(
        children: [
          Container(
            width: 264,
            decoration: const BoxDecoration(
              color: Color(0xFF0B2940),
              boxShadow: [
                BoxShadow(
                  color: Color(0x22000000),
                  blurRadius: 18,
                  offset: Offset(6, 0),
                ),
              ],
            ),
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 24, 22, 18),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: const Color(0xFF19A7A0),
                          borderRadius: BorderRadius.circular(13),
                        ),
                        child: const Icon(
                          Icons.water_drop_rounded,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'ARI SMART RO',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                                fontSize: 16,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Business Suite',
                              style: TextStyle(
                                color: Color(0xFFA9BED0),
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(color: Color(0xFF25445B), height: 1),
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 18, 14, 8),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'WORKSPACES',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: .48),
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.1,
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    itemCount: groups.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 6),
                    itemBuilder: (_, index) {
                      final group = groups[index];
                      final active = selected?.title == group.title;
                      return Material(
                        color: active
                            ? Colors.white.withValues(alpha: .12)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(12),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(12),
                          onTap: () =>
                              setState(() => _windowsWorkspace = group.title),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 13,
                              vertical: 12,
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  group.icon,
                                  color: active
                                      ? Colors.white
                                      : const Color(0xFFA9BED0),
                                  size: 21,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    group.title,
                                    style: TextStyle(
                                      color: active
                                          ? Colors.white
                                          : const Color(0xFFC5D3DF),
                                      fontWeight: active
                                          ? FontWeight.w800
                                          : FontWeight.w600,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 7,
                                    vertical: 3,
                                  ),
                                  decoration: BoxDecoration(
                                    color: active
                                        ? group.color
                                        : Colors.white.withValues(alpha: .07),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    '${group.items.length}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: .06),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    child: Row(
                      children: [
                        const CircleAvatar(
                          radius: 17,
                          backgroundColor: Color(0xFF19A7A0),
                          child: Icon(Icons.person, color: Colors.white, size: 19),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _role,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(34, 28, 34, 44),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1420),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  isCustomer
                                      ? 'Welcome to ARI SMART RO'
                                      : 'Business Command Center',
                                  style: const TextStyle(
                                    color: Color(0xFF102A43),
                                    fontSize: 29,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Manage your complete RO business from one desktop workspace.',
                                  style: TextStyle(
                                    color: const Color(0xFF486581)
                                        .withValues(alpha: .88),
                                    fontSize: 14,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          SizedBox(
                            width: 430,
                            child: TextField(
                              controller: _toolSearchController,
                              textInputAction: TextInputAction.search,
                              onChanged: (value) =>
                                  setState(() => _toolQuery = value),
                              decoration: InputDecoration(
                                filled: true,
                                fillColor: Colors.white,
                                hintText: 'Search tools and reports',
                                prefixIcon: const Icon(Icons.search),
                                suffixIcon: _toolQuery.isEmpty
                                    ? null
                                    : IconButton(
                                        onPressed: () {
                                          _toolSearchController.clear();
                                          setState(() => _toolQuery = '');
                                        },
                                        icon: const Icon(Icons.clear),
                                      ),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(14),
                                  borderSide: const BorderSide(
                                    color: Color(0xFFD9E2EC),
                                  ),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(14),
                                  borderSide: const BorderSide(
                                    color: Color(0xFFD9E2EC),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 26),
                      Row(
                        children: [
                          _WindowsOverviewCard(
                            icon: Icons.grid_view_rounded,
                            color: const Color(0xFF2563EB),
                            value: '${groups.length}',
                            label: 'Workspaces',
                          ),
                          const SizedBox(width: 14),
                          _WindowsOverviewCard(
                            icon: Icons.apps_rounded,
                            color: const Color(0xFF7C3AED),
                            value: '${items.length}',
                            label: 'Available tools',
                          ),
                          if (!isCustomer) ...[
                            const SizedBox(width: 14),
                            Expanded(
                              child: _WindowsAttendanceCard(
                                isLoading: _isLoadingAttendance,
                                attendance: _todayAttendance,
                              ),
                            ),
                          ],
                        ],
                      ),
                      if (_role == 'ENGINEER' && _engineerWorkLocked) ...[
                        const SizedBox(height: 18),
                        Card(
                          color: const Color(0xFFFFF4E5),
                          child: Padding(
                            padding: const EdgeInsets.all(18),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.warning_amber_rounded,
                                  color: Color(0xFFB45309),
                                ),
                                const SizedBox(width: 12),
                                Expanded(child: Text(_engineerLockMessage)),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 30),
                      if (selected == null)
                        const Center(child: Text('No workspace available'))
                      else ...[
                        Row(
                          children: [
                            Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                color: selected.color.withValues(alpha: .11),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Icon(
                                selected.icon,
                                color: selected.color,
                                size: 25,
                              ),
                            ),
                            const SizedBox(width: 13),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  selected.title,
                                  style: const TextStyle(
                                    color: Color(0xFF102A43),
                                    fontSize: 21,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                Text(
                                  '${selected.items.length} business tools',
                                  style: const TextStyle(
                                    color: Color(0xFF627D98),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        GridView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                            maxCrossAxisExtent: 310,
                            mainAxisExtent: 126,
                            crossAxisSpacing: 16,
                            mainAxisSpacing: 16,
                          ),
                          itemCount: selected.items.length,
                          itemBuilder: (_, index) {
                            final item = selected.items[index];
                            return _WindowsToolCard(
                              item: item,
                              color: selected.color,
                              onTap: () => _handleItemTap(item),
                            );
                          },
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingRole) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final allItems = _dashboardItems, isCustomer = _role == 'CUSTOMER';
    final isWindows = defaultTargetPlatform == TargetPlatform.windows;
    final items = allItems
        .where((item) => matchesAllSearchTerms(_toolQuery, [item.title, item.route]))
        .toList();
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) _handleDashboardBack();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(isCustomer ? 'ARI Smart RO' : '$_role Dashboard'),
          actions: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                IconButton(
                  tooltip: 'Notifications',
                  onPressed: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const NotificationCenterScreen(),
                      ),
                    );
                    if (mounted) _loadDashboard();
                  },
                  icon: const Icon(Icons.notifications_outlined),
                ),
                if (_notificationUnread > 0)
                  Positioned(
                    right: 5,
                    top: 5,
                    child: Container(
                      constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      decoration: BoxDecoration(
                        color: Colors.redAccent,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        _notificationUnread > 99 ? '99+' : '$_notificationUnread',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            IconButton(onPressed: _logout, icon: const Icon(Icons.logout)),
          ],
        ),
        body: isWindows
            ? _buildWindowsDashboard(items: items, isCustomer: isCustomer)
            : RefreshIndicator(
          onRefresh: _loadDashboard,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              if (_role == 'ENGINEER' && _engineerWorkLocked) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(_engineerLockMessage),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (!isCustomer) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: _isLoadingAttendance
                        ? const Center(child: CircularProgressIndicator())
                        : Text(
                            _todayAttendance == null
                                ? 'Attendance not marked today'
                                : _todayAttendance!.isReviewRejected
                                ? 'Attendance review: REJECTED'
                                : _todayAttendance!.isReviewApproved
                                ? 'Attendance review: APPROVED'
                                : 'Attendance review: PENDING',
                          ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              TextField(
                controller: _toolSearchController,
                textInputAction: TextInputAction.search,
                onChanged: (value) => setState(() => _toolQuery = value),
                decoration: InputDecoration(
                  hintText: 'Search tools, reports, rent, parts, employees...',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: _toolQuery.isEmpty
                      ? null
                      : IconButton(
                          onPressed: () {
                            _toolSearchController.clear();
                            setState(() => _toolQuery = '');
                          },
                          icon: const Icon(Icons.clear),
                        ),
                ),
              ),
              const SizedBox(height: 14),
              if (items.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(22),
                    child: Center(child: Text('No matching dashboard tool found')),
                  ),
                )
              else
              _CommandGrid(
                role: _role,
                groups: _dashboardGroups(items),
                onOpen: _openDashboardGroup,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardGroup {
  const _DashboardGroup({
    required this.title,
    required this.icon,
    required this.color,
    required this.items,
  });
  final String title;
  final IconData icon;
  final Color color;
  final List<DashboardItem> items;
}

class _CommandGrid extends StatelessWidget {
  const _CommandGrid({
    required this.role,
    required this.groups,
    required this.onOpen,
    this.isDesktop = false,
  });
  final String role;
  final List<_DashboardGroup> groups;
  final ValueChanged<_DashboardGroup> onOpen;
  final bool isDesktop;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        role == 'CUSTOMER' ? 'My ARI workspace' : 'Business command center',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      const SizedBox(height: 4),
      Text(
        'All tools organised into ${groups.length} workspaces',
        style: Theme.of(context).textTheme.bodySmall,
      ),
      const SizedBox(height: 14),
      GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: isDesktop
            ? const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 350,
                mainAxisExtent: 112,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
              )
            : const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 1.55,
              ),
        itemCount: groups.length,
        itemBuilder: (_, index) {
          final group = groups[index];
          return Card(
            margin: EdgeInsets.zero,
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => onOpen(group),
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(11),
                      decoration: BoxDecoration(
                        color: group.color.withValues(alpha: .11),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(group.icon, color: group.color, size: 27),
                    ),
                    const SizedBox(width: 11),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            group.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            '${group.items.length} tools',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right_rounded, size: 20),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    ],
  );
}


class _WindowsMetric extends StatelessWidget {
  const _WindowsMetric({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    width: 112,
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .12),
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: Colors.white.withValues(alpha: .16)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 23,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withValues(alpha: .76),
            fontSize: 12,
          ),
        ),
      ],
    ),
  );
}


class _WindowsOverviewCard extends StatelessWidget {
  const _WindowsOverviewCard({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    width: 190,
    padding: const EdgeInsets.all(17),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: const Color(0xFFE3EAF2)),
    ),
    child: Row(
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: color.withValues(alpha: .10),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              value,
              style: const TextStyle(
                color: Color(0xFF102A43),
                fontSize: 20,
                fontWeight: FontWeight.w900,
              ),
            ),
            Text(
              label,
              style: const TextStyle(
                color: Color(0xFF627D98),
                fontSize: 12,
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

class _WindowsAttendanceCard extends StatelessWidget {
  const _WindowsAttendanceCard({
    required this.isLoading,
    required this.attendance,
  });

  final bool isLoading;
  final AttendanceModel? attendance;

  @override
  Widget build(BuildContext context) {
    final text = isLoading
        ? 'Loading attendance...'
        : attendance == null
        ? 'Attendance not marked today'
        : attendance!.isReviewRejected
        ? 'Attendance review: Rejected'
        : attendance!.isReviewApproved
        ? 'Attendance review: Approved'
        : 'Attendance review: Pending';
    return Container(
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE3EAF2)),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: const Color(0xFF059669).withValues(alpha: .10),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.fact_check_outlined,
              color: Color(0xFF059669),
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Today',
                  style: TextStyle(
                    color: Color(0xFF102A43),
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  text,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF627D98),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _WindowsToolCard extends StatelessWidget {
  const _WindowsToolCard({
    required this.item,
    required this.color,
    required this.onTap,
  });

  final DashboardItem item;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    borderRadius: BorderRadius.circular(17),
    child: InkWell(
      borderRadius: BorderRadius.circular(17),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(17),
          border: Border.all(color: const Color(0xFFE3EAF2)),
          boxShadow: const [
            BoxShadow(
              color: Color(0x0C102A43),
              blurRadius: 12,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: color.withValues(alpha: .10),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(item.icon, color: color, size: 25),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                item.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Color(0xFF243B53),
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                ),
              ),
            ),
            const Icon(
              Icons.arrow_forward_rounded,
              color: Color(0xFF9FB3C8),
              size: 19,
            ),
          ],
        ),
      ),
    ),
  );
}
