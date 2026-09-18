import 'package:flutter/material.dart';

import '../../services/admin_face_security_service.dart';
import '../../utils/search_utils.dart';

class FaceSecurityAdminScreen extends StatefulWidget {
  const FaceSecurityAdminScreen({super.key});

  @override
  State<FaceSecurityAdminScreen> createState() =>
      _FaceSecurityAdminScreenState();
}

class _FaceSecurityAdminScreenState extends State<FaceSecurityAdminScreen> {
  final _service = AdminFaceSecurityService();
  List<Map<String, dynamic>> _engineers = [];
  List<Map<String, dynamic>> _attendanceEmployees = [];
  bool _loading = true;
  String? _error;
  int? _busyId;
  String? _busyAction;
  final _searchController = TextEditingController();
  String _query = '';
  String _attendanceFilter = 'ALL';
  String _reenrollFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _service.getEngineers(),
        _service.getAttendanceDeviceOverrides(),
      ]);
      if (!mounted) return;
      setState(() {
        _engineers = results[0];
        _attendanceEmployees = results[1];
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Unable to load face/device security controls.';
      });
    }
  }

  Future<void> _changePermission(
    Map<String, dynamic> engineer,
    bool allow,
  ) async {
    final id = engineer['id'] as int;
    final name = engineer['name']?.toString() ?? 'Engineer';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(allow ? 'Allow Re-enrollment?' : 'Cancel Re-enrollment?'),
        content: Text(
          allow
              ? '$name will get one opportunity to replace the registered face and attendance device. The permission locks automatically after successful enrollment.'
              : '$name will no longer be allowed to re-enroll face/device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Back'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(allow ? 'Allow' : 'Cancel Permission'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() {
      _busyId = id;
      _busyAction = 'reenroll';
    });
    try {
      final message = await _service.setReEnrollment(
        employeeId: id,
        allow: allow,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _busyId = null;
          _busyAction = null;
        });
      }
    }
  }

  Future<void> _changeEmergencyPermission(
    Map<String, dynamic> employee,
    bool allow,
  ) async {
    final id = employee['id'] as int;
    final name = employee['name']?.toString() ?? 'Employee';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(allow ? 'Allow another phone today?' : 'Revoke permission?'),
        content: Text(
          allow
              ? '$name will be allowed to mark attendance today from another phone if the registered phone is not working. GPS and live selfie will still be required. The registered phone will not be changed.'
              : '$name will again be restricted to the registered attendance phone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Back'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(allow ? 'Allow Today' : 'Revoke'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() {
      _busyId = id;
      _busyAction = 'override';
    });
    try {
      final message = await _service.setEmergencyAttendanceDevicePermission(
        employeeId: id,
        allow: allow,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _busyId = null;
          _busyAction = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Face & Device Security'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Attendance Access'),
              Tab(text: 'Re-enrollment'),
            ],
          ),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(_error!),
                    const SizedBox(height: 12),
                    FilledButton(onPressed: _load, child: const Text('Retry')),
                  ],
                ),
              )
            : TabBarView(
                children: [
                  _buildAttendanceAccessTab(),
                  _buildReEnrollmentTab(),
                ],
              ),
      ),
    );
  }

  Widget _buildAttendanceAccessTab() {
    final filtered = _attendanceEmployees.where((employee) {
      final allowed = employee['emergency_device_allowed_today'] == true;
      final bound = employee['attendance_device_bound'] == true;
      if (_attendanceFilter == 'ALLOWED' && !allowed) return false;
      if (_attendanceFilter == 'BOUND' && !bound) return false;
      if (_attendanceFilter == 'UNBOUND' && bound) return false;
      return matchesAllSearchTerms(_query, [
        (employee['name'] ?? '').toString(),
        (employee['employee_id'] ?? '').toString(),
        (employee['designation'] ?? '').toString(),
        (employee['phone'] ?? '').toString(),
      ]);
    }).toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Emergency Attendance Device Permission',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Use this only when an employee\'s registered phone is not working. Permission is valid for today only, keeps GPS + live selfie mandatory, and does not replace the registered phone.',
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _searchController,
            textInputAction: TextInputAction.search,
            onChanged: (value) => setState(() => _query = value),
            decoration: InputDecoration(
              hintText: 'Search employee, ID, phone or designation...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _query.isEmpty ? null : IconButton(
                onPressed: () { _searchController.clear(); setState(() => _query = ''); },
                icon: const Icon(Icons.clear),
              ),
            ),
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            initialValue: _attendanceFilter,
            decoration: const InputDecoration(labelText: 'Attendance-device filter'),
            items: const [
              DropdownMenuItem(value: 'ALL', child: Text('All employees')),
              DropdownMenuItem(value: 'ALLOWED', child: Text('Other phone allowed today')),
              DropdownMenuItem(value: 'BOUND', child: Text('Registered device bound')),
              DropdownMenuItem(value: 'UNBOUND', child: Text('Device not bound')),
            ],
            onChanged: (v) => setState(() => _attendanceFilter = v ?? 'ALL'),
          ),
          const SizedBox(height: 8),
          Align(alignment: Alignment.centerLeft, child: Text('${filtered.length} of ${_attendanceEmployees.length} employees')),
          const SizedBox(height: 12),
          ...filtered.map((employee) {
            final id = employee['id'] as int;
            final allowed = employee['emergency_device_allowed_today'] == true;
            final deviceBound = employee['attendance_device_bound'] == true;
            final busy = _busyId == id && _busyAction == 'override';
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        employee['name']?.toString() ?? 'Employee',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${employee['employee_id'] ?? ''}  •  ${employee['designation'] ?? ''}  •  ${employee['phone'] ?? ''}',
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Registered device: ${deviceBound ? 'Bound' : 'Not bound'}',
                      ),
                      const SizedBox(height: 5),
                      Text(
                        'Other phone today: ${allowed ? 'ADMIN ALLOWED' : 'NOT ALLOWED'}',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: allowed
                              ? Colors.orange.shade800
                              : Colors.green.shade700,
                        ),
                      ),
                      const SizedBox(height: 14),
                      SizedBox(
                        width: double.infinity,
                        child: allowed
                            ? OutlinedButton.icon(
                                onPressed: busy
                                    ? null
                                    : () => _changeEmergencyPermission(
                                          employee,
                                          false,
                                        ),
                                icon: const Icon(Icons.lock_outline),
                                label: Text(busy ? 'Please wait...' : 'Revoke Today'),
                              )
                            : FilledButton.icon(
                                onPressed: busy || !deviceBound
                                    ? null
                                    : () => _changeEmergencyPermission(
                                          employee,
                                          true,
                                        ),
                                icon: const Icon(Icons.phonelink_lock),
                                label: Text(
                                  busy
                                      ? 'Please wait...'
                                      : 'Allow Other Phone Today',
                                ),
                              ),
                      ),
                      if (!deviceBound) ...[
                        const SizedBox(height: 8),
                        Text(
                          'First complete normal face/device enrollment.',
                          style: TextStyle(
                            color: Colors.orange.shade800,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildReEnrollmentTab() {
    final filtered = _engineers.where((e) {
      final allowed = e['face_enrollment_allowed'] == true;
      final enrolled = e['face_enrolled'] == true;
      if (_reenrollFilter == 'ALLOWED' && !allowed) return false;
      if (_reenrollFilter == 'NOT_ENROLLED' && enrolled) return false;
      return matchesAllSearchTerms(_query, [
        (e['name'] ?? '').toString(),
        (e['employee_id'] ?? '').toString(),
        (e['phone'] ?? '').toString(),
      ]);
    }).toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: filtered.length + 2,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          if (index == 0) {
            return TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onChanged: (value) => setState(() => _query = value),
              decoration: InputDecoration(
                hintText: 'Search engineer, ID or phone...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _query.isEmpty ? null : IconButton(
                  onPressed: () { _searchController.clear(); setState(() => _query = ''); },
                  icon: const Icon(Icons.clear),
                ),
              ),
            );
          }
          if (index == 1) {
            return DropdownButtonFormField<String>(
              initialValue: _reenrollFilter,
              decoration: const InputDecoration(labelText: 'Face enrollment filter'),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('All engineers')),
                DropdownMenuItem(value: 'ALLOWED', child: Text('Re-enrollment allowed')),
                DropdownMenuItem(value: 'NOT_ENROLLED', child: Text('Not enrolled')),
              ],
              onChanged: (v) => setState(() => _reenrollFilter = v ?? 'ALL'),
            );
          }
          final e = filtered[index - 2];
          final enrolled = e['face_enrolled'] == true;
          final verified = e['face_enrollment_verified'] == true;
          final allowed = e['face_enrollment_allowed'] == true;
          final deviceBound = e['attendance_device_bound'] == true;
          final id = e['id'] as int;
          final busy = _busyId == id && _busyAction == 'reenroll';
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    e['name']?.toString() ?? 'Engineer',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text('${e['employee_id'] ?? ''}  •  ${e['phone'] ?? ''}'),
                  const Divider(height: 24),
                  Text(
                    'Face: ${!enrolled
                        ? 'Not enrolled'
                        : verified
                        ? 'Verified'
                        : 'Enrolled - verification pending'}',
                  ),
                  const SizedBox(height: 5),
                  Text(
                    'Attendance device: ${deviceBound ? 'Bound' : 'Not bound'}',
                  ),
                  const SizedBox(height: 5),
                  Text(
                    'Re-enrollment: ${allowed ? 'ADMIN ALLOWED' : 'LOCKED'}',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: allowed
                          ? Colors.orange.shade800
                          : Colors.green.shade700,
                    ),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: allowed
                        ? OutlinedButton.icon(
                            onPressed: busy
                                ? null
                                : () => _changePermission(e, false),
                            icon: const Icon(Icons.lock_outline),
                            label: Text(
                              busy
                                  ? 'Please wait...'
                                  : 'Cancel Re-enrollment Permission',
                            ),
                          )
                        : FilledButton.icon(
                            onPressed: busy
                                ? null
                                : () => _changePermission(e, true),
                            icon: const Icon(
                              Icons.admin_panel_settings_outlined,
                            ),
                            label: Text(
                              busy ? 'Please wait...' : 'Allow One Re-enrollment',
                            ),
                          ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
