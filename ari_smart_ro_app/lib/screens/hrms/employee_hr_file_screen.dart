import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../services/corporate_hrms_service.dart';

class EmployeeHrFileScreen extends StatefulWidget {
  const EmployeeHrFileScreen({super.key, required this.employeeId});

  final int employeeId;

  @override
  State<EmployeeHrFileScreen> createState() => _EmployeeHrFileScreenState();
}

class _EmployeeHrFileScreenState extends State<EmployeeHrFileScreen>
    with SingleTickerProviderStateMixin {
  final _service = CorporateHrmsService();
  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = true;
  bool _documentBusy = false;
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 8, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final value = await _service.employeeFile(widget.employeeId);
      if (mounted) setState(() => _data = value);
    } catch (error) {
      if (mounted) {
        setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null || _data == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Employee HR File')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error ?? 'Employee file unavailable.'),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('RETRY')),
            ],
          ),
        ),
      );
    }

    final employee = _map('employee');
    final lifecycle = _map('lifecycle');
    final readiness = Map<String, dynamic>.from(lifecycle['readiness'] as Map? ?? const {});
    final ready = readiness['ready'] == true;

    return Scaffold(
      appBar: AppBar(
        title: Text('${employee['name'] ?? 'Employee'} • HR File'),
        actions: [
          IconButton(onPressed: _load, tooltip: 'Refresh', icon: const Icon(Icons.refresh)),
          const SizedBox(width: 8),
        ],
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabs: const [
            Tab(text: 'OVERVIEW'),
            Tab(text: 'DOCUMENTS'),
            Tab(text: 'ATTENDANCE'),
            Tab(text: 'LEAVE'),
            Tab(text: 'PAYROLL'),
            Tab(text: 'TRAINING'),
            Tab(text: 'PERFORMANCE'),
            Tab(text: 'CAREER & AUDIT'),
          ],
        ),
      ),
      body: Column(
        children: [
          _header(employee, lifecycle, ready),
          Expanded(
            child: TabBarView(
              controller: _tabs,
              children: [
                _overview(employee, lifecycle, readiness),
                _documents(),
                _recordList('Attendance', 'attendance', _attendanceTile),
                _recordList('Leave history', 'leave', _leaveTile),
                _recordList('Payroll history', 'payroll', _payrollTile),
                _recordList('Training', 'training', _trainingTile),
                _recordList('Performance', 'performance', _performanceTile),
                _careerAudit(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Map<String, dynamic> _map(String key) =>
      Map<String, dynamic>.from(_data?[key] as Map? ?? const {});

  List<Map<String, dynamic>> _list(String key) =>
      (_data?[key] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();

  Widget _header(
    Map<String, dynamic> employee,
    Map<String, dynamic> lifecycle,
    bool ready,
  ) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: .35),
      child: Wrap(
        spacing: 14,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          CircleAvatar(
            radius: 26,
            child: Text((employee['name'] ?? 'E').toString().trim().isEmpty
                ? 'E'
                : (employee['name'] ?? 'E').toString().trim()[0].toUpperCase()),
          ),
          SizedBox(
            width: 270,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(employee['name']?.toString() ?? '-',
                    style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
                Text('${employee['employee_id'] ?? '-'} • ${employee['job_title'] ?? employee['designation'] ?? '-'}'),
                Text('${employee['department'] ?? '-'} • ${employee['grade'] ?? '-'}'),
              ],
            ),
          ),
          Chip(label: Text(ready ? 'READY FOR DUTY' : (lifecycle['hr_stage'] ?? 'PENDING').toString().replaceAll('_', ' '))),
          Chip(label: Text((lifecycle['employment_status'] ?? 'ONBOARDING').toString())),
          OutlinedButton.icon(
            onPressed: _showLifecycleActions,
            icon: const Icon(Icons.rule_folder_outlined),
            label: const Text('HR ACTIONS'),
          ),
        ],
      ),
    );
  }

  Widget _overview(
    Map<String, dynamic> employee,
    Map<String, dynamic> lifecycle,
    Map<String, dynamic> readiness,
  ) {
    final checks = Map<String, dynamic>.from(readiness['checks'] as Map? ?? const {});
    final documents = Map<String, dynamic>.from(readiness['documents'] as Map? ?? const {});
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _section('Employment profile', Icons.business_center_outlined, [
            _kv('Designation', employee['designation']),
            _kv('Job title', employee['job_title']),
            _kv('Department', employee['department']),
            _kv('Grade', employee['grade']),
            _kv('Reporting manager', employee['reporting_manager']),
            _kv('Joining date', employee['joining_date']),
            _kv('Employment type', lifecycle['employment_type']),
            _kv('Employment status', lifecycle['employment_status']),
            _kv('Work location', lifecycle['work_location']),
            _kv('Confirmation due', lifecycle['confirmation_due_date']),
          ]),
          const SizedBox(height: 12),
          _section('Ready-for-duty controls', Icons.fact_check_outlined, [
            ...checks.entries.map((entry) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(entry.value == true ? Icons.check_circle : Icons.error_outline),
                  title: Text(entry.key.replaceAll('_', ' ').toUpperCase()),
                  trailing: Text(entry.value == true ? 'COMPLETE' : 'BLOCKED'),
                )),
            if ((documents['missing'] as List?)?.isNotEmpty == true)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.folder_off_outlined),
                title: const Text('Missing mandatory documents'),
                subtitle: Text((documents['missing'] as List).join(', ')),
              ),
          ]),
          const SizedBox(height: 12),
          _section('Reviews', Icons.how_to_reg_outlined, [
            _kv('Manager review', lifecycle['manager_review_status']),
            _kv('Manager note', lifecycle['manager_review_note']),
            _kv('HR review', lifecycle['hr_review_status']),
            _kv('HR note', lifecycle['hr_review_note']),
          ]),
        ],
      ),
    );
  }

  Widget _documents() {
    final rows = _list('documents');
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              const Expanded(
                child: Text('Employee Documents', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
              ),
              FilledButton.icon(
                onPressed: _documentBusy ? null : _uploadDocument,
                icon: const Icon(Icons.upload_file),
                label: const Text('UPLOAD DOCUMENT'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'MISSING, REJECTED and EXPIRED mandatory documents block READY FOR DUTY. Uploaded files require HR verification.',
          ),
          const SizedBox(height: 12),
          ...rows.map(_documentTile),
        ],
      ),
    );
  }

  Widget _documentTile(Map<String, dynamic> row) {
    final status = (row['status'] ?? (row['verified'] == true ? 'VERIFIED' : 'MISSING')).toString();
    final id = (row['id'] as num?)?.toInt();
    final audit = (row['audit'] as List<dynamic>? ?? const []);
    return Card(
      child: ExpansionTile(
        leading: Icon(_documentIcon(status)),
        title: Text((row['type'] ?? row['document_type'] ?? 'Document').toString().replaceAll('_', ' ')),
        subtitle: Text('${row['file_name']?.toString().isNotEmpty == true ? row['file_name'] : 'No file'} • Expiry: ${row['expiry_date'] ?? 'No expiry'}'),
        trailing: Chip(label: Text(status)),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if ((row['reason'] ?? '').toString().isNotEmpty)
                  Text('Latest reason: ${row['reason']} • ${row['reviewer'] ?? ''}'),
                if (id != null) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      OutlinedButton.icon(
                        onPressed: _documentBusy ? null : () => _reviewDocument(id, 'VERIFY'),
                        icon: const Icon(Icons.verified_outlined),
                        label: const Text('VERIFY'),
                      ),
                      OutlinedButton.icon(
                        onPressed: _documentBusy ? null : () => _reviewDocument(id, 'REJECT'),
                        icon: const Icon(Icons.cancel_outlined),
                        label: const Text('REJECT'),
                      ),
                      OutlinedButton.icon(
                        onPressed: _documentBusy ? null : () => _reviewDocument(id, 'EXPIRE'),
                        icon: const Icon(Icons.event_busy_outlined),
                        label: const Text('MARK EXPIRED'),
                      ),
                    ],
                  ),
                ],
                if (audit.isNotEmpty) ...[
                  const Divider(height: 24),
                  const Text('Audit history', style: TextStyle(fontWeight: FontWeight.w800)),
                  ...audit.map((entry) {
                    final item = Map<String, dynamic>.from(entry as Map);
                    return ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text('${item['status'] ?? item['event'] ?? '-'} • ${item['reviewer'] ?? '-'}'),
                      subtitle: Text('${item['reason'] ?? ''}\n${item['created_at'] ?? ''}'),
                    );
                  }),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  IconData _documentIcon(String status) {
    switch (status) {
      case 'VERIFIED':
        return Icons.verified_outlined;
      case 'REJECTED':
        return Icons.cancel_outlined;
      case 'EXPIRED':
        return Icons.event_busy_outlined;
      case 'UPLOADED':
        return Icons.cloud_done_outlined;
      default:
        return Icons.upload_file_outlined;
    }
  }

  Widget _recordList(
    String title,
    String key,
    Widget Function(Map<String, dynamic>) builder,
  ) {
    final rows = _list(key);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          if (rows.isEmpty)
            const Card(child: Padding(padding: EdgeInsets.all(20), child: Text('No records available.')))
          else
            ...rows.map(builder),
        ],
      ),
    );
  }

  Widget _attendanceTile(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: const Icon(Icons.schedule_outlined),
          title: Text('${row['date'] ?? '-'} • ${row['status'] ?? '-'}'),
          subtitle: Text('Hours: ${row['working_hours'] ?? 0} • In: ${row['check_in'] ?? '-'} • Out: ${row['check_out'] ?? '-'}'),
        ),
      );

  Widget _leaveTile(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: const Icon(Icons.event_note_outlined),
          title: Text('${row['type'] ?? '-'} • ${row['status'] ?? '-'}'),
          subtitle: Text('${row['start'] ?? '-'} to ${row['end'] ?? '-'}\n${row['reason'] ?? ''}'),
        ),
      );

  Widget _payrollTile(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: const Icon(Icons.payments_outlined),
          title: Text('${row['month'] ?? '-'} • ₹${row['net_salary'] ?? 0}'),
          subtitle: Text('OT ₹${row['overtime_amount'] ?? 0} • Deductions ₹${row['other_deductions'] ?? 0}'),
          trailing: Chip(label: Text((row['status'] ?? '-').toString())),
        ),
      );

  Widget _trainingTile(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: const Icon(Icons.school_outlined),
          title: Text((row['course'] ?? 'Training').toString()),
          subtitle: Text('Due: ${row['due_date'] ?? '-'}'),
          trailing: Chip(label: Text((row['status'] ?? '-').toString())),
        ),
      );

  Widget _performanceTile(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: const Icon(Icons.insights_outlined),
          title: Text('${row['period_start'] ?? '-'} to ${row['period_end'] ?? '-'}'),
          subtitle: Text('Overall score: ${row['overall_score'] ?? 0}'),
          trailing: Chip(label: Text((row['status'] ?? '-').toString())),
        ),
      );

  Widget _careerAudit() {
    final career = _list('career');
    final audit = _list('audit');
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Career movements', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          ...career.map((row) => Card(
                child: ListTile(
                  leading: const Icon(Icons.trending_up_outlined),
                  title: Text('${row['type'] ?? '-'} • ${row['status'] ?? '-'}'),
                  subtitle: Text('${row['effective_date'] ?? '-'}\n${row['old_job_title'] ?? '-'} → ${row['new_job_title'] ?? '-'}\n${row['reason'] ?? ''}'),
                ),
              )),
          const SizedBox(height: 16),
          const Text('HR audit trail', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          ...audit.map((row) => Card(
                child: ListTile(
                  leading: const Icon(Icons.history),
                  title: Text('${row['type'] ?? '-'} • ${row['from'] ?? '-'} → ${row['to'] ?? '-'}'),
                  subtitle: Text('${row['note'] ?? ''}\nBy: ${row['by'] ?? '-'} • ${row['created_at'] ?? ''}'),
                ),
              )),
        ],
      ),
    );
  }

  Widget _section(String title, IconData icon, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(children: [
                Icon(icon),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
              ]),
              const Divider(height: 24),
              ...children,
            ],
          ),
        ),
      );

  Widget _kv(String label, dynamic value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 180, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700))),
            Expanded(child: Text((value ?? '-').toString().isEmpty ? '-' : (value ?? '-').toString())),
          ],
        ),
      );

  Future<void> _uploadDocument() async {
    final type = await _selectDocumentType();
    if (type == null) return;
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      withData: true,
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
    );
    if (result == null || result.files.isEmpty) return;
    final details = await _documentMetadata(type);
    if (details == null) return;
    setState(() => _documentBusy = true);
    try {
      await _service.uploadEmployeeDocument(
        widget.employeeId,
        documentType: type,
        file: result.files.single,
        documentNumber: details.$1,
        expiryDate: details.$2,
      );
      await _load();
      _message('$type uploaded. HR verification is now pending.');
    } catch (error) {
      _message(error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _documentBusy = false);
    }
  }

  Future<String?> _selectDocumentType() {
    const types = {
      'PHOTO': 'Photo',
      'AADHAAR': 'Aadhaar',
      'PAN': 'PAN',
      'ADDRESS_PROOF': 'Address Proof',
      'BANK_PROOF': 'Bank Proof',
      'QUALIFICATION': 'Qualification',
      'PREVIOUS_EMPLOYMENT': 'Previous Employment',
      'OTHER': 'Other company-required document',
    };
    return showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Document type'),
        children: types.entries
            .map((entry) => SimpleDialogOption(
                  onPressed: () => Navigator.pop(context, entry.key),
                  child: Text(entry.value),
                ))
            .toList(),
      ),
    );
  }

  Future<(String, String)?> _documentMetadata(String type) async {
    final number = TextEditingController();
    final expiry = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('$type details'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: number, decoration: const InputDecoration(labelText: 'Document number (optional)')),
            const SizedBox(height: 10),
            TextField(controller: expiry, decoration: const InputDecoration(labelText: 'Expiry date YYYY-MM-DD (optional)')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('CONTINUE')),
        ],
      ),
    );
    final value = result == true ? (number.text.trim(), expiry.text.trim()) : null;
    number.dispose();
    expiry.dispose();
    return value;
  }

  Future<void> _reviewDocument(int documentId, String action) async {
    final reason = await _reasonDialog('$action DOCUMENT');
    if (reason == null || reason.trim().isEmpty) return;
    setState(() => _documentBusy = true);
    try {
      await _service.reviewEmployeeDocument(
        widget.employeeId,
        documentId: documentId,
        action: action,
        reason: reason,
      );
      await _load();
      _message('Document $action completed and audited.');
    } catch (error) {
      _message(error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _documentBusy = false);
    }
  }

  Future<void> _showLifecycleActions() async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            const ListTile(
              title: Text('HR lifecycle actions', style: TextStyle(fontWeight: FontWeight.w900)),
              subtitle: Text('Sensitive employment changes use the Corporate HRMS Phase-2 approval workflow.'),
            ),
            ListTile(
              leading: const Icon(Icons.account_tree_outlined),
              title: const Text('Employee Lifecycle workspace'),
              subtitle: const Text('Probation, confirmation, promotion, increment, transfer, exit and clearance'),
              onTap: () {
                Navigator.pop(sheetContext);
                Navigator.of(context).pushNamed('/hrms/lifecycle');
              },
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.supervisor_account_outlined),
              title: const Text('Manager onboarding review'),
              onTap: () { Navigator.pop(sheetContext); _lifecycleAction('MANAGER_REVIEW', withStatus: true); },
            ),
            ListTile(
              leading: const Icon(Icons.how_to_reg_outlined),
              title: const Text('HR onboarding review'),
              onTap: () { Navigator.pop(sheetContext); _lifecycleAction('HR_REVIEW', withStatus: true); },
            ),
            ListTile(
              leading: const Icon(Icons.admin_panel_settings_outlined),
              title: const Text('Admin Ready override'),
              subtitle: const Text('Admin only; mandatory reason + audit'),
              onTap: () { Navigator.pop(sheetContext); _lifecycleAction('OVERRIDE_READY'); },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _lifecycleAction(String action, {bool withStatus = false}) async {
    final reason = await _reasonDialog(action.replaceAll('_', ' '));
    if (reason == null || reason.trim().isEmpty) return;
    try {
      await _service.lifecycleAction(
        widget.employeeId,
        action,
        note: reason,
        extra: withStatus ? const {'status': 'APPROVED'} : const {},
      );
      await _load();
      _message('$action completed.');
    } catch (error) {
      _message(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<String?> _reasonDialog(String title) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Reason / review note *',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          FilledButton(onPressed: () => Navigator.pop(context, controller.text.trim()), child: const Text('SUBMIT')),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  void _message(String value) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value)));
  }
}
