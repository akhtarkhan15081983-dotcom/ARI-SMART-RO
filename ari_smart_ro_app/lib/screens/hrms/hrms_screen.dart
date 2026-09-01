import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/hrms_service.dart';

class HrmsScreen extends StatefulWidget {
  const HrmsScreen({super.key});
  @override
  State<HrmsScreen> createState() => _HrmsScreenState();
}

class _HrmsScreenState extends State<HrmsScreen> {
  final _service = HrmsService();
  List<Map<String, dynamic>> _leaves = [], _payroll = [], _holidays = [];
  Map<String, dynamic> _dashboard = {};
  bool _loading = true;
  String _role = '';
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month - 1);

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _monthValue =>
      '${_month.year}-${_month.month.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _role = (await ApiService.getRole() ?? '').toUpperCase();
      final values = await Future.wait<dynamic>([
        _service.leaves(),
        _service.payroll(month: _role == 'ADMIN' ? _monthValue : null),
        if (_role != 'ADMIN') _service.dashboard(),
        _service.holidays(year: DateTime.now().year),
      ]);
      if (mounted) {
        setState(() {
          _leaves = values[0];
          _payroll = values[1];
          _dashboard = _role == 'ADMIN'
              ? <String, dynamic>{}
              : Map<String, dynamic>.from(values[2] as Map);
          _holidays = List<Map<String, dynamic>>.from(
            values[_role == 'ADMIN' ? 2 : 3] as List,
          );
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
    DateTime start = DateTime.now().add(const Duration(days: 1)),
        end = DateTime.now().add(const Duration(days: 1));
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
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.date_range_outlined),
                  title: const Text('Select leave dates'),
                  subtitle: Text(
                    start == end
                        ? '${start.day}/${start.month}/${start.year}'
                        : '${start.day}/${start.month}/${start.year} – ${end.day}/${end.month}/${end.year}',
                  ),
                  trailing: const Icon(Icons.calendar_month),
                  onTap: () async {
                    final value = await showDateRangePicker(
                      context: context,
                      firstDate: DateTime.now().add(const Duration(days: 1)),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                      initialDateRange: DateTimeRange(start: start, end: end),
                      helpText: 'CHOOSE LEAVE PERIOD',
                      confirmText: 'USE THESE DATES',
                    );
                    if (value != null) {
                      setLocal(() {
                        start = value.start;
                        end = value.end;
                      });
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
        start: start,
        end: end,
        reason: reason,
      );
      _show('Leave request submitted for approval.');
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
                _holidaySection(),
                const SizedBox(height: 14),
                Text(
                  'Salary & incentives',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                if (_payroll.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(20),
                      child: Text('No payroll record available.'),
                    ),
                  ),
                ..._payroll.map(
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
                ..._leaves.map(
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

  Widget _adminReportOverview() {
    final pendingLeaves = _leaves
        .where((row) => row['status'] == 'PENDING')
        .length;
    final approvedLeaves = _leaves
        .where((row) => row['status'] == 'APPROVED')
        .length;
    final grossPayroll = _payroll.fold<double>(
      0,
      (sum, row) => sum + (double.tryParse('${row['net_salary']}') ?? 0),
    );
    final pendingPayroll = _payroll
        .where((row) => row['status'] != 'PAID')
        .length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Admin HR reports',
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
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
              Icons.pending_actions,
              'Pending leaves',
              '$pendingLeaves',
              const Color(0xFFE17819),
            ),
            _metricCard(
              Icons.event_available,
              'Approved leaves',
              '$approvedLeaves',
              const Color(0xFF0A8F70),
            ),
            _metricCard(
              Icons.account_balance_wallet_outlined,
              'Net salary register',
              _money(grossPayroll),
              const Color(0xFF0878D8),
            ),
            _metricCard(
              Icons.receipt_long_outlined,
              'Payroll pending',
              '$pendingPayroll',
              const Color(0xFF7B4BC4),
            ),
          ],
        ),
        const SizedBox(height: 10),
        const Text(
          'Employee-wise attendance, penalties, overtime, incentives, leave records and payroll details are shown below and included in the salary Excel report.',
          style: TextStyle(color: Color(0xFF687386)),
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
