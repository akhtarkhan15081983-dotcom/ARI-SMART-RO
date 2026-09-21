import 'package:flutter/material.dart';

import '../../services/admin_attendance_review_service.dart';

class OvertimeApprovalAdminScreen extends StatefulWidget {
  const OvertimeApprovalAdminScreen({super.key});

  @override
  State<OvertimeApprovalAdminScreen> createState() =>
      _OvertimeApprovalAdminScreenState();
}

class _OvertimeApprovalAdminScreenState
    extends State<OvertimeApprovalAdminScreen> {
  final _service = AdminAttendanceReviewService();
  bool _loading = true;
  String _status = 'PENDING';
  String? _error;
  List<Map<String, dynamic>> _rows = const [];

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
      final rows = await _service.getOvertimeRequests(status: _status);
      if (mounted) setState(() => _rows = rows);
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _review(Map<String, dynamic> row, String action) async {
    final hoursController = TextEditingController(
      text: (row['requested_hours'] ?? '1').toString(),
    );
    final noteController = TextEditingController();
    final approve = action == 'APPROVE';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(approve ? 'Approve overtime?' : 'Reject overtime?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              (row['employee_name'] ?? '').toString(),
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            Text(
              (row['employee_id'] ?? '').toString() +
                  ' • ' +
                  (row['date'] ?? '').toString(),
            ),
            const SizedBox(height: 12),
            Text('Reason: ' + (row['reason'] ?? '').toString()),
            if (approve) ...[
              const SizedBox(height: 12),
              TextField(
                controller: hoursController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Approved overtime hours',
                  helperText: 'Cannot exceed requested hours',
                ),
              ),
            ],
            const SizedBox(height: 12),
            TextField(
              controller: noteController,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Admin note',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(approve ? 'APPROVE' : 'REJECT'),
          ),
        ],
      ),
    );

    if (confirmed != true) {
      hoursController.dispose();
      noteController.dispose();
      return;
    }

    try {
      final message = await _service.reviewOvertime(
        requestId: (row['id'] as num).toInt(),
        action: action,
        approvedHours: approve
            ? double.tryParse(hoursController.text.trim())
            : null,
        note: noteController.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      hoursController.dispose();
      noteController.dispose();
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Overtime Approvals'),
          actions: [
            IconButton(
              onPressed: _load,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              const Card(
                color: Color(0xFFEAF4FC),
                child: Padding(
                  padding: EdgeInsets.all(14),
                  child: Text(
                    'Only Admin-approved overtime is counted in payroll. Regular duty is automatically capped at the configured 8-hour shift.',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'PENDING', label: Text('Pending')),
                  ButtonSegment(value: 'APPROVED', label: Text('Approved')),
                  ButtonSegment(value: 'COMPLETED', label: Text('Completed')),
                  ButtonSegment(value: 'REJECTED', label: Text('Rejected')),
                ],
                selected: {_status},
                onSelectionChanged: (value) {
                  setState(() => _status = value.first);
                  _load();
                },
              ),
              const SizedBox(height: 16),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error != null)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Text(_error!),
                  ),
                )
              else if (_rows.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(child: Text('No overtime requests here.')),
                )
              else
                ..._rows.map((row) {
                  final status = (row['status'] ?? '').toString().toUpperCase();
                  final pending = status == 'PENDING';
                  return Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            (row['employee_name'] ?? '').toString(),
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          Text(
                            (row['employee_id'] ?? '').toString() +
                                ' • ' +
                                (row['designation'] ?? '').toString() +
                                ' • ' +
                                (row['date'] ?? '').toString(),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'Requested: ' +
                                (row['requested_hours'] ?? '0').toString() +
                                'h • Approved: ' +
                                (row['approved_hours'] ?? '0').toString() +
                                'h',
                          ),
                          Text(
                            'Regular worked: ' +
                                (row['regular_hours'] ?? '0').toString() +
                                'h • OT worked: ' +
                                (row['overtime_hours'] ?? '0').toString() +
                                'h',
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Reason: ' + (row['reason'] ?? '').toString(),
                          ),
                          if ((row['review_note'] ?? '').toString().isNotEmpty)
                            Text(
                              'Admin note: ' +
                                  (row['review_note'] ?? '').toString(),
                            ),
                          if (pending) ...[
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: () => _review(row, 'REJECT'),
                                    icon: const Icon(Icons.close_rounded),
                                    label: const Text('REJECT'),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: () => _review(row, 'APPROVE'),
                                    icon: const Icon(Icons.check_rounded),
                                    label: const Text('APPROVE'),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  );
                }),
            ],
          ),
        ),
      );
}
