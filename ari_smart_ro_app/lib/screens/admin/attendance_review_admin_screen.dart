import 'package:flutter/material.dart';

import '../../services/admin_attendance_review_service.dart';

class AttendanceReviewAdminScreen extends StatefulWidget {
  const AttendanceReviewAdminScreen({super.key});

  @override
  State<AttendanceReviewAdminScreen> createState() => _AttendanceReviewAdminScreenState();
}

class _AttendanceReviewAdminScreenState extends State<AttendanceReviewAdminScreen> {
  final _service = AdminAttendanceReviewService();
  String _status = 'PENDING';
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _reviews = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final reviews = await _service.getReviews(status: _status);
      if (!mounted) return;
      setState(() => _reviews = reviews);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _review(Map<String, dynamic> item, String action) async {
    final noteController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(action == 'approve' ? 'Approve selfie review?' : 'Reject selfie review?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Employee: ${item['employee_name'] ?? ''}'),
            const SizedBox(height: 12),
            TextField(
              controller: noteController,
              maxLength: 255,
              decoration: const InputDecoration(labelText: 'Admin note (optional)', border: OutlineInputBorder()),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(action == 'approve' ? 'Approve' : 'Reject')),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      final message = await _service.updateReview(
        attendanceId: item['id'] as int,
        action: action,
        note: noteController.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))));
    } finally {
      noteController.dispose();
    }
  }

  Widget _photo(String? url, String label) {
    return Expanded(
      child: Column(
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          AspectRatio(
            aspectRatio: 1,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: url == null || url.isEmpty
                  ? const ColoredBox(color: Color(0xFFEAEAEA), child: Center(child: Icon(Icons.person_off_outlined, size: 48)))
                  : Image.network(
                      url,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const ColoredBox(color: Color(0xFFEAEAEA), child: Center(child: Icon(Icons.broken_image_outlined, size: 48))),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Attendance Selfie Review')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              color: const Color(0xFFFFF4E5),
              child: const Padding(
                padding: EdgeInsets.all(14),
                child: Text(
                  'Human review only: compare the enrollment photo and attendance selfie yourself. The app does not perform biometric identity matching.',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'PENDING', label: Text('Pending')),
                ButtonSegment(value: 'APPROVED', label: Text('Approved')),
                ButtonSegment(value: 'REJECTED', label: Text('Rejected')),
              ],
              selected: {_status},
              onSelectionChanged: (value) { _status = value.first; _load(); },
            ),
            const SizedBox(height: 16),
            if (_loading) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
            else if (_error != null) Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(children: [Text(_error!), const SizedBox(height: 12), FilledButton(onPressed: _load, child: const Text('Retry'))])))
            else if (_reviews.isEmpty) const Padding(padding: EdgeInsets.all(40), child: Center(child: Text('No attendance selfie reviews in this section.')))
            else ..._reviews.map((item) => _ReviewCard(item: item, photoBuilder: _photo, onApprove: () => _review(item, 'approve'), onReject: () => _review(item, 'reject'))),
          ],
        ),
      ),
    );
  }
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({required this.item, required this.photoBuilder, required this.onApprove, required this.onReject});

  final Map<String, dynamic> item;
  final Widget Function(String?, String) photoBuilder;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  @override
  Widget build(BuildContext context) {
    final pending = item['identity_review_status'] == 'PENDING';
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(item['employee_name']?.toString() ?? 'Employee', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text('${item['employee_id'] ?? ''}  •  ${item['date'] ?? ''}'),
            const SizedBox(height: 4),
            Text('Status: ${item['identity_review_status'] ?? 'PENDING'}', style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              photoBuilder(item['enrollment_photo']?.toString(), 'Enrollment'),
              const SizedBox(width: 12),
              photoBuilder(item['attendance_selfie']?.toString(), 'Attendance selfie'),
            ]),
            const SizedBox(height: 12),
            Text(item['distance_note']?.toString() ?? ''),
            if ((item['identity_review_note']?.toString() ?? '').isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Review note: ${item['identity_review_note']}'),
            ],
            if (pending) ...[
              const SizedBox(height: 14),
              Row(children: [
                Expanded(child: OutlinedButton.icon(onPressed: onReject, icon: const Icon(Icons.close), label: const Text('Reject'))),
                const SizedBox(width: 10),
                Expanded(child: FilledButton.icon(onPressed: onApprove, icon: const Icon(Icons.check), label: const Text('Approve'))),
              ]),
            ],
          ],
        ),
      ),
    );
  }
}
