import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/complaint_model.dart';
import '../../services/api_service.dart';
import '../../services/complaint_service.dart';
import '../jobs/secure_field_work_screen.dart';

class ComplaintDetailsScreen extends StatefulWidget {
  const ComplaintDetailsScreen({super.key, required this.complaintId});

  final int complaintId;

  @override
  State<ComplaintDetailsScreen> createState() => _ComplaintDetailsScreenState();
}

class _ComplaintDetailsScreenState extends State<ComplaintDetailsScreen> {
  final ComplaintService _complaintService = ComplaintService();
  late Future<ComplaintModel> _complaintFuture;
  bool _isSaving = false;
  String _role = '';

  @override
  void initState() {
    super.initState();
    _complaintFuture = _complaintService.getComplaintDetail(widget.complaintId);
    _loadRole();
  }

  Future<void> _loadRole() async {
    final role = await ApiService.getRole();
    if (!mounted) return;
    setState(() => _role = (role ?? '').trim().toUpperCase());
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() {
      _complaintFuture = _complaintService.getComplaintDetail(widget.complaintId);
    });
    try {
      await _complaintFuture;
    } catch (_) {}
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openSecureWork(ComplaintModel complaint) async {
    if (_isSaving) return;
    if (_role != 'ENGINEER') {
      _showMessage('Secure field work can be performed only by the assigned engineer.');
      return;
    }
    if (complaint.job == null) {
      _showMessage(
        'Secure work job is being prepared. Refresh this complaint and try again.',
      );
      return;
    }

    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => SecureFieldWorkScreen(jobId: complaint.job!),
      ),
    );
    if (mounted) await _refresh();
  }

  Future<void> _closeComplaint() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Close Complaint'),
        content: const Text(
          'Close this complaint after the engineer has completed the secure work workflow?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Close'),
          ),
        ],
      ),
    );
    if (confirmed != true || _isSaving) return;

    setState(() => _isSaving = true);
    try {
      await _complaintService.closeComplaint(widget.complaintId);
      _showMessage('Complaint closed successfully.');
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      _showMessage(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _callPhone(String phone, String person) async {
    if (phone.trim().isEmpty) {
      _showMessage('$person phone number is not available.');
      return;
    }
    final uri = Uri(scheme: 'tel', path: phone);
    if (!await launchUrl(uri)) {
      _showMessage('Unable to open the phone app.');
    }
  }

  Future<void> _navigateToCustomer(ComplaintModel complaint) async {
    if (complaint.latitude == null || complaint.longitude == null) {
      _showMessage('Customer location is not available.');
      return;
    }
    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1'
      '&destination=${complaint.latitude},${complaint.longitude}'
      '&travelmode=driving',
    );
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _showMessage('Unable to open Maps.');
    }
  }

  Widget _nextStep(ComplaintModel complaint) {
    final status = complaint.status.trim().toUpperCase();

    if (status == 'NEW') {
      return const _InfoCard(
        icon: Icons.hourglass_empty,
        title: 'Waiting for Assignment',
        message: 'Assign an engineer before field work can begin.',
      );
    }

    if (status == 'ASSIGNED' || status == 'IN_PROGRESS') {
      if (_role == 'ENGINEER') {
        if (complaint.job == null) {
          return _InfoCard(
            icon: Icons.sync,
            title: 'Preparing Secure Work',
            message:
                'The secure job is not linked yet. Refresh after the server finishes preparing it.',
            action: OutlinedButton.icon(
              onPressed: _refresh,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh'),
            ),
          );
        }
        return _InfoCard(
          icon: Icons.verified_user,
          title: status == 'ASSIGNED' ? 'Secure Field Workflow' : 'Work In Progress',
          message:
              'Continue through Accept Job, journey, arrival, before photo, work, parts, after photo, OTP and customer signature.',
          action: FilledButton.icon(
            onPressed: _isSaving ? null : () => _openSecureWork(complaint),
            icon: const Icon(Icons.play_arrow),
            label: Text(status == 'ASSIGNED' ? 'Open Secure Work' : 'Continue Secure Work'),
          ),
        );
      }

      return const _InfoCard(
        icon: Icons.engineering,
        title: 'Engineer Action Required',
        message:
            'The assigned engineer must complete this complaint through the secure field-work workflow.',
      );
    }

    if (status == 'RESOLVED') {
      if (_role == 'ADMIN' || _role == 'MANAGER' || _role == 'OFFICE') {
        return _InfoCard(
          icon: Icons.task_alt,
          title: 'Work Completed',
          message: 'Secure work is complete. Confirm the result and close the complaint.',
          action: FilledButton.icon(
            onPressed: _isSaving ? null : _closeComplaint,
            icon: const Icon(Icons.lock_outline),
            label: const Text('Close Complaint'),
          ),
        );
      }
      return const _InfoCard(
        icon: Icons.task_alt,
        title: 'Complaint Resolved',
        message: 'Secure field work has been completed.',
      );
    }

    if (status == 'CLOSED') {
      return const _InfoCard(
        icon: Icons.check_circle,
        title: 'Complaint Closed',
        message: 'This complaint has been completed and closed.',
      );
    }

    if (status == 'CANCELLED') {
      return const _InfoCard(
        icon: Icons.cancel,
        title: 'Complaint Cancelled',
        message: 'This complaint has been cancelled.',
      );
    }

    return _InfoCard(
      icon: Icons.help_outline,
      title: 'Unknown Status',
      message: 'Current status: $status',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Complaint Details'),
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isSaving ? null : _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<ComplaintModel>(
        future: _complaintFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 56),
                    const SizedBox(height: 12),
                    Text(
                      snapshot.error?.toString().replaceFirst('Exception: ', '') ??
                          'Unable to load complaint.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _refresh,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }

          final complaint = snapshot.data!;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                _Header(complaint: complaint),
                const SizedBox(height: 12),
                _Section(
                  title: 'Customer Details',
                  child: Column(
                    children: [
                      _Row('Name', complaint.customerName),
                      _Row('Customer ID', complaint.customerIdDisplay),
                      _Row('Phone', complaint.customerPhone),
                      _Row('Current Card', complaint.currentCardNumber),
                      if (complaint.oldCardNumber.isNotEmpty)
                        _Row('Old Card', complaint.oldCardNumber),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _callPhone(complaint.customerPhone, 'Customer'),
                              icon: const Icon(Icons.call),
                              label: const Text('Call'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _navigateToCustomer(complaint),
                              icon: const Icon(Icons.navigation),
                              label: const Text('Navigate'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _Section(
                  title: 'Complaint',
                  child: Column(
                    children: [
                      _Row('Type', complaint.displayComplaintType),
                      _Row('Priority', complaint.displayPriority),
                      _Row('Status', complaint.displayStatus),
                      _Row('Description', complaint.description),
                      _Row('Complaint Date', complaint.complaintDate ?? '-'),
                      if (complaint.scheduledDate?.isNotEmpty ?? false)
                        _Row('Scheduled Date', complaint.scheduledDate!),
                      if (complaint.job != null)
                        _Row('Secure Job', '#${complaint.job}'),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _Section(
                  title: 'Engineer',
                  child: Column(
                    children: [
                      _Row('Name', complaint.displayEngineer),
                      _Row('Engineer ID', complaint.engineerIdDisplay),
                      if (complaint.engineerPhone.isNotEmpty) ...[
                        _Row('Phone', complaint.engineerPhone),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: () => _callPhone(complaint.engineerPhone, 'Engineer'),
                            icon: const Icon(Icons.call),
                            label: const Text('Call Engineer'),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (complaint.resolution.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _Section(
                    title: 'Resolution',
                    child: Column(
                      children: [
                        _Row('Resolution', complaint.resolution),
                        if (complaint.resolvedDate?.isNotEmpty ?? false)
                          _Row('Resolved Date', complaint.resolvedDate!),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                _nextStep(complaint),
                const SizedBox(height: 28),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.complaint});
  final ComplaintModel complaint;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              complaint.complaintId,
              style: Theme.of(context)
                  .textTheme
                  .headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                Chip(label: Text(complaint.displayStatus)),
                Chip(label: Text(complaint.displayPriority)),
              ],
            ),
            const SizedBox(height: 6),
            Text(complaint.displayComplaintType),
            Text('Engineer: ${complaint.displayEngineer}'),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);
  final String label;
  final Object? value;

  @override
  Widget build(BuildContext context) {
    final text = value == null || value.toString().trim().isEmpty
        ? '-'
        : value.toString();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 115,
            child: Text(
              label,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ),
          Expanded(
            child: Text(text, style: const TextStyle(fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: 30),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(message),
                    ],
                  ),
                ),
              ],
            ),
            if (action != null) ...[
              const SizedBox(height: 14),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
