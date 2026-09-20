import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/hrms_service.dart';
import '../../utils/search_utils.dart';

class HrmsScreen extends StatefulWidget {
  const HrmsScreen({super.key});
  @override
  State<HrmsScreen> createState() => _HrmsScreenState();
}

class _HrmsScreenState extends State<HrmsScreen> {
  final _service = HrmsService();
  List<Map<String, dynamic>> _leaves = [], _payroll = [], _holidays = [];
  List<Map<String, dynamic>> _penalties = [], _penaltyEmployees = [];
  List<Map<String, dynamic>> _performanceReviews = [], _documents = [];
  Map<String, dynamic> _dashboard = {};
  bool _loading = true;
  String _role = '';
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month - 1);
  final _searchController = TextEditingController();
  String _query = '';
  String _leaveStatus = 'ALL';

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

  bool _matchesRecord(Map<String, dynamic> row) => matchesAllSearchTerms(
    _query,
    row.entries.map((e) => '${e.key} ${e.value}'),
  );

  List<Map<String, dynamic>> get _filteredPayroll =>
      _payroll.where(_matchesRecord).toList();

  List<Map<String, dynamic>> get _filteredLeaves => _leaves.where((row) {
    if (_leaveStatus != 'ALL' &&
        (row['status'] ?? '').toString().toUpperCase() != _leaveStatus) {
      return false;
    }
    return _matchesRecord(row);
  }).toList();

  List<Map<String, dynamic>> get _filteredPenalties =>
      _penalties.where(_matchesRecord).toList();

  String get _monthValue =>
      '${_month.year}-${_month.month.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _role = (await ApiService.getRole() ?? '').toUpperCase();
      final values = await Future.wait<dynamic>([
        _service.leaves(),
        _service.payroll(month: _role == 'ADMIN' ? _monthValue : null),
        _service.dashboard(),
        _service.holidays(year: DateTime.now().year),
        _service.penalties(),
        _service.performanceReviews(),
        _service.documents(),
      ]);
      if (mounted) {
        setState(() {
          _leaves = values[0];
          _payroll = values[1];
          _dashboard = Map<String, dynamic>.from(values[2] as Map);
          _holidays = List<Map<String, dynamic>>.from(values[3] as List);
          final penaltyData = Map<String, dynamic>.from(values[4] as Map);
          _penalties = List<Map<String, dynamic>>.from(
            penaltyData['penalties'] as List? ?? const [],
          );
          _penaltyEmployees = List<Map<String, dynamic>>.from(
            penaltyData['employees'] as List? ?? const [],
          );
          _performanceReviews = List<Map<String, dynamic>>.from(
            values[5] as List,
          );
          _documents = List<Map<String, dynamic>>.from(values[6] as List);
        });
      }
    } catch (error) {
      if (mounted) {
        _show(error.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _requestLeave() async {
    DateTime selectedDate = DateTime.now().add(const Duration(days: 1));
    String type = 'FULL_DAY', reason = '';
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Request leave'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField(
                  initialValue: type,
                  decoration: const InputDecoration(labelText: 'Leave type'),
                  items: const [
                    DropdownMenuItem(
                      value: 'FULL_DAY',
                      child: Text('Full day'),
                    ),
                    DropdownMenuItem(
                      value: 'HALF_DAY',
                      child: Text('Half day'),
                    ),
                  ],
                  onChanged: (value) => setLocal(() => type = value!),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Monthly allowance: 2 full-day dates and 2 half-day dates. '
                  'Select one date for this request.',
                  style: TextStyle(fontSize: 12, color: Color(0xFF687386)),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.event_outlined),
                  title: const Text('Leave date'),
                  subtitle: Text(
                    '${selectedDate.day}/${selectedDate.month}/${selectedDate.year}',
                  ),
                  trailing: const Icon(Icons.calendar_month),
                  onTap: () async {
                    final value = await showDatePicker(
                      context: context,
                      initialDate: selectedDate,
                      firstDate: DateTime.now().add(const Duration(days: 1)),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                      helpText: 'CHOOSE LEAVE DATE',
                      confirmText: 'USE THIS DATE',
                    );
                    if (value != null) {
                      setLocal(() => selectedDate = value);
                    }
                  },
                ),
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Reason',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 3,
                  onChanged: (value) => reason = value,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('CANCEL'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('SUBMIT'),
            ),
          ],
        ),
      ),
    );
    if (submit != true) return;
    try {
      await _service.requestLeave(
        type: type,
        start: selectedDate,
        end: selectedDate,
        reason: reason,
      );
      _show('Leave request submitted for approval.');
      await _load();
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _createPenalty() async {
    if (_penaltyEmployees.isEmpty) {
      _show('No active employee is available.');
      return;
    }
    int employeeId = (_penaltyEmployees.first['id'] as num).toInt();
    DateTime penaltyDate = DateTime.now();
    String amount = '', reason = '';
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Create employee penalty'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<int>(
                  initialValue: employeeId,
                  decoration: const InputDecoration(labelText: 'Employee'),
                  items: _penaltyEmployees
                      .map(
                        (row) => DropdownMenuItem(
                          value: (row['id'] as num).toInt(),
                          child: Text('${row['name']} (${row['employee_id']})'),
                        ),
                      )
                      .toList(),
                  onChanged: (value) =>
                      setLocal(() => employeeId = value ?? employeeId),
                ),
                TextField(
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Penalty amount',
                  ),
                  onChanged: (value) => amount = value,
                ),
                TextField(
                  maxLines: 3,
                  decoration: const InputDecoration(
                    labelText: 'Reason / audit note',
                  ),
                  onChanged: (value) => reason = value,
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Penalty date'),
                  subtitle: Text(
                    '${penaltyDate.day}/${penaltyDate.month}/${penaltyDate.year}',
                  ),
                  trailing: const Icon(Icons.calendar_month),
                  onTap: () async {
                    final value = await showDatePicker(
                      context: context,
                      initialDate: penaltyDate,
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (value != null) setLocal(() => penaltyDate = value);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('CANCEL'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('SAVE DRAFT'),
            ),
          ],
        ),
      ),
    );
    final parsedAmount = double.tryParse(amount.trim());
    if (submit != true) return;
    if (parsedAmount == null || parsedAmount <= 0 || reason.trim().isEmpty) {
      _show('Enter a valid amount and reason.');
      return;
    }
    try {
      await _service.createPenalty(
        employeeId: employeeId,
        date: penaltyDate,
        amount: parsedAmount,
        reason: reason.trim(),
      );
      _show('Penalty draft created. Approve it after verification.');
      await _load();
    } catch (error) {
      _show(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _penaltyAction(Map<String, dynamic> row, String action) async {
    try {
      await _service.penaltyAction((row['id'] as num).toInt(), action);
      _show(
        action == 'APPROVE'
            ? 'Penalty approved for payroll.'
            : 'Penalty cancelled.',
      );
      await _load();
    } catch (error) {
      _show(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _payrollAction(
    Map<String, dynamic> row,
    String action,
  ) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    try {
      await _service.payrollAction(id, action);
      _show(
        action == 'APPROVE'
            ? 'Payroll approved successfully.'
            : 'Payroll marked as paid.',
      );
      await _load();
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _generate() async {
    try {
      final count = await _service.generatePayroll(_monthValue);
      _show('$count payroll drafts generated.');
      await _load();
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _download() async {
    try {
      final path = await _service.downloadPayroll(_monthValue);
      _show('Salary register saved: $path');
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  void _show(String value) {
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(value)));
    }
  }

  String _money(dynamic value) =>
      '₹${double.tryParse(value.toString())?.toStringAsFixed(0) ?? '0'}';

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Employee HRMS')),
    floatingActionButton: _role == 'ADMIN'
        ? null
        : FloatingActionButton.extended(
            onPressed: _requestLeave,
            icon: const Icon(Icons.add),
            label: const Text('REQUEST LEAVE'),
          ),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_role == 'ADMIN')
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text(
                            'Monthly payroll control',
                            style: TextStyle(
                              fontWeight: FontWeight.w900,
                              fontSize: 17,
                            ),
                          ),
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(Icons.calendar_month),
                            title: Text(_monthValue),
                            trailing: const Icon(Icons.edit_calendar),
                            onTap: () async {
                              final value = await showDatePicker(
                                context: context,
                                initialDate: _month,
                                firstDate: DateTime(2020),
                                lastDate: DateTime.now(),
                              );
                              if (value != null) {
                                setState(
                                  () => _month = DateTime(
                                    value.year,
                                    value.month,
                                  ),
                                );
                                await _load();
                              }
                            },
                          ),
                          Row(
                            children: [
                              Expanded(
                                child: FilledButton.icon(
                                  onPressed: _generate,
                                  icon: const Icon(Icons.calculate_outlined),
                                  label: const Text('GENERATE'),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: _download,
                                  icon: const Icon(Icons.download),
                                  label: const Text('EXCEL'),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                if (_role != 'ADMIN') _employeeOverview(),
                if (_role == 'ADMIN') _adminReportOverview(),
                const SizedBox(height: 14),
                TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    hintText: 'Search employee, ID, month, status, reason...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty ? null : IconButton(
                      onPressed: () { _searchController.clear(); setState(() => _query = ''); },
                      icon: const Icon(Icons.clear),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                _performanceSection(),
                const SizedBox(height: 14),
                _documentComplianceSection(),
                const SizedBox(height: 14),
                _holidaySection(),
                const SizedBox(height: 14),
                _penaltySection(),
                const SizedBox(height: 14),
                Text(
                  'Salary & incentives',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                if (_filteredPayroll.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(20),
                      child: Text('No payroll record available.'),
                    ),
                  ),
                ..._filteredPayroll.map(
                  (row) => Card(
                    child: ExpansionTile(
                      leading: const CircleAvatar(
                        child: Icon(Icons.receipt_long),
                      ),
                      title: Text(
                        _role == 'ADMIN'
                            ? (row['employee_name']?.toString() ?? '')
                            : '${row['month']} Payslip',
                      ),
                      subtitle: Text(
                        'Net ${_money(row['net_salary'])} • ${row['status']}',
                      ),
                      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                      children: [
                        _line('Base salary', _money(row['base_salary'])),
                        _line(
                          'Late penalty',
                          '- ${_money(row['late_penalty'])}',
                        ),
                        _line(
                          'Half-day deduction',
                          '- ${_money(row['half_day_deduction'])}',
                        ),
                        _line(
                          'Absence deduction',
                          '- ${_money(row['absence_deduction'])}',
                        ),
                        _line(
                          'Manual approved penalties',
                          '- ${_money(row['other_deductions'])}',
                        ),
                        _line(
                          'Overtime (${row['overtime_hours']} hr)',
                          '+ ${_money(row['overtime_amount'])}',
                        ),
                        _line(
                          'Rent incentive',
                          '+ ${_money(row['rent_incentive'])}',
                        ),
                        _line(
                          'Sale incentive',
                          '+ ${_money(row['sale_incentive'])}',
                        ),
                        const Divider(),
                        _line(
                          'Net salary',
                          _money(row['net_salary']),
                          bold: true,
                        ),
                        if (_role == 'ADMIN' &&
                            row['status'] == 'DRAFT') ...[
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.icon(
                              onPressed: () => _payrollAction(row, 'APPROVE'),
                              icon: const Icon(Icons.verified_outlined),
                              label: const Text('APPROVE PAYROLL'),
                            ),
                          ),
                        ],
                        if (_role == 'ADMIN' &&
                            row['status'] == 'APPROVED') ...[
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.icon(
                              onPressed: () => _payrollAction(row, 'MARK_PAID'),
                              icon: const Icon(Icons.payments_outlined),
                              label: const Text('MARK AS PAID'),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    Text(
                      'Leave management',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const Spacer(),
                    if (_role != 'ADMIN')
                      TextButton.icon(
                        onPressed: _requestLeave,
                        icon: const Icon(Icons.add),
                        label: const Text('REQUEST'),
                      ),
                  ],
                ),
                DropdownButtonFormField<String>(
                  initialValue: _leaveStatus,
                  decoration: const InputDecoration(labelText: 'Leave status'),
                  items: const [
                    DropdownMenuItem(value: 'ALL', child: Text('All leave requests')),
                    DropdownMenuItem(value: 'PENDING', child: Text('Pending')),
                    DropdownMenuItem(value: 'APPROVED', child: Text('Approved')),
                    DropdownMenuItem(value: 'REJECTED', child: Text('Rejected')),
                  ],
                  onChanged: (v) => setState(() => _leaveStatus = v ?? 'ALL'),
                ),
                const SizedBox(height: 8),
                Align(alignment: Alignment.centerLeft, child: Text('${_filteredLeaves.length} of ${_leaves.length} leave requests')),
                ..._filteredLeaves.map(
                  (row) => Card(
                    child: Column(
                      children: [
                        ListTile(
                          leading: Icon(
                            row['type'] == 'HALF_DAY'
                                ? Icons.timelapse
                                : Icons.event,
                          ),
                          title: Text(
                            _role == 'ADMIN' ||
                                    _role == 'MANAGER' ||
                                    _role == 'OFFICE'
                                ? '${row['employee_name']} • ${row['type']}'
                                : row['type'].toString().replaceAll('_', ' '),
                          ),
                          subtitle: Text(
                            '${row['start_date']} to ${row['end_date']}\n${row['reason']}'
                            '${(row['review_note']?.toString() ?? '').isEmpty ? '' : '\nReview: ${row['review_note']}'}',
                          ),
                          isThreeLine: true,
                          trailing: Chip(label: Text(row['status'].toString())),
                        ),
                        if (row['status'] == 'PENDING' &&
                            (_role == 'ADMIN' ||
                                _role == 'MANAGER' ||
                                _role == 'OFFICE')) ...[
                          const Divider(height: 1),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                            child: Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: () =>
                                        _reviewLeave(row, 'REJECTED'),
                                    icon: const Icon(Icons.close),
                                    label: const Text('REJECT'),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: () =>
                                        _reviewLeave(row, 'APPROVED'),
                                    icon: const Icon(Icons.check),
                                    label: const Text('APPROVE'),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 80),
              ],
            ),
          ),
  );

  Map<String, dynamic> _map(String key) =>
      Map<String, dynamic>.from(_dashboard[key] as Map? ?? const {});

  Widget _penaltySection() => _sectionCard(
    icon: Icons.gavel_outlined,
    title: 'Employee penalty register',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_filteredPenalties.isEmpty)
          const Text(
            'No manual penalties recorded.',
            style: TextStyle(color: Color(0xFF687386)),
          )
        else
          ..._filteredPenalties
              .take(50)
              .map(
                (row) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: Column(
                    children: [
                      ListTile(
                        title: Text(
                          '${row['employee_name']} • ${_money(row['amount'])}',
                        ),
                        subtitle: Text(
                          '${row['penalty_date']}\n${row['reason']}',
                        ),
                        isThreeLine: true,
                        trailing: Chip(label: Text(row['status'].toString())),
                      ),
                      if (_role == 'ADMIN' && row['status'] == 'DRAFT')
                        Padding(
                          padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                          child: Row(
                            children: [
                              Expanded(
                                child: OutlinedButton(
                                  onPressed: () =>
                                      _penaltyAction(row, 'CANCEL'),
                                  child: const Text('CANCEL'),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: FilledButton(
                                  onPressed: () =>
                                      _penaltyAction(row, 'APPROVE'),
                                  child: const Text('APPROVE'),
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
        if (_role == 'ADMIN') ...[
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: _createPenalty,
            icon: const Icon(Icons.add),
            label: const Text('CREATE PENALTY DRAFT'),
          ),
        ],
      ],
    ),
  );
  Widget _adminReportOverview() {
    final workforce = _map('workforce');
    final approvals = _map('approvals');
    final payroll = _map('payroll');
    final attendance = _map('attendance');
    final designationMix = Map<String, dynamic>.from(
      workforce['designation_mix'] as Map? ?? const {},
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0B2447), Color(0xFF19376D)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'CORPORATE HRMS',
                style: TextStyle(
                  color: Color(0xFFB7D7FF),
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.4,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'People Operations Command Center',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 23,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Live workforce, approvals, payroll and policy overview • $_monthValue',
                style: const TextStyle(color: Colors.white70),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: _heroMetric(
                      'Active workforce',
                      '${workforce['active_employees'] ?? 0}',
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _heroMetric(
                      'Present today',
                      '${workforce['present_today'] ?? 0}',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Executive snapshot',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.55,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          children: [
            _metricCard(
              Icons.pending_actions_rounded,
              'Pending leave approvals',
              '${approvals['pending_leaves'] ?? 0}',
              const Color(0xFFE17819),
            ),
            _metricCard(
              Icons.payments_outlined,
              'Payroll drafts',
              '${approvals['draft_payroll'] ?? 0}',
              const Color(0xFF7B4BC4),
            ),
            _metricCard(
              Icons.account_balance_wallet_outlined,
              'Net salary',
              _money(payroll['net_salary']),
              const Color(0xFF0878D8),
            ),
            _metricCard(
              Icons.more_time_rounded,
              'Overtime payout',
              _money(payroll['overtime_amount']),
              const Color(0xFF0A8F70),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _sectionCard(
          icon: Icons.groups_2_outlined,
          title: 'Workforce structure',
          child: designationMix.isEmpty
              ? const Text('No active workforce data available.')
              : Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: designationMix.entries
                      .map(
                        (entry) => Chip(
                          avatar: const Icon(Icons.badge_outlined, size: 18),
                          label: Text('${entry.key}: ${entry.value}'),
                        ),
                      )
                      .toList(),
                ),
        ),
        const SizedBox(height: 12),
        _sectionCard(
          icon: Icons.assignment_turned_in_outlined,
          title: 'Approval queue',
          child: Column(
            children: [
              _line(
                'Leave requests awaiting review',
                '${approvals['pending_leaves'] ?? 0}',
                bold: true,
              ),
              _line(
                'Payroll awaiting approval',
                '${approvals['draft_payroll'] ?? 0}',
              ),
              _line(
                'Approved payroll awaiting payment',
                '${approvals['approved_payroll'] ?? 0}',
              ),
              _line(
                'Penalty drafts awaiting approval',
                '${approvals['draft_penalties'] ?? 0}',
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _sectionCard(
          icon: Icons.insights_outlined,
          title: 'Attendance & cost controls',
          child: Column(
            children: [
              _line(
                'Not checked-in / absent today',
                '${workforce['absent_or_not_checked_in'] ?? 0}',
              ),
              _line(
                'Half-days this month',
                '${attendance['half_days'] ?? 0}',
              ),
              _line(
                'Absences this month',
                '${attendance['absences'] ?? 0}',
              ),
              _line(
                'Pending selfie reviews',
                '${attendance['pending_selfie_reviews'] ?? 0}',
              ),
              _line(
                'Performance incentives',
                _money(payroll['incentives']),
              ),
              _line(
                'Approved penalties',
                _money(payroll['approved_penalties']),
                bold: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _holidaySection() => _sectionCard(
    icon: Icons.celebration_outlined,
    title: 'Office holiday calendar',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_holidays.isEmpty)
          const Text(
            'No office holidays declared for this year.',
            style: TextStyle(color: Color(0xFF687386)),
          )
        else
          ..._holidays
              .take(12)
              .map(
                (row) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const CircleAvatar(
                    child: Icon(Icons.event_available),
                  ),
                  title: Text(
                    row['name']?.toString() ?? 'Office holiday',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    '${row['date']}${(row['description']?.toString() ?? '').isEmpty ? '' : '\n${row['description']}'}',
                  ),
                  trailing: row['is_paid'] == true
                      ? const Chip(label: Text('PAID'))
                      : null,
                ),
              ),
        if (_role == 'ADMIN' || _role == 'OFFICE') ...[
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _declareHoliday,
            icon: const Icon(Icons.add),
            label: const Text('DECLARE HOLIDAY'),
          ),
        ],
      ],
    ),
  );

  Widget _performanceSection() => _sectionCard(
    icon: Icons.insights_rounded,
    title: 'Performance & Appraisal',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_performanceReviews.isEmpty)
          const Text(
            'No performance review available yet.',
            style: TextStyle(color: Color(0xFF687386)),
          )
        else
          ..._performanceReviews.take(12).map(
            (row) => Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: Column(
                children: [
                  ListTile(
                    leading: const CircleAvatar(
                      child: Icon(Icons.assessment_outlined),
                    ),
                    title: Text(
                      _role == 'ADMIN' || _role == 'MANAGER' || _role == 'OFFICE'
                          ? '${row['employee_name']} • Score ${row['overall_score']}'
                          : 'Overall score ${row['overall_score']}',
                    ),
                    subtitle: Text(
                      '${row['period_start']} to ${row['period_end']}\n'
                      'Goals ${row['goals_score']} • Attendance ${row['attendance_score']} • '
                      'Service ${row['service_quality_score']}\n'
                      'Customer ${row['customer_score']} • Sales ${row['sales_score']}'
                      '${(row['improvement_plan']?.toString() ?? '').isEmpty ? '' : '\nPlan: ${row['improvement_plan']}'}',
                    ),
                    isThreeLine: true,
                    trailing: Chip(label: Text(row['status'].toString())),
                  ),
                  if (_role != 'ADMIN' &&
                      _role != 'MANAGER' &&
                      _role != 'OFFICE' &&
                      row['status'] == 'FINAL')
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                      child: SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: () => _acknowledgePerformance(row),
                          icon: const Icon(Icons.check_circle_outline),
                          label: const Text('ACKNOWLEDGE REVIEW'),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
      ],
    ),
  );

  Widget _documentComplianceSection() => _sectionCard(
    icon: Icons.folder_copy_outlined,
    title: 'Employee Document Compliance',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_documents.isEmpty)
          const Text(
            'No employee document records available.',
            style: TextStyle(color: Color(0xFF687386)),
          )
        else
          ..._documents.take(20).map(
            (row) {
              final state = row['expiry_state']?.toString() ?? 'VALID';
              final warning =
                  state == 'EXPIRED' || state == 'EXPIRING_SOON' || row['verified'] != true;
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  warning ? Icons.warning_amber_rounded : Icons.verified_outlined,
                ),
                title: Text(
                  _role == 'ADMIN' || _role == 'MANAGER' || _role == 'OFFICE'
                      ? '${row['employee_name']} • ${row['document_type']}'
                      : row['document_type'].toString(),
                ),
                subtitle: Text(
                  '${row['document_number'] ?? ''}'
                  '${row['expiry_date'] == null ? '' : ' • expires ${row['expiry_date']}'}',
                ),
                trailing: Chip(
                  label: Text(
                    row['verified'] == true ? state : 'UNVERIFIED',
                  ),
                ),
              );
            },
          ),
      ],
    ),
  );

  Widget _employeeOverview() {
    final employee = _map('employee');
    final attendance = _map('attendance');
    final leave = _map('leave_balance');
    final earnings = _map('earnings');
    final policy = _map('policy');
    final latest = _dashboard['latest_payroll'] is Map
        ? Map<String, dynamic>.from(_dashboard['latest_payroll'] as Map)
        : <String, dynamic>{};
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF07315E), Color(0xFF0878D8)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'MY HR DESK',
                style: TextStyle(
                  color: Color(0xFFBFE3FF),
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                employee['name']?.toString() ?? 'Employee',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Text(
                '${employee['employee_id'] ?? ''} • ${employee['designation'] ?? ''}',
                style: const TextStyle(color: Colors.white70),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: _heroMetric(
                      'Monthly salary',
                      _money(earnings['monthly_salary']),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _heroMetric(
                      'Latest payslip',
                      latest.isEmpty
                          ? 'Not generated'
                          : '${_money(latest['net_salary'])} • ${latest['status']}',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'This month',
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.55,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          children: [
            _metricCard(
              Icons.fact_check_outlined,
              'Present',
              '${attendance['present_days'] ?? 0} days',
              const Color(0xFF0878D8),
            ),
            _metricCard(
              Icons.schedule_outlined,
              'Work hours',
              '${attendance['total_hours'] ?? 0} hrs',
              const Color(0xFF0A8F70),
            ),
            _metricCard(
              Icons.more_time,
              'Overtime',
              '${attendance['overtime_hours'] ?? 0} hrs',
              const Color(0xFF7B4BC4),
            ),
            _metricCard(
              Icons.warning_amber_rounded,
              'Late / half day',
              '${attendance['late_days'] ?? 0} / ${attendance['half_days'] ?? 0}',
              const Color(0xFFE17819),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _sectionCard(
          icon: Icons.event_available_outlined,
          title: 'Leave balance',
          child: Column(
            children: [
              _progressLine(
                'Paid full-day leave',
                leave['paid_full_remaining'],
                leave['paid_full_allowed'],
              ),
              const SizedBox(height: 12),
              _progressLine(
                'Paid half-day leave',
                leave['paid_half_remaining'],
                leave['paid_half_allowed'],
              ),
              if ((leave['pending_requests'] as num? ?? 0) > 0) ...[
                const Divider(height: 24),
                Row(
                  children: [
                    const Icon(
                      Icons.hourglass_top,
                      size: 18,
                      color: Color(0xFFE17819),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${leave['pending_requests']} request awaiting approval',
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        _sectionCard(
          icon: Icons.workspace_premium_outlined,
          title: 'Performance earnings',
          child: Column(
            children: [
              _line(
                'New rental installations',
                '${earnings['new_rent_installations'] ?? 0}',
              ),
              _line(
                'Future monthly rent incentive',
                '+ ${_money(earnings['future_rent_monthly_incentive'])}',
              ),
              _line('New RO sales', '${earnings['new_sales'] ?? 0}'),
              _line(
                'Next salary sale incentive',
                '+ ${_money(earnings['next_salary_sale_incentive'])}',
                bold: true,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _sectionCard(
          icon: Icons.policy_outlined,
          title: 'Your work policy',
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(label: Text('Office ${policy['office_start_time'] ?? ''}')),
              Chip(
                label: Text('${policy['daily_work_hours'] ?? 8} working hours'),
              ),
              Chip(
                label: Text('Late penalty ${_money(policy['late_penalty'])}'),
              ),
              Chip(
                label: Text(
                  '${policy['leave_notice_days'] ?? 1}-day leave notice',
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _acknowledgePerformance(Map<String, dynamic> row) async {
    try {
      await _service.performanceAction((row['id'] as num).toInt(), 'ACKNOWLEDGE');
      _show('Performance review acknowledged.');
      await _load();
    } catch (error) {
      _show(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _declareHoliday() async {
    DateTime selected = DateTime.now().add(const Duration(days: 1));
    String name = '', description = '';
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Declare office holiday'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.calendar_month),
                  title: const Text('Holiday date'),
                  subtitle: Text(
                    '${selected.day}/${selected.month}/${selected.year}',
                  ),
                  onTap: () async {
                    final value = await showDatePicker(
                      context: context,
                      initialDate: selected,
                      firstDate: DateTime.now(),
                      lastDate: DateTime.now().add(const Duration(days: 730)),
                    );
                    if (value != null) setLocal(() => selected = value);
                  },
                ),
                TextField(
                  decoration: const InputDecoration(labelText: 'Holiday name'),
                  onChanged: (value) => name = value,
                ),
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Description (optional)',
                  ),
                  maxLines: 2,
                  onChanged: (value) => description = value,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('CANCEL'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('DECLARE'),
            ),
          ],
        ),
      ),
    );
    if (submit != true || name.trim().isEmpty) return;
    try {
      await _service.declareHoliday(
        date: selected,
        name: name.trim(),
        description: description.trim(),
      );
      _show('Office holiday declared. It will not count as absence.');
      await _load();
    } catch (error) {
      _show(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _reviewLeave(Map<String, dynamic> row, String decision) async {
    String note = '';
    final approved = decision == 'APPROVED';
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          approved ? 'Approve leave request?' : 'Reject leave request?',
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${row['employee_name']}\n${row['start_date']} to ${row['end_date']}',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 14),
            TextField(
              maxLines: 3,
              decoration: InputDecoration(
                labelText: approved
                    ? 'Approval note (optional)'
                    : 'Rejection reason',
                border: const OutlineInputBorder(),
              ),
              onChanged: (value) => note = value,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            style: approved
                ? null
                : FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
            onPressed: () => Navigator.pop(context, true),
            child: Text(approved ? 'APPROVE' : 'REJECT'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _service.reviewLeave(
        leaveId: (row['id'] as num).toInt(),
        status: decision,
        note: note.trim(),
      );
      _show(
        approved ? 'Leave approved successfully.' : 'Leave request rejected.',
      );
      await _load();
    } catch (error) {
      _show(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  Widget _heroMetric(String label, String value) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .12),
      borderRadius: BorderRadius.circular(14),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: Colors.white70, fontSize: 12),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    ),
  );

  Widget _metricCard(IconData icon, String label, String value, Color color) =>
      Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: color),
              const SizedBox(height: 8),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Text(
                label,
                style: const TextStyle(color: Color(0xFF687386), fontSize: 12),
              ),
            ],
          ),
        ),
      );

  Widget _sectionCard({
    required IconData icon,
    required String title,
    required Widget child,
  }) => Card(
    margin: EdgeInsets.zero,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(icon, color: const Color(0xFF0878D8)),
              const SizedBox(width: 10),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const Divider(height: 24),
          child,
        ],
      ),
    ),
  );

  Widget _progressLine(
    String label,
    dynamic remainingValue,
    dynamic totalValue,
  ) {
    final remaining = (remainingValue as num?)?.toDouble() ?? 0;
    final total = (totalValue as num?)?.toDouble() ?? 0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(child: Text(label)),
            Text(
              '${remaining.toInt()} of ${total.toInt()} left',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ],
        ),
        const SizedBox(height: 7),
        LinearProgressIndicator(
          value: total <= 0 ? 0 : (remaining / total).clamp(0, 1),
          minHeight: 7,
          borderRadius: BorderRadius.circular(20),
        ),
      ],
    );
  }

  Widget _line(String title, String value, {bool bold = false}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      children: [
        Expanded(child: Text(title)),
        Text(
          value,
          style: TextStyle(
            fontWeight: bold ? FontWeight.w900 : FontWeight.w600,
          ),
        ),
      ],
    ),
  );
}
