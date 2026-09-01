import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/complaint_model.dart';
import '../../services/complaint_service.dart';

class ComplaintDetailsScreen extends StatefulWidget {
  const ComplaintDetailsScreen({super.key, required this.complaintId});

  final int complaintId;

  @override
  State<ComplaintDetailsScreen> createState() => _ComplaintDetailsScreenState();
}

class _ComplaintDetailsScreenState extends State<ComplaintDetailsScreen> {
  final ComplaintService _complaintService = ComplaintService();

  final TextEditingController _resolutionController = TextEditingController();

  final TextEditingController _remarksController = TextEditingController();

  late Future<ComplaintModel> _complaintFuture;

  bool _isSaving = false;

  @override
  void initState() {
    super.initState();

    _complaintFuture = _complaintService.getComplaintDetail(widget.complaintId);
  }

  @override
  void dispose() {
    _resolutionController.dispose();
    _remarksController.dispose();

    super.dispose();
  }

  // ============================================================
  // REFRESH
  // ============================================================

  Future<void> _refresh() async {
    if (!mounted) return;

    setState(() {
      _complaintFuture = _complaintService.getComplaintDetail(
        widget.complaintId,
      );
    });

    try {
      await _complaintFuture;
    } catch (_) {
      // FutureBuilder displays the error.
    }
  }

  // ============================================================
  // MESSAGE
  // ============================================================

  void _showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  // ============================================================
  // RUN ACTION
  // ============================================================

  Future<void> _runAction(Future<void> Function() action) async {
    if (_isSaving) return;

    setState(() {
      _isSaving = true;
    });

    try {
      await action();
    } catch (e) {
      _showMessage(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  // ============================================================
  // START COMPLAINT
  // ============================================================

  Future<void> _startComplaint() async {
    await _runAction(() async {
      await _complaintService.startComplaint(widget.complaintId);

      _showMessage('Complaint work started.');

      await _refresh();
    });
  }

  // ============================================================
  // RESOLVE COMPLAINT
  // ============================================================

  Future<void> _resolveComplaint() async {
    final resolution = _resolutionController.text.trim();

    if (resolution.isEmpty) {
      _showMessage('Please enter resolution details.');
      return;
    }

    final remarks = _remarksController.text.trim();

    await _runAction(() async {
      await _complaintService.resolveComplaint(
        widget.complaintId,
        resolution: resolution,
        engineerRemarks: remarks.isEmpty ? null : remarks,
      );

      _showMessage('Complaint resolved.');

      await _refresh();
    });
  }

  // ============================================================
  // CLOSE COMPLAINT
  // ============================================================

  Future<void> _closeComplaint() async {
    final confirmed = await _showConfirmDialog(
      title: 'Close Complaint',
      message: 'Are you sure you want to close this complaint?',
      confirmText: 'Close',
    );

    if (!confirmed) return;

    await _runAction(() async {
      await _complaintService.closeComplaint(widget.complaintId);

      if (!mounted) return;

      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) {
          return AlertDialog(
            icon: const Icon(Icons.check_circle, color: Colors.green, size: 48),
            title: const Text('Complaint Closed'),
            content: const Text('Complaint has been closed successfully.'),
            actions: [
              FilledButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop();
                },
                child: const Text('Back to Complaints'),
              ),
            ],
          );
        },
      );

      if (mounted) {
        Navigator.of(context).pop(true);
      }
    });
  }

  // ============================================================
  // CONFIRM DIALOG
  // ============================================================

  Future<bool> _showConfirmDialog({
    required String title,
    required String message,
    required String confirmText,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: Text(confirmText),
            ),
          ],
        );
      },
    );

    return result == true;
  }

  // ============================================================
  // CALL CUSTOMER
  // ============================================================

  Future<void> _callCustomer(String phone) async {
    if (phone.trim().isEmpty) {
      _showMessage('Customer phone number is not available.');
      return;
    }

    final uri = Uri(scheme: 'tel', path: phone);

    if (!await launchUrl(uri)) {
      _showMessage('Unable to open the phone app.');
    }
  }

  // ============================================================
  // NAVIGATE CUSTOMER
  // ============================================================

  Future<void> _navigateToCustomer(ComplaintModel complaint) async {
    final latitude = complaint.latitude;

    final longitude = complaint.longitude;

    if (latitude == null || longitude == null) {
      _showMessage('Customer location is not available.');
      return;
    }

    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1'
      '&destination=$latitude,$longitude'
      '&travelmode=driving',
    );

    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _showMessage('Unable to open Maps.');
    }
  }

  // ============================================================
  // BUILD
  // ============================================================

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
            return _ErrorView(
              onRetry: _refresh,
              message:
                  snapshot.error?.toString().replaceFirst('Exception: ', '') ??
                  'Unable to load complaint.',
            );
          }

          final complaint = snapshot.data!;

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _ComplaintHeader(complaint: complaint),

                const SizedBox(height: 12),

                _SectionCard(
                  title: 'Customer Details',
                  child: Column(
                    children: [
                      _InfoRow('Name', complaint.customerName),
                      _InfoRow('Customer ID', complaint.customerIdDisplay),
                      _InfoRow('Phone', complaint.customerPhone),
                      _InfoRow('Current Card', complaint.currentCardNumber),
                      if (complaint.oldCardNumber.isNotEmpty)
                        _InfoRow('Old Card', complaint.oldCardNumber),

                      const SizedBox(height: 12),

                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _isSaving
                                  ? null
                                  : () =>
                                        _callCustomer(complaint.customerPhone),
                              icon: const Icon(Icons.call),
                              label: const Text('Call'),
                            ),
                          ),

                          const SizedBox(width: 12),

                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _isSaving
                                  ? null
                                  : () => _navigateToCustomer(complaint),
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

                _SectionCard(
                  title: 'Complaint',
                  child: Column(
                    children: [
                      _InfoRow('Type', complaint.displayComplaintType),
                      _InfoRow('Priority', complaint.displayPriority),
                      _InfoRow('Status', complaint.displayStatus),
                      _InfoRow('Description', complaint.description),
                      _InfoRow(
                        'Complaint Date',
                        complaint.complaintDate ?? '-',
                      ),
                      if (complaint.scheduledDate?.isNotEmpty ?? false)
                        _InfoRow('Scheduled Date', complaint.scheduledDate!),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                _StatusTimeline(complaint: complaint),

                const SizedBox(height: 12),

                _SectionCard(
                  title: 'Engineer',
                  child: Column(
                    children: [
                      _InfoRow('Name', complaint.displayEngineer),
                      _InfoRow('Engineer ID', complaint.engineerIdDisplay),
                      _InfoRow(
                        'Remarks',
                        complaint.engineerRemarks.isEmpty
                            ? '-'
                            : complaint.engineerRemarks,
                      ),
                    ],
                  ),
                ),

                if (complaint.resolution.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _SectionCard(
                    title: 'Resolution',
                    child: Column(
                      children: [
                        _InfoRow('Resolution', complaint.resolution),
                        if (complaint.resolvedDate?.isNotEmpty ?? false)
                          _InfoRow('Resolved Date', complaint.resolvedDate!),
                      ],
                    ),
                  ),
                ],

                if (complaint.latitude != null ||
                    complaint.longitude != null) ...[
                  const SizedBox(height: 12),
                  _SectionCard(
                    title: 'Location',
                    child: Column(
                      children: [
                        _InfoRow(
                          'Latitude',
                          complaint.latitude?.toString() ?? '-',
                        ),
                        _InfoRow(
                          'Longitude',
                          complaint.longitude?.toString() ?? '-',
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 12),

                _buildNextStep(complaint),

                const SizedBox(height: 24),
              ],
            ),
          );
        },
      ),
    );
  }

  // ============================================================
  // NEXT STEP
  // ============================================================

  Widget _buildNextStep(ComplaintModel complaint) {
    final status = complaint.status.trim().toUpperCase();

    if (status == 'NEW') {
      return _InfoActionCard(
        title: 'Waiting for Assignment',
        message: 'This complaint has not been assigned yet.',
        icon: Icons.hourglass_empty,
      );
    }

    if (status == 'ASSIGNED') {
      return _SectionCard(
        title: 'Next Step',
        child: _PrimaryAction(
          label: 'Start Work',
          icon: Icons.play_arrow,
          loading: _isSaving,
          onPressed: _startComplaint,
        ),
      );
    }

    if (status == 'IN_PROGRESS') {
      return _SectionCard(
        title: 'Next Step',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Complete the complaint work and enter the resolution details.',
            ),

            const SizedBox(height: 14),

            TextField(
              controller: _resolutionController,
              minLines: 3,
              maxLines: 5,
              enabled: !_isSaving,
              decoration: const InputDecoration(
                labelText: 'Resolution *',
                hintText: 'Enter what was done to resolve the complaint.',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 12),

            TextField(
              controller: _remarksController,
              minLines: 2,
              maxLines: 4,
              enabled: !_isSaving,
              decoration: const InputDecoration(
                labelText: 'Engineer Remarks',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 14),

            _PrimaryAction(
              label: 'Resolve Complaint',
              icon: Icons.check_circle,
              loading: _isSaving,
              onPressed: _resolveComplaint,
            ),
          ],
        ),
      );
    }

    if (status == 'RESOLVED') {
      return _SectionCard(
        title: 'Next Step',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Complaint is resolved. Close it after confirming the resolution.',
            ),

            const SizedBox(height: 14),

            _PrimaryAction(
              label: 'Close Complaint',
              icon: Icons.lock_outline,
              loading: _isSaving,
              onPressed: _closeComplaint,
            ),
          ],
        ),
      );
    }

    if (status == 'CLOSED') {
      return const _InfoActionCard(
        title: 'Complaint Closed',
        message: 'This complaint has been completed and closed.',
        icon: Icons.check_circle,
      );
    }

    if (status == 'CANCELLED') {
      return const _InfoActionCard(
        title: 'Complaint Cancelled',
        message: 'This complaint has been cancelled.',
        icon: Icons.cancel,
      );
    }

    return _InfoActionCard(
      title: 'Unknown Status',
      message: 'Current status: $status',
      icon: Icons.help_outline,
    );
  }
}

// ================================================================
// COMPLAINT HEADER
// ================================================================

class _ComplaintHeader extends StatelessWidget {
  const _ComplaintHeader({required this.complaint});

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
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),

            const SizedBox(height: 8),

            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StatusBadge(status: complaint.status),
                _PriorityBadge(priority: complaint.priority),
              ],
            ),

            const SizedBox(height: 10),

            Text(
              complaint.displayComplaintType,
              style: Theme.of(context).textTheme.titleMedium,
            ),

            const SizedBox(height: 4),

            Text('Engineer: ${complaint.displayEngineer}'),
          ],
        ),
      ),
    );
  }
}

// ================================================================
// STATUS TIMELINE
// ================================================================

class _StatusTimeline extends StatelessWidget {
  const _StatusTimeline({required this.complaint});

  final ComplaintModel complaint;

  @override
  Widget build(BuildContext context) {
    const statuses = ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];

    final currentIndex = statuses.indexOf(
      complaint.status.trim().toUpperCase(),
    );

    if (complaint.status.trim().toUpperCase() == 'CANCELLED') {
      return _InfoActionCard(
        title: 'Complaint Cancelled',
        message: 'This complaint has been cancelled.',
        icon: Icons.cancel,
      );
    }

    return _SectionCard(
      title: 'Progress',
      child: Column(
        children: List.generate(statuses.length, (index) {
          final status = statuses[index];

          final completed = currentIndex >= 0 && index <= currentIndex;

          final current = currentIndex == index;

          final last = index == statuses.length - 1;

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 32,
                child: Column(
                  children: [
                    Container(
                      width: 26,
                      height: 26,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: completed ? Colors.green : Colors.grey.shade300,
                      ),
                      child: Icon(
                        completed ? Icons.check : Icons.circle,
                        size: completed ? 16 : 8,
                        color: completed ? Colors.white : Colors.grey.shade500,
                      ),
                    ),
                    if (!last)
                      Container(
                        width: 2,
                        height: 42,
                        color: completed ? Colors.green : Colors.grey.shade300,
                      ),
                  ],
                ),
              ),

              const SizedBox(width: 10),

              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 3, bottom: 18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _statusDisplayName(status),
                        style: TextStyle(
                          fontWeight: current
                              ? FontWeight.bold
                              : FontWeight.w500,
                          color: completed
                              ? Colors.green.shade800
                              : Colors.grey.shade600,
                        ),
                      ),
                      if (current)
                        Text(
                          'Current status',
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.green.shade700,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          );
        }),
      ),
    );
  }

  String _statusDisplayName(String status) {
    switch (status) {
      case 'NEW':
        return 'New';

      case 'ASSIGNED':
        return 'Assigned';

      case 'IN_PROGRESS':
        return 'In Progress';

      case 'RESOLVED':
        return 'Resolved';

      case 'CLOSED':
        return 'Closed';

      default:
        return status.replaceAll('_', ' ');
    }
  }
}

// ================================================================
// SECTION CARD
// ================================================================

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

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
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
            ),

            const SizedBox(height: 12),

            child,
          ],
        ),
      ),
    );
  }
}

// ================================================================
// INFO ROW
// ================================================================

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);

  final String label;
  final Object? value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ),
          Expanded(
            child: Text(
              value == null || value.toString().trim().isEmpty
                  ? '-'
                  : value.toString(),
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}

// ================================================================
// PRIMARY ACTION
// ================================================================

class _PrimaryAction extends StatelessWidget {
  const _PrimaryAction({
    required this.label,
    required this.icon,
    required this.loading,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final bool loading;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: loading ? null : onPressed,
        icon: loading
            ? const SizedBox.square(
                dimension: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Icon(icon),
        label: Text(label),
      ),
    );
  }
}

// ================================================================
// INFO ACTION CARD
// ================================================================

class _InfoActionCard extends StatelessWidget {
  const _InfoActionCard({
    required this.title,
    required this.message,
    required this.icon,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
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
      ),
    );
  }
}

// ================================================================
// STATUS BADGE
// ================================================================

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(status);

    return _Badge(text: _statusName(status), color: color);
  }

  Color _statusColor(String value) {
    switch (value.trim().toUpperCase()) {
      case 'NEW':
        return Colors.blue;

      case 'ASSIGNED':
        return Colors.orange;

      case 'IN_PROGRESS':
        return Colors.deepPurple;

      case 'RESOLVED':
        return Colors.green;

      case 'CLOSED':
        return Colors.teal;

      case 'CANCELLED':
        return Colors.red;

      default:
        return Colors.grey;
    }
  }

  String _statusName(String value) {
    switch (value.trim().toUpperCase()) {
      case 'NEW':
        return 'New';

      case 'ASSIGNED':
        return 'Assigned';

      case 'IN_PROGRESS':
        return 'In Progress';

      case 'RESOLVED':
        return 'Resolved';

      case 'CLOSED':
        return 'Closed';

      case 'CANCELLED':
        return 'Cancelled';

      default:
        return value.replaceAll('_', ' ');
    }
  }
}

// ================================================================
// PRIORITY BADGE
// ================================================================

class _PriorityBadge extends StatelessWidget {
  const _PriorityBadge({required this.priority});

  final String priority;

  @override
  Widget build(BuildContext context) {
    final color = _priorityColor(priority);

    return _Badge(text: _priorityName(priority), color: color);
  }

  Color _priorityColor(String value) {
    switch (value.trim().toUpperCase()) {
      case 'EMERGENCY':
        return Colors.red;

      case 'URGENT':
        return Colors.deepOrange;

      case 'NORMAL':
        return Colors.blue;

      case 'LOW':
        return Colors.green;

      default:
        return Colors.grey;
    }
  }

  String _priorityName(String value) {
    switch (value.trim().toUpperCase()) {
      case 'EMERGENCY':
        return 'Emergency';

      case 'URGENT':
        return 'Urgent';

      case 'NORMAL':
        return 'Normal';

      case 'LOW':
        return 'Low';

      default:
        return value.isEmpty ? '-' : value;
    }
  }
}

// ================================================================
// BADGE
// ================================================================

class _Badge extends StatelessWidget {
  const _Badge({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

// ================================================================
// ERROR VIEW
// ================================================================

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.onRetry, required this.message});

  final VoidCallback onRetry;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 60),

            const SizedBox(height: 12),

            Text(message, textAlign: TextAlign.center),

            const SizedBox(height: 18),

            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
