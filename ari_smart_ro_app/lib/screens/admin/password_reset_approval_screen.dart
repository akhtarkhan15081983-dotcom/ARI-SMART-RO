import 'package:flutter/material.dart';

import '../../services/password_reset_service.dart';

class PasswordResetApprovalScreen extends StatefulWidget {
  const PasswordResetApprovalScreen({super.key});

  @override
  State<PasswordResetApprovalScreen> createState() =>
      _PasswordResetApprovalScreenState();
}

class _PasswordResetApprovalScreenState
    extends State<PasswordResetApprovalScreen> {
  final _service = const PasswordResetService();
  List<Map<String, dynamic>> _requests = const [];
  bool _loading = true;
  String? _error;

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
      final rows = await _service.pendingRequests();
      if (!mounted) return;
      setState(() => _requests = rows);
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error.toString().replaceFirst('Exception: ', ''),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _review(Map<String, dynamic> row, String action) async {
    final requestId = (row['id'] as num).toInt();
    final name = row['name']?.toString() ?? row['phone']?.toString() ?? 'User';

    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text(action == 'approve' ? 'Approve reset?' : 'Reject reset?'),
            content: Text(
              action == 'approve'
                  ? 'Approve password reset for $name? A one-time code valid for 15 minutes will be generated.'
                  : 'Reject password reset request for $name?',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('CANCEL'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: Text(action == 'approve' ? 'APPROVE' : 'REJECT'),
              ),
            ],
          ),
        ) ??
        false;

    if (!confirmed) return;

    try {
      final code = await _service.review(
        requestId: requestId,
        action: action,
      );

      if (!mounted) return;
      if (action == 'approve' && code != null) {
        await showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (dialogContext) => AlertDialog(
            title: const Text('One-time reset code'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Give this code only to $name.'),
                const SizedBox(height: 16),
                SelectableText(
                  code,
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        fontWeight: FontWeight.w900,
                        letterSpacing: 8,
                      ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'This code expires in 15 minutes and cannot reveal the old password.',
                ),
              ],
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('DONE'),
              ),
            ],
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Password reset request rejected.')),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Password Reset Approvals'),
          actions: [
            IconButton(
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(_error!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed: _load,
                            child: const Text('RETRY'),
                          ),
                        ],
                      ),
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        const Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Text(
                              'For security, existing passwords are never shown. Approving a request creates a temporary one-time reset code.',
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (_requests.isEmpty)
                          const Card(
                            child: Padding(
                              padding: EdgeInsets.all(24),
                              child: Center(
                                child: Text('No pending password reset requests.'),
                              ),
                            ),
                          ),
                        ..._requests.map(
                          (row) => Card(
                            child: ListTile(
                              leading: const CircleAvatar(
                                child: Icon(Icons.lock_reset_rounded),
                              ),
                              title: Text(
                                row['name']?.toString() ??
                                    row['phone']?.toString() ??
                                    'User',
                              ),
                              subtitle: Text(
                                '${row['phone']} • ${row['role']}\nStatus: ${row['status']}',
                              ),
                              isThreeLine: true,
                              trailing: row['status'] == 'PENDING'
                                  ? PopupMenuButton<String>(
                                      onSelected: (value) =>
                                          _review(row, value),
                                      itemBuilder: (_) => const [
                                        PopupMenuItem(
                                          value: 'approve',
                                          child: ListTile(
                                            leading: Icon(
                                              Icons.check_circle_outline,
                                            ),
                                            title: Text('Approve'),
                                          ),
                                        ),
                                        PopupMenuItem(
                                          value: 'reject',
                                          child: ListTile(
                                            leading: Icon(Icons.cancel_outlined),
                                            title: Text('Reject'),
                                          ),
                                        ),
                                      ],
                                    )
                                  : const Icon(Icons.timer_outlined),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
      );
}
