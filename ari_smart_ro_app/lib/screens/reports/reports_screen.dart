import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../services/report_service.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  static const Map<String, String> _periods = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "halfyearly": "Half-Yearly",
    "annual": "Annual",
  };

  final ReportService _service = ReportService();

  String _period = "monthly";
  DateTime _date = DateTime.now();
  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = true;
  bool _downloading = false;

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
      final data = await _service.getSummary(
        period: _period,
        date: _date,
      );
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString().replaceFirst("Exception: ", "");
        _loading = false;
      });
    }
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 366)),
    );
    if (selected == null || !mounted) return;
    setState(() => _date = selected);
    await _load();
  }

  Future<void> _download() async {
    if (_downloading) return;
    setState(() => _downloading = true);
    try {
      final path = await _service.downloadExcel(
        period: _period,
        date: _date,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Excel report saved: $path"),
          duration: const Duration(seconds: 6),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error.toString().replaceFirst("Exception: ", ""),
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  Map<String, dynamic> _map(String key) {
    final value = _data?[key];
    return value is Map
        ? Map<String, dynamic>.from(value)
        : <String, dynamic>{};
  }

  Map<String, dynamic> _nestedMap(String parent, String child) {
    final value = _map(parent)[child];
    return value is Map
        ? Map<String, dynamic>.from(value)
        : <String, dynamic>{};
  }

  List<Map<String, dynamic>> _list(String parent, String child) {
    final value = _map(parent)[child];
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
  }

  String _money(dynamic value) {
    final number = num.tryParse(value?.toString() ?? "") ?? 0;
    return NumberFormat.currency(
      locale: "en_IN",
      symbol: "₹",
      decimalDigits: 2,
    ).format(number);
  }

  String _number(dynamic value) {
    final number = num.tryParse(value?.toString() ?? "") ?? 0;
    return NumberFormat.decimalPattern("en_IN").format(number);
  }

  @override
  Widget build(BuildContext context) {
    final period = _map("period");

    return Scaffold(
      appBar: AppBar(
        title: const Text("Business Reports"),
        actions: [
          IconButton(
            tooltip: "Download Excel",
            onPressed: _data == null || _downloading ? null : _download,
            icon: _downloading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.download),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            _filters(),
            const SizedBox(height: 12),
            if (period.isNotEmpty)
              Text(
                period["label"]?.toString() ?? "",
                style: Theme.of(context).textTheme.titleMedium,
              ),
            const SizedBox(height: 12),
            if (_loading)
              const Padding(
                padding: EdgeInsets.only(top: 80),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _errorCard()
            else ...[
              _overview(),
              const SizedBox(height: 12),
              _partsSection(),
              _rentSection(),
              _attendanceSection(),
              _operationsSection(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _filters() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _period,
                decoration: const InputDecoration(
                  labelText: "Report Period",
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                items: _periods.entries
                    .map(
                      (entry) => DropdownMenuItem(
                        value: entry.key,
                        child: Text(entry.value),
                      ),
                    )
                    .toList(),
                onChanged: (value) async {
                  if (value == null) return;
                  setState(() => _period = value);
                  await _load();
                },
              ),
            ),
            const SizedBox(width: 10),
            OutlinedButton.icon(
              onPressed: _pickDate,
              icon: const Icon(Icons.calendar_month),
              label: Text(DateFormat("dd MMM yyyy").format(_date)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _errorCard() {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(_error ?? "Unable to load reports."),
            const SizedBox(height: 8),
            ElevatedButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              label: const Text("Retry"),
            ),
          ],
        ),
      ),
    );
  }

  Widget _overview() {
    final overview = _map("overview");
    return _section(
      title: "Overview",
      icon: Icons.dashboard_outlined,
      initiallyExpanded: true,
      children: [
        _metricGrid([
          ("Parts Used", _number(overview["parts_used"]), Icons.build),
          ("Rent Collected", _money(overview["rent_collected"]), Icons.payments),
          ("Rent Outstanding", _money(overview["rent_outstanding"]), Icons.warning_amber),
          ("Attendance Hours", _number(overview["attendance_hours"]), Icons.schedule),
          ("Jobs Completed", _number(overview["jobs_completed"]), Icons.task_alt),
          ("Open Complaints", _number(overview["open_complaints"]), Icons.report_problem),
        ]),
      ],
    );
  }

  Widget _partsSection() {
    final summary = _nestedMap("parts", "summary");
    final employees = _list("parts", "by_employee");
    final parts = _list("parts", "by_part");

    return _section(
      title: "Parts Usage",
      icon: Icons.inventory_2_outlined,
      children: [
        _metricGrid([
          ("Used Quantity", _number(summary["used_quantity"]), Icons.build_circle_outlined),
          ("Employees", _number(summary["employees"]), Icons.engineering),
          ("Jobs", _number(summary["jobs"]), Icons.work_outline),
          ("Part Requests", _number(summary["part_requests"]), Icons.request_page_outlined),
          ("Bag Issued", _number(summary["bag_items_issued"]), Icons.outbox_outlined),
          ("Bag Installed", _number(summary["bag_items_installed"]), Icons.install_mobile),
        ]),
        _subheading("Employee-wise Usage"),
        if (employees.isEmpty)
          const Text("No part usage in this period.")
        else
          ...employees.take(25).map(
                (row) => _reportTile(
                  title: row["employee_name"]?.toString() ?? "Employee",
                  subtitle:
                      "${row["employee_id"] ?? ""} • ${row["jobs"] ?? 0} jobs • ${row["different_parts"] ?? 0} part types",
                  trailing: "${_number(row["quantity"])} used",
                ),
              ),
        _subheading("Part-wise Usage"),
        ...parts.take(25).map(
              (row) => _reportTile(
                title: row["inventory_item__part__name"]?.toString() ?? "Part",
                subtitle:
                    "${row["inventory_item__part__code"] ?? ""} • ${row["employees"] ?? 0} employees",
                trailing: "${_number(row["quantity"])} used",
              ),
            ),
      ],
    );
  }

  Widget _rentSection() {
    final summary = _nestedMap("rent", "summary");
    final collectors = _list("rent", "by_collector");
    final dues = _list("rent", "outstanding_customers");

    return _section(
      title: "Rent Reports",
      icon: Icons.account_balance_wallet_outlined,
      children: [
        _metricGrid([
          ("Expected", _money(summary["expected"]), Icons.receipt_long),
          ("Paid", _money(summary["paid"]), Icons.check_circle_outline),
          ("Outstanding", _money(summary["outstanding"]), Icons.pending_actions),
          ("Transactions", _number(summary["payment_transactions"]), Icons.swap_horiz),
          ("Customers", _number(summary["customers"]), Icons.people_outline),
          ("Customers Due", _number(summary["customers_with_due"]), Icons.person_off_outlined),
        ]),
        _subheading("Employee-wise Collection"),
        if (collectors.isEmpty)
          const Text("No rent collection in this period.")
        else
          ...collectors.take(25).map(
                (row) => _reportTile(
                  title: row["employee_name"]?.toString() ?? "Unassigned",
                  subtitle:
                      "${row["employee_id"] ?? ""} • ${row["payments"] ?? 0} payments • ${row["customers"] ?? 0} customers",
                  trailing: _money(row["amount"]),
                ),
              ),
        _subheading("Outstanding Customers"),
        if (dues.isEmpty)
          const Text("No outstanding rent in this period.")
        else
          ...dues.take(50).map(
                (row) => _reportTile(
                  title: row["customer_name"]?.toString() ?? "Customer",
                  subtitle:
                      "${row["customer_code"] ?? ""} • ${row["phone"] ?? ""}",
                  trailing: _money(row["outstanding"]),
                  warning: true,
                ),
              ),
      ],
    );
  }

  Widget _attendanceSection() {
    final summary = _nestedMap("attendance", "summary");
    final employees = _list("attendance", "by_employee");

    return _section(
      title: "Employee Attendance",
      icon: Icons.fact_check_outlined,
      children: [
        _metricGrid([
          ("Present", _number(summary["present"]), Icons.check_circle),
          ("Absent", _number(summary["absent"]), Icons.cancel_outlined),
          ("Half Day", _number(summary["half_day"]), Icons.timelapse),
          ("Leave", _number(summary["leave"]), Icons.event_busy),
          ("Working Hours", _number(summary["working_hours"]), Icons.schedule),
          ("Pending Reviews", _number(summary["pending_identity_reviews"]), Icons.pending),
        ]),
        _subheading("Employee-wise Attendance"),
        if (employees.isEmpty)
          const Text("No attendance in this period.")
        else
          ...employees.take(50).map(
                (row) => _reportTile(
                  title: row["employee_name"]?.toString() ?? "Employee",
                  subtitle:
                      "${row["employee_id"] ?? ""} • P ${row["present"] ?? 0} • A ${row["absent"] ?? 0} • H ${row["half_day"] ?? 0} • L ${row["leave"] ?? 0}",
                  trailing: "${_number(row["working_hours"])} hrs",
                  warning: (row["missing_checkout"] as num? ?? 0) > 0,
                ),
              ),
      ],
    );
  }

  Widget _operationsSection() {
    final summary = _nestedMap("operations", "summary");
    final jobs = _nestedMap("operations", "jobs_by_status");
    final complaints = _nestedMap("operations", "complaints_by_status");

    return _section(
      title: "Operations",
      icon: Icons.insights_outlined,
      children: [
        _metricGrid([
          ("New Customers", _number(summary["new_customers"]), Icons.person_add_alt),
          ("Jobs Created", _number(summary["jobs_created"]), Icons.work_outline),
          ("Jobs Completed", _number(summary["jobs_completed"]), Icons.task_alt),
          ("Complaints Created", _number(summary["complaints_created"]), Icons.report),
          ("Complaints Resolved", _number(summary["complaints_resolved"]), Icons.verified),
          ("Purchase Value", _money(summary["purchase_value"]), Icons.shopping_cart_checkout),
        ]),
        _subheading("Job Status"),
        _statusWrap(jobs),
        _subheading("Complaint Status"),
        _statusWrap(complaints),
      ],
    );
  }

  Widget _section({
    required String title,
    required IconData icon,
    required List<Widget> children,
    bool initiallyExpanded = false,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ExpansionTile(
        initiallyExpanded: initiallyExpanded,
        leading: Icon(icon),
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: children,
      ),
    );
  }

  Widget _metricGrid(
    List<(String, String, IconData)> values,
  ) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = (constraints.maxWidth - 10) / 2;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: values
              .map(
                (item) => SizedBox(
                  width: width,
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(item.$3, size: 20),
                        const SizedBox(height: 8),
                        Text(
                          item.$2,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          item.$1,
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              )
              .toList(),
        );
      },
    );
  }

  Widget _subheading(String title) {
    return Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 8),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  Widget _reportTile({
    required String title,
    required String subtitle,
    required String trailing,
    bool warning = false,
  }) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: Text(
        trailing,
        textAlign: TextAlign.end,
        style: TextStyle(
          fontWeight: FontWeight.bold,
          color: warning ? Colors.red.shade700 : null,
        ),
      ),
    );
  }

  Widget _statusWrap(Map<String, dynamic> values) {
    if (values.isEmpty) return const Text("No records.");
    return Align(
      alignment: Alignment.centerLeft,
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: values.entries
            .map(
              (entry) => Chip(
                label: Text(
                  "${entry.key.replaceAll("_", " ")}: ${entry.value}",
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}
