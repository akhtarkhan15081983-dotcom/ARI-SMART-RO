import 'package:flutter/material.dart';
import '../profile/profile_screen.dart';
import '../../models/attendance_model.dart';
import '../../services/api_service.dart';
import '../../services/attendance_service.dart';
import '../../services/live_location_service.dart';
import '../attendance/attendance_screen.dart';
import '../bag/my_bag_screen.dart';
import '../engineer/map_screen.dart';
import '../jobs/my_jobs_screen.dart';
import '../qr/qr_scanner_screen.dart';
import 'dashboard_card.dart';
import 'dashboard_items.dart';
import '../login/login_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final AttendanceService _attendanceService = AttendanceService();
  final LiveLocationService _liveLocationService = LiveLocationService();

  static const List<DashboardItem> _customerItems = [
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
      title: 'Profile',
      icon: Icons.person,
      route: 'profile',
    ),
  ];

  AttendanceModel? _todayAttendance;
  String _role = 'CUSTOMER';
  bool _isLoadingAttendance = true;
  bool _isLoadingRole = true;

  @override
  void initState() {
    super.initState();
    _liveLocationService.startTracking();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    await Future.wait([
      _loadAttendance(),
      _loadRole(),
    ]);
  }

  Future<void> _loadAttendance() async {
    try {
      final attendance = await _attendanceService.todayAttendance();
      if (!mounted) return;
      setState(() {
        _todayAttendance = attendance;
        _isLoadingAttendance = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingAttendance = false);
    }
  }

  Future<void> _loadRole() async {
    try {
      final storedRole = await ApiService.getRole();
      if (!mounted) return;
      setState(() {
        _role = _normaliseRole(storedRole?.toString());
        _isLoadingRole = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingRole = false);
    }
  }

  String _normaliseRole(String? role) {
    final value = role?.trim().toUpperCase().replaceAll('ROLE_', '');
    switch (value) {
      case 'ADMIN':
      case 'MANAGER':
      case 'OFFICE':
      case 'ENGINEER':
      case 'CUSTOMER':
        return value!;
      default:
        return 'CUSTOMER';
    }
  }

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
  Future<void> _logout() async {

    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Logout"),
        content: const Text(
          "Are you sure you want to logout?",
        ),
        actions: [

          TextButton(
            onPressed: () {
              Navigator.pop(context, false);
            },
            child: const Text("Cancel"),
          ),

          ElevatedButton(
            onPressed: () {
              Navigator.pop(context, true);
            },
            child: const Text("Logout"),
          ),

        ],
      ),
    );

    if (confirm != true) return;

    await ApiService.logout();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (_) => const LoginScreen(),
      ),
      (route) => false,
    );
  }

  void _handleItemTap(DashboardItem item) {
    switch (item.route) {
      case 'attendance':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const AttendanceScreen()),
        );
        return;
      case 'jobs':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const MyJobsScreen()),
        );
        return;
      case 'bag':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => MyBagScreen()),
        );
        return;
      case 'qr':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const QRScanScreen(jobId: 0)),
        );
        return;
      case 'map':
      case 'engineer_map':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const EngineerMapScreen()),
        );
        return;
      case 'profile':
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => const ProfileScreen(),
          ),
        );
        return;

      default:
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${item.title} module coming soon...')),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingRole) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final items = _dashboardItems;

    return Scaffold(
    appBar: AppBar(
      title: const Text("ARI SMART RO"),
      centerTitle: true,

        actions: [

          IconButton(

            icon: const Icon(Icons.logout),

            onPressed: _logout,

          ),

        ],

      ),
      body: Column(
        children: [
          _AttendanceCard(
            attendance: _todayAttendance,
            isLoading: _isLoadingAttendance,
          ),
          Expanded(
            child: GridView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                childAspectRatio: 1.05,
                crossAxisSpacing: 15,
                mainAxisSpacing: 15,
              ),
              itemBuilder: (context, index) {
                final item = items[index];
                return DashboardCard(
                  title: item.title,
                  icon: item.icon,
                  onTap: () => _handleItemTap(item),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _liveLocationService.stopTracking();
    super.dispose();
  }
}

class _AttendanceCard extends StatelessWidget {
  const _AttendanceCard({
    required this.attendance,
    required this.isLoading,
  });

  final AttendanceModel? attendance;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(12),
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Today's Attendance",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            if (isLoading)
              const Center(child: CircularProgressIndicator())
            else if (attendance == null)
              const Text('No Attendance Today')
            else ...[
              Text('Status : ${attendance!.status}'),
              const SizedBox(height: 5),
              Text('Check In : ${attendance!.checkIn ?? '-'}'),
              Text('Check Out : ${attendance!.checkOut ?? '-'}'),
              Text('Working Hours : ${attendance!.workingHours}'),
            ],
          ],
        ),
      ),
    );
  }
}
