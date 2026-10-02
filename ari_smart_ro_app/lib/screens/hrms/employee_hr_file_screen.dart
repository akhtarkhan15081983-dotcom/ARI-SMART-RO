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
    setState(() {
      _loading = true;
      _error = null;
    });
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

    final employee = Map<String, dynamic>.from(_data!['employee'] as Map? ?? const {});
    final lifecycle = Map<String, dynamic>.from(_data!['lifecycle'] as Map? ?? const {});
    final readiness = Map<String, dynamic>.from(lifecycle['readiness'] as Map? ?? const {});
    final ready = readiness['ready'] == true;

    return Scaffold(
      appBar: AppBar(
        title: Text('${employee['name'] ?? 'Employee'} • HR File'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
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
          _employeeHeader(employee, lifecycle, readiness, ready),
          Expanded(
            child: TabBarView(
              controller: _tabs,
              children: [
                _overview(employee, lifecycle, readiness),
                _records('Documents', _list('documents'), _documentTile),
                _records('Attendance', _list('attendance'), _attendanceTile),
                _records('Leave history', _list('leave'), _leaveTile),
                _records('Payroll history', _list('payroll'), _payrollTile),
                _records('Training', _list('training'), _trainingTile),
                _records('Performance', _list('performance'), _performanceTile),
                _careerAudit(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _list(String key) =>
      (_data?[key] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();

  Widget _employeeHeader(
    Map<String, dynamic> employee,
    Map<String, dynamic> lifecycle,
    Map<String, dynamic> readiness,
    bool ready,
  ) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
      color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: .35),
      child: Wrap(
        spacing: 18,
        runSpacing: 12,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          CircleAvatar(
            radius: 28,
            child: Text(
              (employee['name'] ?? 'E').toString().trim().isEmpty
                  ? 'E'
                  : (employee['name'] ?? 'E').toString().trim()[0].toUpperCase(),
            ),
          ),
          SizedBox(
            width: 260,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  employee['name']?.toString() ?? '-',
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                ),
                Text(
                  '${employee['employee_id'] ?? '-'} • ${employee['job_title'] ?? employee['designation'] ?? '-'}',
                ),
                Text('${employee['department'] ?? '-'} • ${employee['grade'] ?? '-'}'),
              ],
            ),
          ),
          _statusChip(ready ? 'READY FOR DUTY' : (lifecycle['hr_stage'] ?? 'PENDING').toString(), ready),
          _statusChip((lifecycle['employment_status'] ?? 'ONBOARDING').toString(), lifecycle['employment_status'] == 'CONFIRMED'),
          OutlinedButton.icon(
            onPressed: _showLifecycleActions,
            icon: const Icon(Icons.rule_folder_outlined),
            label: const Text('HR ACTIONS'),
          ),
        ],
      ),
    );
  }

  Widget _statusChip(String label, bool positive) => Chip(
        avatar: Icon(
          positive ? Icons.verified_outlined : Icons.pending_actions_outlined,
          size: 18,
        ),
        label: Text(label.replaceAll('_', ' ')),
      );

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
          _section(
            'Employment profile',
            Icons.business_center_outlined,
            [
              _kv('Designation', employee['designation']),
              _kv('Job title', employee['job_title']),
              _kv('Department', employee['department']),
              _kv('Grade', employee['grade']),
              _kv('Reporting manager', employee['reporting_manager']),
              _kv('Joining date', employee['joining_date']),
              _kv('Employment type', lifecycle['employment_type']),
              _kv('Work location', lifecycle['work_location']),
              _kv('Probation start', lifecycle['probation_start_date']),
              _kv('Confirmation due', lifecycle['confirmation_due_date']),
              _kv('Confirmed on', lifecycle['confirmed_at']),
            ],
          ),
          const SizedBox(height: 12),
          _section(
            'Personal & emergency information',
            Icons.contact_page_outlined,
            [
              _kv('Phone', employee['phone']),
              _kv('Email', employee['email']),
              _kv('DOB', employee['date_of_birth']),
              _kv('Gender', employee['gender']),
              _kv('Address', [employee['address'], employee['city'], employee['state'], employee['pincode']]
                  .where((e) => e != null && e.toString().trim().isNotEmpty)
                  .join(', ')),
              _kv('Emergency contact', '${employee['emergency_name'] ?? ''} ${employee['emergency_contact'] ?? ''}'.trim()),
            ],
          ),
          const SizedBox(height: 12),
          _section(
            'Ready-for-duty controls',
            Icons.fact_check_outlined,
            [
              ...checks.entries.map((e) => ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(e.value == true ? Icons.check_circle : Icons.error_outline),
                    title: Text(e.key.replaceAll('_', ' ').toUpperCase()),
                    trailing: Text(e.value == true ? 'COMPLETE' : 'PENDING'),
                  )),
              if ((documents['missing'] as List?)?.isNotEmpty == true)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.folder_off_outlined),
                  title: const Text('Missing mandatory documents'),
                  subtitle: Text((documents['missing'] as List).join(', ')),
                ),
            ],
          ),
          const SizedBox(height: 12),
          _section(
            'Probation & confirmation',
            Icons.workspace_premium_outlined,
            [
              _kv('Manager review', lifecycle['manager_review_status']),
              _kv('Manager note', lifecycle['manager_review_note']),
              _kv('HR review', lifecycle['hr_review_status']),
              _kv('HR note', lifecycle['hr_review_note']),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _review('MANAGER_REVIEW'),
                      icon: const Icon(Icons.supervisor_account_outlined),
                      label: const Text('MANAGER REVIEW'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _review('HR_REVIEW'),
                      icon: const Icon(Icons.how_to_reg_outlined),
                      label: const Text('HR REVIEW'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.tonalIcon(
                      onPressed: _extendProbation,
                      icon: const Icon(Icons.more_time),
                      label: const Text('EXTEND PROBATION'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _confirmEmployee,
                      icon: const Icon(Icons.verified_user_outlined),
                      label: const Text('CONFIRM EMPLOYEE'),
                    ),
                  ),
                ],
              ),
            ],
          ),
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
              Row(children: [Icon(icon), const SizedBox(width: 8), Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800))]),
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

  Widget _records(
    String title,
    List<Map<String, dynamic>> rows,
    Widget Function(Map<String, dynamic>) builder,
  ) {
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

  Widget _documentTile(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: Icon(row['verified'] == true ? Icons.verified_outlined : Icons.pending_outlined),
          title: Text((row['type'] ?? 'Document').toString()),
          subtitle: Text('No: ${row['number'] ?? '-'} • Expiry: ${row['expiry_date'] ?? 'No expiry'}'),
          trailing: Chip(label: Text(row['verified'] == true ? 'VERIFIED' : 'PENDING')),
        ),
      );

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
          const SizedBox(height: 10),
          if (career.isEmpty) const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('No career movements yet.'))),
          ...career.map((row) => Card(
                child: ListTile(
                  leading: const Icon(Icons.trending_up_outlined),
                  title: Text('${row['type'] ?? '-'} • ${row['status'] ?? '-'}'),
                  subtitle: Text('${row['effective_date'] ?? '-'}\n${row['old_job_title'] ?? '-'} → ${row['new_job_title'] ?? '-'}\n${row['reason'] ?? ''}'),
                ),
              )),
          const SizedBox(height: 18),
          const Text('HR audit trail', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          if (audit.isEmpty) const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('No lifecycle audit events yet.'))),
          ...audit.map((row) => Card(
                child: ListTile(
                  leading: const Icon(Icons.history_outlined),
                  title: Text('${row['type'] ?? '-'} • ${row['effective_date'] ?? '-'}'),
                  subtitle: Text('${row['from'] ?? ''} → ${row['to'] ?? ''}\n${row['note'] ?? ''}\nBy: ${row['by'] ?? '-'}'),
                ),
              )),
        ],
      ),
    );
  }

  Future<void> _showLifecycleActions() async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Wrap(
            runSpacing: 8,
            children: [
              const Text('Employee lifecycle actions', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
              ListTile(
                leading: const Icon(Icons.fact_check_outlined),
                title: const Text('Manager review'),
                onTap: () { Navigator.pop(context); _review('MANAGER_REVIEW'); },
              ),
              ListTile(
                leading: const Icon(Icons.verified_user_outlined),
                title: const Text('HR review'),
                onTap: () { Navigator.pop(context); _review('HR_REVIEW'); },
              ),
              ListTile(
                leading: const Icon(Icons.more_time),
                title: const Text('Extend probation'),
                onTap: () { Navigator.pop(context); _extendProbation(); },
              ),
              ListTile(
                leading: const Icon(Icons.workspace_premium_outlined),
                title: const Text('Confirm employee'),
                onTap: () { Navigator.pop(context); _confirmEmployee(); },
              ),
              ListTile(
                leading: const Icon(Icons.logout_outlined),
                title: const Text('Start notice / separation'),
                onTap: () { Navigator.pop(context); _startNotice(); },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _review(String action) async {
    String note = '';
    String status = 'APPROVED';
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(action == 'HR_REVIEW' ? 'HR Review' : 'Manager Review'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: status,
                items: const [
                  DropdownMenuItem(value: 'APPROVED', child: Text('Approve')),
                  DropdownMenuItem(value: 'REJECTED', child: Text('Needs correction')),
                ],
                onChanged: (v) => setLocal(() => status = v ?? 'APPROVED'),
              ),
              const SizedBox(height: 10),
              TextField(
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Review note', border: OutlineInputBorder()),
                onChanged: (v) => note = v,
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('SAVE REVIEW')),
          ],
        ),
      ),
    );
    if (submit != true) return;
    await _runAction(action, note: note, extra: {'status': status});
  }

  Future<void> _extendProbation() async {
    int months = 1;
    String note = '';
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Extend probation'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<int>(
                initialValue: months,
                items: const [1, 2, 3, 6]
                    .map((m) => DropdownMenuItem(value: m, child: Text('$m month${m == 1 ? '' : 's'}')))
                    .toList(),
                onChanged: (v) => setLocal(() => months = v ?? 1),
              ),
              const SizedBox(height: 10),
              TextField(
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Reason', border: OutlineInputBorder()),
                onChanged: (v) => note = v,
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('EXTEND')),
          ],
        ),
      ),
    );
    if (submit == true) await _runAction('EXTEND_PROBATION', note: note, extra: {'months': months});
  }

  Future<void> _confirmEmployee() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm employment?'),
        content: const Text('Manager and HR reviews must both be approved. This action creates an auditable confirmation event.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('CONFIRM EMPLOYEE')),
        ],
      ),
    );
    if (confirmed == true) await _runAction('CONFIRM', note: 'Employment confirmed after approved probation reviews.');
  }

  Future<void> _startNotice() async {
    String reason = '';
    String type = 'RESIGNATION';
    DateTime lastDay = DateTime.now().add(const Duration(days: 30));
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Start notice / separation'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: type,
                  items: const [
                    DropdownMenuItem(value: 'RESIGNATION', child: Text('Resignation')),
                    DropdownMenuItem(value: 'TERMINATION', child: Text('Termination')),
                    DropdownMenuItem(value: 'CONTRACT_END', child: Text('Contract end')),
                  ],
                  onChanged: (v) => setLocal(() => type = v ?? type),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Last working date'),
                  subtitle: Text('${lastDay.year}-${lastDay.month.toString().padLeft(2, '0')}-${lastDay.day.toString().padLeft(2, '0')}'),
                  trailing: const Icon(Icons.edit_calendar),
                  onTap: () async {
                    final value = await showDatePicker(
                      context: context,
                      initialDate: lastDay,
                      firstDate: DateTime.now(),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                    );
                    if (value != null) setLocal(() => lastDay = value);
                  },
                ),
                TextField(
                  maxLines: 3,
                  decoration: const InputDecoration(labelText: 'Reason / HR note', border: OutlineInputBorder()),
                  onChanged: (v) => reason = v,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('START NOTICE')),
          ],
        ),
      ),
    );
    if (submit == true) {
      await _runAction('START_NOTICE', note: reason, extra: {
        'separation_type': type,
        'last_working_date': '${lastDay.year}-${lastDay.month.toString().padLeft(2, '0')}-${lastDay.day.toString().padLeft(2, '0')}',
      });
    }
  }

  Future<void> _runAction(
    String action, {
    String note = '',
    Map<String, dynamic> extra = const {},
  }) async {
    try {
      await _service.lifecycleAction(widget.employeeId, action, note: note, extra: extra);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('HR lifecycle updated.')));
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }
}
