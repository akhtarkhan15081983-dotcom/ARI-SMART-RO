import 'package:flutter/material.dart';

import '../../services/admin_face_security_service.dart';

class FaceSecurityAdminScreen extends StatefulWidget {
  const FaceSecurityAdminScreen({super.key});

  @override
  State<FaceSecurityAdminScreen> createState() =>
      _FaceSecurityAdminScreenState();
}

class _FaceSecurityAdminScreenState extends State<FaceSecurityAdminScreen> {
  final _service = AdminFaceSecurityService();
  List<Map<String, dynamic>> _engineers = [];
  bool _loading = true;
  String? _error;
  int? _busyId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final engineers = await _service.getEngineers();
      if (!mounted) return;
      setState(() {
        _engineers = engineers;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Unable to load engineers.';
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

    setState(() => _busyId = id);
    try {
      final message = await _service.setReEnrollment(
        employeeId: id,
        allow: allow,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Face & Device Security')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? ListView(
                children: [
                  const SizedBox(height: 160),
                  Center(child: Text(_error!)),
                  const SizedBox(height: 12),
                  Center(
                    child: FilledButton(
                      onPressed: _load,
                      child: const Text('Retry'),
                    ),
                  ),
                ],
              )
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: _engineers.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final e = _engineers[index];
                  final enrolled = e['face_enrolled'] == true;
                  final verified = e['face_enrollment_verified'] == true;
                  final allowed = e['face_enrollment_allowed'] == true;
                  final deviceBound = e['attendance_device_bound'] == true;
                  final id = e['id'] as int;
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
                          Text(
                            '${e['employee_id'] ?? ''}  •  ${e['phone'] ?? ''}',
                          ),
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
                                    onPressed: _busyId == id
                                        ? null
                                        : () => _changePermission(e, false),
                                    icon: const Icon(Icons.lock_outline),
                                    label: Text(
                                      _busyId == id
                                          ? 'Please wait...'
                                          : 'Cancel Re-enrollment Permission',
                                    ),
                                  )
                                : FilledButton.icon(
                                    onPressed: _busyId == id
                                        ? null
                                        : () => _changePermission(e, true),
                                    icon: const Icon(
                                      Icons.admin_panel_settings_outlined,
                                    ),
                                    label: Text(
                                      _busyId == id
                                          ? 'Please wait...'
                                          : 'Allow One Re-enrollment',
                                    ),
                                  ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
