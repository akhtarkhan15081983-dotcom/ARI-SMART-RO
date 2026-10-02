import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/corporate_hrms_lifecycle_service.dart';
import '../../services/corporate_hrms_service.dart';

class EmployeeLifecycleScreen extends StatefulWidget {
  const EmployeeLifecycleScreen({super.key, this.initialEmployeeId});

  final int? initialEmployeeId;

  @override
  State<EmployeeLifecycleScreen> createState() => _EmployeeLifecycleScreenState();
}

class _EmployeeLifecycleScreenState extends State<EmployeeLifecycleScreen> {
  final _service = CorporateHrmsService();
  final _search = TextEditingController();

  bool _loading = true;
  bool _busy = false;
  String? _error;
  String _role = '';
  String _query = '';
  String _status = 'ALL';
  String _type = 'ALL';
  int? _selectedEmployeeId;
  Map<String, dynamic> _command = const {};
  Map<String, dynamic> _probation = const {};
  List<Map<String, dynamic>> _actions = const [];
  List<Map<String, dynamic>> _exits = const [];
  List<Map<String, dynamic>> _directory = const [];
  Map<String, dynamic>? _timeline;

  bool get _canManage => const {'ADMIN', 'OFFICE'}.contains(_role);
  bool get _canManagerReview => const {'ADMIN', 'MANAGER'}.contains(_role);
  bool get _canHrReview => const {'ADMIN', 'OFFICE'}.contains(_role);
  bool get _canApprove => _role == 'ADMIN';
  bool get _canExitManage => const {'ADMIN', 'OFFICE'}.contains(_role);
  bool get _canExitClearance => const {'ADMIN', 'MANAGER', 'OFFICE'}.contains(_role);

  @override
  void initState() {
    super.initState();
    _selectedEmployeeId = widget.initialEmployeeId;
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
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
      _role = (await ApiService.getRole() ?? '').toUpperCase();
      final results = await Future.wait([
        _service.lifecycleCommandCenter(),
        _service.lifecycleProbationQueue(),
        _service.lifecycleActions(),
        _service.exitCases(),
        _service.directory(),
      ]);
      _command = Map<String, dynamic>.from(results[0] as Map);
      _probation = Map<String, dynamic>.from(results[1] as Map);
      _actions = List<Map<String, dynamic>>.from(results[2] as List);
      _exits = List<Map<String, dynamic>>.from(results[3] as List);
      _directory = List<Map<String, dynamic>>.from(results[4] as List);
      if (_selectedEmployeeId != null) {
        _timeline = await _service.lifecycleTimeline(_selectedEmployeeId!);
      }
    } catch (error) {
      _error = error.toString().replaceFirst('Exception: ', '');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _refreshTimeline(int employeeId) async {
    try {
      final value = await _service.lifecycleTimeline(employeeId);
      if (mounted) {
        setState(() {
          _selectedEmployeeId = employeeId;
          _timeline = value;
        });
      }
    } catch (error) {
      _showError(error);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Employee Lifecycle'),
        actions: [
          IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh), tooltip: 'Refresh'),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _errorState()
              : LayoutBuilder(
                  builder: (context, constraints) {
                    if (constraints.maxWidth >= 1180) return _desktop();
                    return _mobile();
                  },
                ),
      floatingActionButton: _canManage
          ? FloatingActionButton.extended(
              onPressed: _busy ? null : _showCreateAction,
              icon: const Icon(Icons.add_task),
              label: const Text('LIFECYCLE ACTION'),
            )
          : null,
    );
  }

  Widget _errorState() => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.cloud_off_outlined, size: 46),
                  const SizedBox(height: 12),
                  const Text('Lifecycle workspace could not load', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 8),
                  Text(_error!, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton.icon(onPressed: _load, icon: const Icon(Icons.refresh), label: const Text('RETRY')),
                ],
              ),
            ),
          ),
        ),
      );

  Widget _desktop() => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 7,
            child: RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(18),
                children: [
                  _hero(),
                  const SizedBox(height: 14),
                  _metrics(),
                  const SizedBox(height: 16),
                  _filters(),
                  const SizedBox(height: 12),
                  _actionTable(),
                  const SizedBox(height: 16),
                  _exitQueue(),
                ],
              ),
            ),
          ),
          const VerticalDivider(width: 1),
          SizedBox(
            width: 420,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _probationQueue(),
                const SizedBox(height: 12),
                _timelinePanel(),
              ],
            ),
          ),
        ],
      );

  Widget _mobile() => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            _hero(),
            const SizedBox(height: 12),
            _metrics(),
            const SizedBox(height: 14),
            _filters(),
            const SizedBox(height: 10),
            _mobileActions(),
            const SizedBox(height: 14),
            _probationQueue(),
            const SizedBox(height: 14),
            _exitQueue(),
            const SizedBox(height: 14),
            _timelinePanel(),
            const SizedBox(height: 90),
          ],
        ),
      );

  Widget _hero() => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF123B66), Color(0xFF1769AA)]),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 16,
          runSpacing: 12,
          children: [
            const SizedBox(
              width: 600,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('CORPORATE HRMS • PHASE 2', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800)),
                  SizedBox(height: 4),
                  Text('Employee Lifecycle Command Center', style: TextStyle(color: Colors.white, fontSize: 27, fontWeight: FontWeight.w900)),
                  SizedBox(height: 5),
                  Text('Probation, confirmation, promotion, increment, transfer, exit clearance and separation with auditable approvals.', style: TextStyle(color: Colors.white70)),
                ],
              ),
            ),
            Chip(label: Text('ROLE • ${_role.isEmpty ? 'EMPLOYEE' : _role}')),
          ],
        ),
      );

  Widget _metrics() {
    final values = <(String, dynamic, IconData)>[
      ('Probation overdue', _command['probation_overdue'], Icons.warning_amber_outlined),
      ('Confirmation pending', _command['confirmation_pending'], Icons.workspace_premium_outlined),
      ('Promotions', _command['promotion_pending'], Icons.trending_up),
      ('Increments', _command['increment_pending'], Icons.currency_rupee),
      ('Transfers', _command['transfer_pending'], Icons.swap_horiz),
      ('On notice', _command['employees_on_notice'], Icons.logout_outlined),
      ('Clearance pending', _command['exit_clearance_pending'], Icons.fact_check_outlined),
      ('Settlement pending', _command['final_settlement_pending'], Icons.payments_outlined),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1200 ? 4 : constraints.maxWidth >= 650 ? 2 : 1;
        final width = (constraints.maxWidth - ((columns - 1) * 10)) / columns;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: values
              .map((item) => SizedBox(
                    width: width,
                    child: Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Row(children: [
                          CircleAvatar(child: Icon(item.$3)),
                          const SizedBox(width: 12),
                          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${item.$2 ?? 0}', style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w900)),
                            Text(item.$1, maxLines: 1, overflow: TextOverflow.ellipsis),
                          ])),
                        ]),
                      ),
                    ),
                  ))
              .toList(),
        );
      },
    );
  }

  Widget _filters() => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Wrap(
            spacing: 10,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SizedBox(
                width: 310,
                child: TextField(
                  controller: _search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search employee, type, status...', border: OutlineInputBorder(), isDense: true),
                ),
              ),
              DropdownButton<String>(
                value: _type,
                items: const ['ALL', 'PROBATION_REVIEW', 'PROBATION_EXTENSION', 'CONFIRMATION', 'PROMOTION', 'INCREMENT', 'TRANSFER']
                    .map((v) => DropdownMenuItem(value: v, child: Text(v.replaceAll('_', ' '))))
                    .toList(),
                onChanged: (value) => setState(() => _type = value ?? 'ALL'),
              ),
              DropdownButton<String>(
                value: _status,
                items: const ['ALL', 'DRAFT', 'MANAGER_REVIEW', 'HR_REVIEW', 'PENDING_APPROVAL', 'APPROVED', 'APPLIED', 'REJECTED']
                    .map((v) => DropdownMenuItem(value: v, child: Text(v.replaceAll('_', ' '))))
                    .toList(),
                onChanged: (value) => setState(() => _status = value ?? 'ALL'),
              ),
              if (_canExitManage)
                OutlinedButton.icon(onPressed: _busy ? null : _showCreateExit, icon: const Icon(Icons.person_remove_outlined), label: const Text('START EXIT')),
            ],
          ),
        ),
      );

  List<Map<String, dynamic>> get _filteredActions {
    final q = _query.trim().toLowerCase();
    return _actions.where((row) {
      if (_type != 'ALL' && row['action_type'] != _type) return false;
      if (_status != 'ALL' && row['status'] != _status) return false;
      if (q.isEmpty) return true;
      final employee = _employee(row['employee_id']);
      return [row['action_type'], row['status'], row['reason'], employee?['name'], employee?['employee_id']]
          .any((v) => (v ?? '').toString().toLowerCase().contains(q));
    }).toList();
  }

  Map<String, dynamic>? _employee(dynamic id) {
    final target = (id as num?)?.toInt();
    if (target == null) return null;
    for (final row in _directory) {
      if ((row['id'] as num?)?.toInt() == target) return row;
    }
    return null;
  }

  Widget _actionTable() {
    final rows = _filteredActions;
    if (rows.isEmpty) return _empty('No lifecycle actions match the current filters.');
    return Card(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columns: const [
            DataColumn(label: Text('EMPLOYEE')),
            DataColumn(label: Text('ACTION')),
            DataColumn(label: Text('EFFECTIVE')),
            DataColumn(label: Text('STATUS')),
            DataColumn(label: Text('REASON')),
            DataColumn(label: Text('WORKFLOW')),
          ],
          rows: rows.map((row) {
            final employee = _employee(row['employee_id']);
            return DataRow(
              onSelectChanged: (_) => _refreshTimeline((row['employee_id'] as num).toInt()),
              cells: [
                DataCell(Text('${employee?['name'] ?? 'Employee #${row['employee_id']}'}\n${employee?['employee_id'] ?? ''}')),
                DataCell(Text((row['action_type'] ?? '-').toString().replaceAll('_', ' '))),
                DataCell(Text('${row['effective_date'] ?? '-'}')),
                DataCell(_statusChip('${row['status'] ?? '-'}')),
                DataCell(SizedBox(width: 220, child: Text('${row['reason'] ?? '-'}', maxLines: 2, overflow: TextOverflow.ellipsis))),
                DataCell(_workflowButton(row)),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _mobileActions() {
    final rows = _filteredActions;
    if (rows.isEmpty) return _empty('No lifecycle actions match the current filters.');
    return Column(
      children: rows.map((row) {
        final employee = _employee(row['employee_id']);
        return Card(
          child: InkWell(
            onTap: () => _refreshTimeline((row['employee_id'] as num).toInt()),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(children: [
                    Expanded(child: Text(employee?['name']?.toString() ?? 'Employee #${row['employee_id']}', style: const TextStyle(fontWeight: FontWeight.w900))),
                    _statusChip('${row['status'] ?? '-'}'),
                  ]),
                  const SizedBox(height: 6),
                  Text((row['action_type'] ?? '-').toString().replaceAll('_', ' '), style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text('Effective: ${row['effective_date'] ?? '-'}'),
                  if ((row['reason'] ?? '').toString().isNotEmpty) Text('Reason: ${row['reason']}'),
                  const SizedBox(height: 8),
                  Align(alignment: Alignment.centerRight, child: _workflowButton(row)),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _workflowButton(Map<String, dynamic> row) {
    final status = (row['status'] ?? '').toString();
    String? label;
    String? action;
    if (status == 'DRAFT' && _canManage) {
      label = 'SUBMIT'; action = 'SUBMIT_MANAGER';
    } else if (status == 'MANAGER_REVIEW' && _canManagerReview) {
      label = 'MANAGER REVIEW'; action = 'MANAGER_REVIEW';
    } else if (status == 'HR_REVIEW' && _canHrReview) {
      label = 'HR REVIEW'; action = 'HR_REVIEW';
    } else if (status == 'PENDING_APPROVAL' && _canApprove) {
      label = 'APPROVE'; action = 'APPROVE';
    } else if (status == 'APPROVED' && _canApprove) {
      label = 'APPLY'; action = 'APPLY';
    }
    if (label == null || action == null) return const Text('—');
    return FilledButton.tonal(
      onPressed: _busy ? null : () => _workflow(row, action!),
      child: Text(label),
    );
  }

  Widget _probationQueue() {
    final items = (_probation['items'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Probation / Confirmation Queue', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const Divider(),
            if (items.isEmpty) const Text('No probation confirmations are currently due.'),
            ...items.take(15).map((row) {
              final employee = _employee(row['employee_id']);
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(row['overdue'] == true ? Icons.warning_amber : Icons.hourglass_top),
                title: Text(employee?['name']?.toString() ?? row['employee_code']?.toString() ?? 'Employee'),
                subtitle: Text('Due ${row['confirmation_due_date'] ?? '-'} • ${row['days_to_due'] ?? 0} days'),
                trailing: _canManage
                    ? IconButton(
                        tooltip: 'Create confirmation action',
                        onPressed: () => _showCreateAction(employeeId: (row['employee_id'] as num?)?.toInt(), presetType: 'CONFIRMATION'),
                        icon: const Icon(Icons.add_task),
                      )
                    : null,
                onTap: () => _refreshTimeline((row['employee_id'] as num).toInt()),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _exitQueue() => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(children: [
                const Expanded(child: Text('Exit / Clearance / Separation', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900))),
                if (_canExitManage) IconButton(onPressed: _showCreateExit, icon: const Icon(Icons.add), tooltip: 'Start exit case'),
              ]),
              const Divider(),
              if (_exits.isEmpty) const Text('No active or historical exit cases.'),
              ..._exits.take(50).map(_exitTile),
            ],
          ),
        ),
      );

  Widget _exitTile(Map<String, dynamic> row) {
    final employee = _employee(row['employee_id']);
    final clearances = (row['clearances'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      title: Text(employee?['name']?.toString() ?? 'Employee #${row['employee_id']}', style: const TextStyle(fontWeight: FontWeight.w800)),
      subtitle: Text('${(row['separation_type'] ?? '-').toString().replaceAll('_', ' ')} • LWD ${row['approved_last_working_date'] ?? row['proposed_last_working_date'] ?? '-'}'),
      trailing: _statusChip('${row['status'] ?? '-'}'),
      onExpansionChanged: (open) {
        if (open) _refreshTimeline((row['employee_id'] as num).toInt());
      },
      children: [
        ...clearances.map((item) => ListTile(
              dense: true,
              contentPadding: const EdgeInsets.only(left: 12),
              leading: const Icon(Icons.fact_check_outlined),
              title: Text((item['type'] ?? '-').toString().replaceAll('_', ' ')),
              subtitle: Text('Status: ${item['status'] ?? '-'}${(item['note'] ?? '').toString().isEmpty ? '' : ' • ${item['note']}'}'),
              trailing: _canExitClearance && const {'NOTICE', 'CLEARANCE'}.contains(row['status'])
                  ? PopupMenuButton<String>(
                      onSelected: (value) => _clearance(row, item, value),
                      itemBuilder: (_) => const [
                        PopupMenuItem(value: 'CLEARED', child: Text('Mark cleared')),
                        PopupMenuItem(value: 'BLOCKED', child: Text('Mark blocked')),
                        PopupMenuItem(value: 'WAIVED', child: Text('Waive with reason')),
                      ],
                    )
                  : null,
            )),
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Wrap(spacing: 8, runSpacing: 8, children: _exitActions(row)),
        ),
      ],
    );
  }

  List<Widget> _exitActions(Map<String, dynamic> row) {
    final status = (row['status'] ?? '').toString();
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return const [];
    final buttons = <Widget>[];
    void add(String label, String action, {Map<String, dynamic> extra = const {}}) {
      buttons.add(OutlinedButton(onPressed: _busy ? null : () => _exitAction(id, action, extra: extra), child: Text(label)));
    }
    if (_canExitManage && status == 'DRAFT') add('START NOTICE', 'START_NOTICE');
    if (_canExitManage && const {'DRAFT', 'NOTICE'}.contains(status)) add('START CLEARANCE', 'START_CLEARANCE');
    if (_canExitManage && const {'CLEARANCE', 'PENDING_APPROVAL'}.contains(status) && row['final_settlement_ready'] != true) {
      add('SETTLEMENT READY', 'SET_FINAL_SETTLEMENT_READY', extra: const {'ready': true});
    }
    if (_canExitManage && status == 'CLEARANCE') add('SUBMIT APPROVAL', 'SUBMIT_APPROVAL');
    if (_canApprove && status == 'PENDING_APPROVAL') add('APPROVE EXIT', 'APPROVE');
    if (_canApprove && status == 'APPROVED') add('SEPARATE', 'SEPARATE');
    if (_canApprove && !const {'APPROVED', 'SEPARATED', 'CANCELLED'}.contains(status)) add('CANCEL', 'CANCEL');
    if (_canManage && status == 'SEPARATED') {
      buttons.add(TextButton(onPressed: () => _postSeparationLetter(id, 'EXPERIENCE'), child: const Text('EXPERIENCE LETTER')));
      buttons.add(TextButton(onPressed: () => _postSeparationLetter(id, 'RELIEVING'), child: const Text('RELIEVING LETTER')));
    }
    return buttons;
  }

  Widget _timelinePanel() {
    final timeline = _timeline;
    if (timeline == null) {
      return _empty('Select an employee or lifecycle row to open the unified timeline.');
    }
    final employee = _employee(timeline['employee_id']);
    final items = (timeline['timeline'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(employee?['name']?.toString() ?? timeline['employee_code']?.toString() ?? 'Employee timeline', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            Text('${timeline['employment_status'] ?? '-'} • ${timeline['hr_stage'] ?? '-'}'),
            const Divider(),
            if (items.isEmpty) const Text('No lifecycle timeline events yet.'),
            ...items.take(60).map((row) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(_timelineIcon('${row['kind'] ?? ''}')),
                  title: Text('${row['title'] ?? '-'}'),
                  subtitle: Text('${row['date'] ?? '-'}${(row['note'] ?? '').toString().isEmpty ? '' : '\n${row['note']}'}'),
                  trailing: Text('${row['status'] ?? '-'}', textAlign: TextAlign.end),
                )),
          ],
        ),
      ),
    );
  }

  IconData _timelineIcon(String kind) {
    switch (kind) {
      case 'JOINING': return Icons.person_add_alt_1;
      case 'BGV': return Icons.verified_user_outlined;
      case 'CAREER': return Icons.trending_up;
      case 'EXIT': return Icons.logout;
      case 'ISSUED_LETTER':
      case 'LETTER_WORKFLOW': return Icons.description_outlined;
      default: return Icons.timeline;
    }
  }

  Widget _statusChip(String value) => Chip(
        visualDensity: VisualDensity.compact,
        label: Text(value.replaceAll('_', ' '), overflow: TextOverflow.ellipsis),
      );

  Widget _empty(String message) => Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(children: [const Icon(Icons.inbox_outlined), const SizedBox(width: 10), Expanded(child: Text(message))]),
        ),
      );

  Future<void> _workflow(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    Map<String, dynamic> assessment = const {};
    String reason = '';
    if (action == 'MANAGER_REVIEW' || action == 'HR_REVIEW') {
      final note = await _textDialog('${action == 'MANAGER_REVIEW' ? 'Manager' : 'HR'} assessment', required: true);
      if (note == null) return;
      assessment = {'note': note};
    }
    if (action == 'REJECT') {
      final value = await _textDialog('Rejection reason', required: true);
      if (value == null) return;
      reason = value;
    }
    await _run(() => _service.lifecycleWorkflow(id, action, reason: reason, assessment: assessment));
  }

  Future<void> _showCreateAction({int? employeeId, String? presetType}) async {
    var selected = employeeId ?? _selectedEmployeeId ?? (_directory.isNotEmpty ? (_directory.first['id'] as num?)?.toInt() : null);
    var type = presetType ?? 'PROBATION_REVIEW';
    final reason = TextEditingController();
    final designation = TextEditingController();
    final department = TextEditingController();
    final grade = TextEditingController();
    final salary = TextEditingController();
    final location = TextEditingController();
    final extensionMonths = TextEditingController(text: '1');
    final date = TextEditingController(text: DateTime.now().toIso8601String().split('T').first);
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setLocal) {
        return AlertDialog(
          title: const Text('Create lifecycle action'),
          content: SizedBox(
            width: 620,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                DropdownButtonFormField<int>(
                  initialValue: selected,
                  decoration: const InputDecoration(labelText: 'Employee'),
                  items: _directory.map((row) => DropdownMenuItem(value: (row['id'] as num).toInt(), child: Text('${row['name'] ?? '-'} • ${row['employee_id'] ?? '-'}'))).toList(),
                  onChanged: (value) => setLocal(() => selected = value),
                ),
                DropdownButtonFormField<String>(
                  initialValue: type,
                  decoration: const InputDecoration(labelText: 'Action type'),
                  items: const ['PROBATION_REVIEW', 'PROBATION_EXTENSION', 'CONFIRMATION', 'PROMOTION', 'INCREMENT', 'TRANSFER']
                      .map((v) => DropdownMenuItem(value: v, child: Text(v.replaceAll('_', ' '))))
                      .toList(),
                  onChanged: (value) => setLocal(() => type = value ?? type),
                ),
                TextField(controller: date, decoration: const InputDecoration(labelText: 'Effective date • YYYY-MM-DD')),
                TextField(controller: reason, decoration: InputDecoration(labelText: const {'PROBATION_EXTENSION', 'PROMOTION', 'INCREMENT', 'TRANSFER'}.contains(type) ? 'Reason • required' : 'Reason / note')),
                if (type == 'PROBATION_EXTENSION') TextField(controller: extensionMonths, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Extension months')),
                if (type == 'PROMOTION') ...[
                  TextField(controller: designation, decoration: const InputDecoration(labelText: 'New designation')),
                  TextField(controller: department, decoration: const InputDecoration(labelText: 'New department')),
                  TextField(controller: grade, decoration: const InputDecoration(labelText: 'New grade')),
                ],
                if (type == 'INCREMENT') TextField(controller: salary, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'New salary')),
                if (type == 'TRANSFER') ...[
                  TextField(controller: department, decoration: const InputDecoration(labelText: 'New department')),
                  TextField(controller: location, decoration: const InputDecoration(labelText: 'Work location')),
                ],
              ]),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: selected == null ? null : () => Navigator.pop(context, true), child: const Text('CREATE')),
          ],
        );
      }),
    );
    if (submitted != true || selected == null) return;
    final proposed = <String, dynamic>{};
    if (type == 'PROBATION_EXTENSION') proposed['extension_months'] = int.tryParse(extensionMonths.text.trim()) ?? 0;
    if (designation.text.trim().isNotEmpty) proposed['designation'] = designation.text.trim();
    if (department.text.trim().isNotEmpty) proposed['department'] = department.text.trim();
    if (grade.text.trim().isNotEmpty) proposed['grade'] = grade.text.trim();
    if (salary.text.trim().isNotEmpty) proposed['salary'] = salary.text.trim();
    if (location.text.trim().isNotEmpty) proposed['work_location'] = location.text.trim();
    await _run(() => _service.createLifecycleAction({
          'employee_id': selected,
          'action_type': type,
          'effective_date': date.text.trim(),
          'reason': reason.text.trim(),
          'proposed_changes': proposed,
        }));
  }

  Future<void> _showCreateExit() async {
    var selected = _selectedEmployeeId ?? (_directory.isNotEmpty ? (_directory.first['id'] as num?)?.toInt() : null);
    var type = 'RESIGNATION';
    final resignation = TextEditingController(text: DateTime.now().toIso8601String().split('T').first);
    final lwd = TextEditingController(text: DateTime.now().add(const Duration(days: 30)).toIso8601String().split('T').first);
    final notice = TextEditingController(text: '30');
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setLocal) => AlertDialog(
            title: const Text('Start exit case'),
            content: SizedBox(
              width: 560,
              child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
                DropdownButtonFormField<int>(
                  initialValue: selected,
                  decoration: const InputDecoration(labelText: 'Employee'),
                  items: _directory.where((row) => row['is_active'] != false).map((row) => DropdownMenuItem(value: (row['id'] as num).toInt(), child: Text('${row['name'] ?? '-'} • ${row['employee_id'] ?? '-'}'))).toList(),
                  onChanged: (value) => setLocal(() => selected = value),
                ),
                DropdownButtonFormField<String>(
                  initialValue: type,
                  decoration: const InputDecoration(labelText: 'Separation type'),
                  items: const ['RESIGNATION', 'TERMINATION', 'RETIREMENT', 'ABSCONDING', 'CONTRACT_COMPLETION'].map((v) => DropdownMenuItem(value: v, child: Text(v.replaceAll('_', ' ')))).toList(),
                  onChanged: (value) => setLocal(() => type = value ?? type),
                ),
                if (type == 'RESIGNATION') TextField(controller: resignation, decoration: const InputDecoration(labelText: 'Resignation date • YYYY-MM-DD')),
                TextField(controller: lwd, decoration: const InputDecoration(labelText: 'Proposed last working date • YYYY-MM-DD')),
                TextField(controller: notice, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Notice days')),
                TextField(controller: reason, minLines: 2, maxLines: 4, decoration: const InputDecoration(labelText: 'Exit reason • required')),
              ])),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
              FilledButton(onPressed: selected == null ? null : () => Navigator.pop(context, true), child: const Text('CREATE EXIT')),
            ],
          )),
    );
    if (ok != true || selected == null) return;
    await _run(() => _service.createExitCase({
          'employee_id': selected,
          'separation_type': type,
          if (type == 'RESIGNATION') 'resignation_date': resignation.text.trim(),
          'notice_days': int.tryParse(notice.text.trim()) ?? 0,
          'proposed_last_working_date': lwd.text.trim(),
          'reason': reason.text.trim(),
        }));
  }

  Future<void> _exitAction(int caseId, String action, {Map<String, dynamic> extra = const {}}) async {
    var reason = '';
    if (action == 'CANCEL') {
      final value = await _textDialog('Cancellation reason', required: true);
      if (value == null) return;
      reason = value;
    }
    if (action == 'SUBMIT_APPROVAL') {
      final value = await _textDialog('Approved last working date • optional YYYY-MM-DD');
      if (value == null) return;
      if (value.trim().isNotEmpty) extra = {...extra, 'approved_last_working_date': value.trim()};
    }
    await _run(() => _service.exitCaseAction(caseId, action, reason: reason, extra: extra));
  }

  Future<void> _clearance(Map<String, dynamic> exit, Map<String, dynamic> clearance, String status) async {
    final caseId = (exit['id'] as num?)?.toInt();
    final clearanceId = (clearance['id'] as num?)?.toInt();
    if (caseId == null || clearanceId == null) return;
    String note = '';
    String waiver = '';
    if (status == 'WAIVED') {
      final value = await _textDialog('Waiver reason', required: true);
      if (value == null) return;
      waiver = value;
    } else {
      final value = await _textDialog(status == 'BLOCKED' ? 'Blocking note' : 'Clearance note');
      if (value == null) return;
      note = value;
    }
    await _run(() => _service.exitClearanceAction(caseId, clearanceId, status: status, note: note, waiverReason: waiver));
  }

  Future<void> _postSeparationLetter(int caseId, String type) =>
      _run(() => _service.createPostSeparationLetter(caseId, type));

  Future<String?> _textDialog(String title, {bool required = false}) async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(controller: controller, autofocus: true, minLines: 2, maxLines: 5, decoration: const InputDecoration(border: OutlineInputBorder())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          FilledButton(onPressed: () {
            final value = controller.text.trim();
            if (required && value.isEmpty) return;
            Navigator.pop(context, value);
          }, child: const Text('CONTINUE')),
        ],
      ),
    );
  }

  Future<void> _run(Future<dynamic> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Lifecycle workflow updated.')));
      await _load();
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))));
  }
}
