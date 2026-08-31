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
  List<Map<String, dynamic>> _leaves = [], _payroll = [];
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
      final values = await Future.wait([
        _service.leaves(),
        _service.payroll(month: _role == 'ADMIN' ? _monthValue : null),
      ]);
      if (mounted) {
        setState(() {
          _leaves = values[0];
          _payroll = values[1];
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
                  title: const Text('Start date'),
                  subtitle: Text('${start.day}/${start.month}/${start.year}'),
                  onTap: () async {
                    final value = await showDatePicker(
                      context: context,
                      firstDate: DateTime.now().add(const Duration(days: 1)),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                      initialDate: start,
                    );
                    if (value != null) {
                      setLocal(() {
                        start = value;
                        if (end.isBefore(start)) {
                          end = start;
                        }
                      });
                    }
                  },
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('End date'),
                  subtitle: Text('${end.day}/${end.month}/${end.year}'),
                  onTap: () async {
                    final value = await showDatePicker(
                      context: context,
                      firstDate: start,
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                      initialDate: end.isBefore(start) ? start : end,
                    );
                    if (value != null) setLocal(() => end = value);
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
                    child: ListTile(
                      leading: Icon(
                        row['type'] == 'HALF_DAY'
                            ? Icons.timelapse
                            : Icons.event,
                      ),
                      title: Text(
                        _role == 'ADMIN'
                            ? '${row['employee_name']} • ${row['type']}'
                            : row['type'].toString().replaceAll('_', ' '),
                      ),
                      subtitle: Text(
                        '${row['start_date']} to ${row['end_date']}\n${row['reason']}',
                      ),
                      isThreeLine: true,
                      trailing: Chip(label: Text(row['status'].toString())),
                    ),
                  ),
                ),
                const SizedBox(height: 80),
              ],
            ),
          ),
  );

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
