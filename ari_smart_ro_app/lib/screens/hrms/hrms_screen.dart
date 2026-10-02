import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/corporate_hrms_service.dart';
import '../../services/hrms_service.dart';
import '../attendance/attendance_screen.dart';
import 'corporate_joining_wizard.dart';
import 'employee_hr_file_screen.dart';
import 'employee_management_screen.dart';
import 'hr_letters_bgv_screen.dart';
import 'recruitment_screen.dart';
import 'training_screen.dart';

class HrmsScreen extends StatefulWidget {
  const HrmsScreen({super.key});

  @override
  State<HrmsScreen> createState() => _HrmsScreenState();
}

class _HrmsScreenState extends State<HrmsScreen> {
  final _corporate = CorporateHrmsService();
  final _hrms = HrmsService();
  final _search = TextEditingController();

  bool _loading = true;
  String? _error;
  String _role = '';
  int _page = 0;
  String _query = '';
  Map<String, dynamic> _dashboard = const {};
  List<Map<String, dynamic>> _directory = const [];
  List<Map<String, dynamic>> _leaves = const [];
  List<Map<String, dynamic>> _payroll = const [];
  List<Map<String, dynamic>> _penalties = const [];
  List<Map<String, dynamic>> _performance = const [];
  List<Map<String, dynamic>> _documents = const [];

  bool get _isHrAdmin => const {'ADMIN', 'MANAGER', 'OFFICE'}.contains(_role);

  String get _monthValue {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}';
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _role = (await ApiService.getRole() ?? '').toUpperCase();
      _dashboard = await _corporate.dashboard();
      if (_isHrAdmin) {
        _directory = await _corporate.directory();
      }
      await _loadOperations();
    } catch (error) {
      _error = error.toString().replaceFirst('Exception: ', '');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadOperations() async {
    try {
      _leaves = await _hrms.leaves();
    } catch (_) {}
    try {
      _payroll = await _hrms.payroll(month: _isHrAdmin ? _monthValue : null);
    } catch (_) {}
    if (_isHrAdmin) {
      try {
        final data = await _hrms.penalties();
        _penalties = List<Map<String, dynamic>>.from(
          data['penalties'] as List? ?? const [],
        );
      } catch (_) {}
      try {
        _performance = await _hrms.performanceReviews();
      } catch (_) {}
      try {
        _documents = await _hrms.documents();
      } catch (_) {}
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        appBar: _HrmsAppBar(),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Scaffold(
        appBar: const _HrmsAppBar(),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.cloud_off_outlined, size: 44),
                    const SizedBox(height: 12),
                    const Text(
                      'Corporate HRMS could not load',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                    ),
                    const SizedBox(height: 8),
                    Text(_error!, textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _load,
                      icon: const Icon(Icons.refresh),
                      label: const Text('RETRY'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    final width = MediaQuery.sizeOf(context).width;
    final desktop = width >= 1050;
    final pages = [
      _commandCenter(),
      if (_isHrAdmin) _peoplePage() else _employeeSelfService(),
      _operationsPage(),
    ];

    return Scaffold(
      appBar: const _HrmsAppBar(),
      body: Row(
        children: [
          if (desktop)
            NavigationRail(
              selectedIndex: _page,
              onDestinationSelected: (value) => setState(() => _page = value),
              labelType: NavigationRailLabelType.all,
              destinations: const [
                NavigationRailDestination(
                  icon: Icon(Icons.space_dashboard_outlined),
                  selectedIcon: Icon(Icons.space_dashboard),
                  label: Text('Command Center'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.groups_outlined),
                  selectedIcon: Icon(Icons.groups),
                  label: Text('People'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.fact_check_outlined),
                  selectedIcon: Icon(Icons.fact_check),
                  label: Text('Operations'),
                ),
              ],
            ),
          if (desktop) const VerticalDivider(width: 1),
          Expanded(child: pages[_page]),
        ],
      ),
      bottomNavigationBar: desktop
          ? null
          : NavigationBar(
              selectedIndex: _page,
              onDestinationSelected: (value) => setState(() => _page = value),
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.space_dashboard_outlined),
                  selectedIcon: Icon(Icons.space_dashboard),
                  label: 'Command',
                ),
                NavigationDestination(
                  icon: Icon(Icons.groups_outlined),
                  selectedIcon: Icon(Icons.groups),
                  label: 'People',
                ),
                NavigationDestination(
                  icon: Icon(Icons.fact_check_outlined),
                  selectedIcon: Icon(Icons.fact_check),
                  label: 'Operations',
                ),
              ],
            ),
    );
  }

  Widget _commandCenter() {
    final workforce = Map<String, dynamic>.from(
      _dashboard['workforce'] as Map? ?? const {},
    );
    final approvals = Map<String, dynamic>.from(
      _dashboard['approvals'] as Map? ?? const {},
    );
    final compliance = Map<String, dynamic>.from(
      _dashboard['compliance'] as Map? ?? const {},
    );
    final payroll = Map<String, dynamic>.from(
      _dashboard['payroll'] as Map? ?? const {},
    );

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          _hero(workforce),
          const SizedBox(height: 16),
          const Text(
            'Executive workforce snapshot',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          LayoutBuilder(
            builder: (context, constraints) => Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _metric('Active workforce', workforce['active'], Icons.groups_outlined, constraints.maxWidth),
                _metric('Present today', workforce['present_today'], Icons.how_to_reg_outlined, constraints.maxWidth),
                _metric('Absent / not checked-in', workforce['absent_or_not_checked_in'], Icons.person_off_outlined, constraints.maxWidth),
                _metric('New joiners • 30d', workforce['new_joiners_30d'], Icons.person_add_alt_1_outlined, constraints.maxWidth),
                _metric('Probation', workforce['probation'], Icons.hourglass_top_outlined, constraints.maxWidth),
                _metric('Confirmation due', workforce['confirmation_due_30d'], Icons.workspace_premium_outlined, constraints.maxWidth),
                _metric('Pending onboarding', workforce['pending_onboarding'], Icons.assignment_late_outlined, constraints.maxWidth),
                _metric('Notice period', workforce['notice_period'], Icons.exit_to_app_outlined, constraints.maxWidth),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'Action queue',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          _actionQueue(approvals, compliance),
          const SizedBox(height: 18),
          const Text(
            'Quick actions',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          _quickActions(),
          const SizedBox(height: 18),
          LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 860;
              final structure = _structureCard(workforce);
              final payrollCard = _payrollSummary(payroll);
              if (!wide) {
                return Column(children: [structure, const SizedBox(height: 12), payrollCard]);
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: structure),
                  const SizedBox(width: 12),
                  Expanded(child: payrollCard),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _hero(Map<String, dynamic> workforce) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF0B3B68), Color(0xFF174E8B)],
          ),
          borderRadius: BorderRadius.circular(22),
        ),
        child: Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 18,
          runSpacing: 14,
          children: [
            const SizedBox(
              width: 520,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'ARI SMART RO • PEOPLE OPERATIONS',
                    style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800, letterSpacing: .8),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Corporate HR Command Center',
                    style: TextStyle(color: Colors.white, fontSize: 29, fontWeight: FontWeight.w900),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Joining, workforce, compliance, payroll, performance and employee lifecycle control.',
                    style: TextStyle(color: Colors.white70),
                  ),
                ],
              ),
            ),
            Wrap(
              spacing: 10,
              children: [
                _heroPill('ACTIVE', workforce['active']),
                _heroPill('PRESENT', workforce['present_today']),
                _heroPill('ONBOARDING', workforce['pending_onboarding']),
              ],
            ),
          ],
        ),
      );

  Widget _heroPill(String label, dynamic value) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white24),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${value ?? 0}', style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900)),
            Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.w700)),
          ],
        ),
      );

  Widget _metric(String label, dynamic value, IconData icon, double width) {
    final cardWidth = width >= 1200
        ? (width - 30) / 4
        : width >= 700
            ? (width - 10) / 2
            : width;
    return SizedBox(
      width: cardWidth,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(child: Icon(icon)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${value ?? 0}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
                    Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _actionQueue(
    Map<String, dynamic> approvals,
    Map<String, dynamic> compliance,
  ) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _queueChip('Leave approvals', approvals['leave'], Icons.event_available_outlined),
              _queueChip('Payroll drafts', approvals['payroll'], Icons.payments_outlined),
              _queueChip('Penalty drafts', approvals['penalty'], Icons.gavel_outlined),
              _queueChip('Performance due', approvals['performance'], Icons.insights_outlined),
              _queueChip('Missing documents', compliance['missing_required_documents'], Icons.folder_off_outlined),
              _queueChip('Unverified documents', compliance['unverified_documents'], Icons.fact_check_outlined),
              _queueChip('Training overdue', compliance['training_overdue'], Icons.school_outlined),
            ],
          ),
        ),
      );

  Widget _queueChip(String label, dynamic value, IconData icon) => ActionChip(
        avatar: Icon(icon, size: 18),
        label: Text('$label • ${value ?? 0}'),
        onPressed: () => setState(() => _page = 2),
      );

  Widget _quickActions() {
    final actions = <_QuickAction>[
      if (_isHrAdmin)
        _QuickAction('New Joining', Icons.person_add_alt_1_outlined, _openJoining),
      if (_isHrAdmin)
        _QuickAction('Talent Acquisition', Icons.person_search_outlined, () => _push(const RecruitmentScreen())),
      if (_isHrAdmin)
        _QuickAction('HR Letters & BGV', Icons.verified_user_outlined, () => _push(const HrLettersBgvScreen())),
      if (_isHrAdmin)
        _QuickAction('Employee Lifecycle', Icons.account_tree_outlined, () => Navigator.of(context).pushNamed('/hrms/lifecycle')),
      _QuickAction('Employee Directory', Icons.badge_outlined, () => setState(() => _page = 1)),
      _QuickAction('Attendance', Icons.fingerprint_outlined, () => _push(const AttendanceScreen())),
      _QuickAction('Leave', Icons.event_note_outlined, () => setState(() => _page = 2)),
      _QuickAction('Payroll', Icons.payments_outlined, () => setState(() => _page = 2)),
      _QuickAction('Documents', Icons.folder_copy_outlined, () => setState(() => _page = 2)),
      _QuickAction('Training', Icons.school_outlined, () => _push(const TrainingScreen())),
      _QuickAction('Performance', Icons.query_stats_outlined, () => setState(() => _page = 2)),
      if (_isHrAdmin)
        _QuickAction('Career Movement', Icons.trending_up_outlined, () => _peopleHint('Open an employee HR file for career movement history/actions.')),
      if (_isHrAdmin)
        _QuickAction('Exit Management', Icons.logout_outlined, () => _peopleHint('Open an employee HR file to start notice or separation.')),
      if (_isHrAdmin)
        _QuickAction('HR Reports', Icons.download_outlined, _downloadPayroll),
      if (_isHrAdmin)
        _QuickAction('Employee Admin', Icons.admin_panel_settings_outlined, () => _push(const EmployeeManagementScreen())),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1200
            ? 6
            : constraints.maxWidth >= 760
                ? 4
                : 2;
        final width = (constraints.maxWidth - (columns - 1) * 10) / columns;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: actions
              .map(
                (item) => SizedBox(
                  width: width,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: item.onTap,
                    child: Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 15),
                        child: Column(
                          children: [
                            Icon(item.icon, size: 28),
                            const SizedBox(height: 7),
                            Text(item.label, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700)),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        );
      },
    );
  }

  Widget _structureCard(Map<String, dynamic> workforce) {
    final departments = Map<String, dynamic>.from(workforce['department_mix'] as Map? ?? const {});
    final designations = Map<String, dynamic>.from(workforce['designation_mix'] as Map? ?? const {});
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Workforce structure', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const Divider(height: 22),
            if (departments.isEmpty && designations.isEmpty)
              const Text('No workforce structure data yet.'),
            ...departments.entries.map((e) => _structureRow(e.key, e.value)),
            if (departments.isNotEmpty && designations.isNotEmpty) const Divider(),
            ...designations.entries.map((e) => _structureRow(e.key, e.value)),
          ],
        ),
      ),
    );
  }

  Widget _structureRow(String label, dynamic value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [Expanded(child: Text(label)), Text('${value ?? 0}', style: const TextStyle(fontWeight: FontWeight.w900))]),
      );

  Widget _payrollSummary(Map<String, dynamic> payroll) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Payroll control', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
              const Divider(height: 22),
              _structureRow('Month', payroll['month']),
              _structureRow('Draft', payroll['draft']),
              _structureRow('Approved', payroll['approved']),
              _structureRow('Paid', payroll['paid']),
              _structureRow('Net payroll', '₹${payroll['net_salary'] ?? 0}'),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: () => setState(() => _page = 2),
                icon: const Icon(Icons.arrow_forward),
                label: const Text('OPEN PAYROLL OPERATIONS'),
              ),
            ],
          ),
        ),
      );

  Widget _peoplePage() {
    final rows = _directory.where((row) {
      if (_query.trim().isEmpty) return true;
      final q = _query.toLowerCase();
      return [
        row['name'],
        row['employee_id'],
        row['phone'],
        row['job_title'],
        row['department'],
        row['designation'],
      ].any((v) => (v ?? '').toString().toLowerCase().contains(q));
    }).toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Row(
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Employee Directory', style: TextStyle(fontSize: 25, fontWeight: FontWeight.w900)),
                    Text('Digital personnel files, onboarding, probation and lifecycle status.'),
                  ],
                ),
              ),
              FilledButton.icon(
                onPressed: _openJoining,
                icon: const Icon(Icons.person_add_alt_1),
                label: const Text('NEW JOINING'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _search,
            onChanged: (value) => setState(() => _query = value),
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search employee, ID, role, department, phone...',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 900) {
                return _employeeTable(rows);
              }
              return Column(children: rows.map(_employeeCard).toList());
            },
          ),
        ],
      ),
    );
  }

  Widget _employeeTable(List<Map<String, dynamic>> rows) => Card(
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columns: const [
              DataColumn(label: Text('EMPLOYEE')),
              DataColumn(label: Text('ROLE / DEPARTMENT')),
              DataColumn(label: Text('EMPLOYMENT')),
              DataColumn(label: Text('ONBOARDING')),
              DataColumn(label: Text('CONFIRMATION')),
              DataColumn(label: Text('ACTION')),
            ],
            rows: rows.map((row) {
              final lifecycle = Map<String, dynamic>.from(row['lifecycle'] as Map? ?? const {});
              return DataRow(cells: [
                DataCell(Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(row['name']?.toString() ?? '-', style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text('${row['employee_id'] ?? '-'} • ${row['phone'] ?? '-'}'),
                  ],
                )),
                DataCell(Text('${row['job_title'] ?? row['designation'] ?? '-'}\n${row['department'] ?? '-'}')),
                DataCell(Text((lifecycle['employment_status'] ?? '-').toString().replaceAll('_', ' '))),
                DataCell(_smallStatus((lifecycle['hr_stage'] ?? '-').toString())),
                DataCell(Text('${lifecycle['confirmation_due_date'] ?? '-'}')),
                DataCell(IconButton(
                  tooltip: 'Open digital HR file',
                  onPressed: () => _openEmployee(row),
                  icon: const Icon(Icons.open_in_new),
                )),
              ]);
            }).toList(),
          ),
        ),
      );

  Widget _employeeCard(Map<String, dynamic> row) {
    final lifecycle = Map<String, dynamic>.from(row['lifecycle'] as Map? ?? const {});
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          child: Text((row['name'] ?? 'E').toString().trim().isEmpty ? 'E' : (row['name'] ?? 'E').toString().trim()[0].toUpperCase()),
        ),
        title: Text(row['name']?.toString() ?? '-', style: const TextStyle(fontWeight: FontWeight.w800)),
        subtitle: Text('${row['employee_id'] ?? '-'} • ${row['job_title'] ?? row['designation'] ?? '-'}\n${row['department'] ?? '-'} • ${(lifecycle['hr_stage'] ?? '-').toString().replaceAll('_', ' ')}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => _openEmployee(row),
      ),
    );
  }

  Widget _smallStatus(String label) => Chip(
        visualDensity: VisualDensity.compact,
        label: Text(label.replaceAll('_', ' ')),
      );

  Widget _employeeSelfService() {
    final employee = Map<String, dynamic>.from(
      _dashboard['employee'] as Map? ?? const {},
    );
    final attendance = Map<String, dynamic>.from(
      _dashboard['attendance'] as Map? ?? const {},
    );
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Text(employee['name']?.toString() ?? 'My HR', style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          _sectionCard('Attendance', Icons.schedule_outlined, [
            _infoLine('Present days', attendance['present_days']),
            _infoLine('Half days', attendance['half_days']),
            _infoLine('Late days', attendance['late_days']),
            _infoLine('Total hours', attendance['total_hours']),
          ]),
        ],
      ),
    );
  }

  Widget _operationsPage() {
    final pendingLeaves = _leaves.where((e) => (e['status'] ?? '').toString().toUpperCase() == 'PENDING').toList();
    final draftPayroll = _payroll.where((e) => (e['status'] ?? '').toString().toUpperCase() == 'DRAFT').toList();
    final draftPenalties = _penalties.where((e) => (e['status'] ?? '').toString().toUpperCase() == 'DRAFT').toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          const Text('HR Operations', style: TextStyle(fontSize: 25, fontWeight: FontWeight.w900)),
          const Text('Approvals, payroll, compliance and performance — kept separate from the executive dashboard.'),
          const SizedBox(height: 14),
          if (_isHrAdmin) _payrollControl(),
          const SizedBox(height: 12),
          _sectionCard('Leave approval queue', Icons.event_available_outlined, [
            if (pendingLeaves.isEmpty) const Text('No leave requests awaiting review.'),
            ...pendingLeaves.take(12).map(_leaveRow),
          ]),
          const SizedBox(height: 12),
          if (_isHrAdmin)
            _sectionCard('Payroll approval queue', Icons.payments_outlined, [
              if (draftPayroll.isEmpty) const Text('No payroll drafts awaiting approval.'),
              ...draftPayroll.take(20).map(_payrollRow),
            ]),
          if (_isHrAdmin) const SizedBox(height: 12),
          if (_isHrAdmin)
            _sectionCard('Penalty review queue', Icons.gavel_outlined, [
              if (draftPenalties.isEmpty) const Text('No penalty drafts awaiting approval.'),
              ...draftPenalties.take(20).map(_penaltyRow),
            ]),
          if (_isHrAdmin) const SizedBox(height: 12),
          if (_isHrAdmin)
            _sectionCard('Document compliance', Icons.folder_copy_outlined, [
              if (_documents.isEmpty) const Text('No employee document records.'),
              ..._documents.take(30).map((row) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(row['verified'] == true ? Icons.verified_outlined : Icons.pending_outlined),
                    title: Text('${row['employee_name'] ?? '-'} • ${row['document_type'] ?? '-'}'),
                    subtitle: Text('Expiry: ${row['expiry_date'] ?? 'No expiry'} • ${row['expiry_state'] ?? '-'}'),
                    trailing: Text(row['verified'] == true ? 'VERIFIED' : 'PENDING'),
                  )),
            ]),
          if (_isHrAdmin) const SizedBox(height: 12),
          if (_isHrAdmin)
            _sectionCard('Performance & appraisal', Icons.insights_outlined, [
              if (_performance.isEmpty) const Text('No performance review available yet.'),
              ..._performance.take(20).map((row) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.query_stats),
                    title: Text('${row['employee_name'] ?? '-'} • ${row['overall_score'] ?? 0}'),
                    subtitle: Text('${row['period_start'] ?? '-'} to ${row['period_end'] ?? '-'} • ${row['status'] ?? '-'}'),
                  )),
            ]),
        ],
      ),
    );
  }

  Widget _payrollControl() => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Monthly payroll control', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                    Text('Generate draft → verify → approve → paid. Deductions remain auditable.'),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.tonalIcon(
                onPressed: _generatePayroll,
                icon: const Icon(Icons.calculate_outlined),
                label: Text('GENERATE $_monthValue'),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: _downloadPayroll,
                icon: const Icon(Icons.download),
                label: const Text('EXCEL'),
              ),
            ],
          ),
        ),
      );

  Widget _sectionCard(String title, IconData icon, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(children: [Icon(icon), const SizedBox(width: 8), Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900))]),
              const Divider(height: 24),
              ...children,
            ],
          ),
        ),
      );

  Widget _infoLine(String label, dynamic value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [Expanded(child: Text(label)), Text('${value ?? 0}', style: const TextStyle(fontWeight: FontWeight.w900))]),
      );

  Widget _leaveRow(Map<String, dynamic> row) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: const Icon(Icons.event_note_outlined),
        title: Text('${row['employee_name'] ?? row['employee'] ?? '-'} • ${row['leave_type'] ?? '-'}'),
        subtitle: Text('${row['start_date'] ?? '-'} to ${row['end_date'] ?? '-'}\n${row['reason'] ?? ''}'),
        trailing: _isHrAdmin
            ? Wrap(
                spacing: 4,
                children: [
                  IconButton(
                    tooltip: 'Reject',
                    onPressed: () => _reviewLeave(row, 'REJECTED'),
                    icon: const Icon(Icons.close),
                  ),
                  IconButton(
                    tooltip: 'Approve',
                    onPressed: () => _reviewLeave(row, 'APPROVED'),
                    icon: const Icon(Icons.check),
                  ),
                ],
              )
            : Text('${row['status'] ?? '-'}'),
      );

  Widget _payrollRow(Map<String, dynamic> row) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: const Icon(Icons.payments_outlined),
        title: Text('${row['employee_name'] ?? '-'} • ₹${row['net_salary'] ?? 0}'),
        subtitle: Text('${row['payroll_month'] ?? '-'} • Base ₹${row['base_salary'] ?? 0}'),
        trailing: FilledButton.tonal(
          onPressed: () => _payrollAction(row, 'APPROVE'),
          child: const Text('APPROVE'),
        ),
      );

  Widget _penaltyRow(Map<String, dynamic> row) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: const Icon(Icons.gavel_outlined),
        title: Text('${row['employee_name'] ?? row['employee'] ?? '-'} • ₹${row['amount'] ?? 0}'),
        subtitle: Text('${row['penalty_date'] ?? '-'} • ${row['reason'] ?? ''}'),
        trailing: Wrap(
          spacing: 4,
          children: [
            TextButton(onPressed: () => _penaltyAction(row, 'CANCEL'), child: const Text('CANCEL')),
            FilledButton.tonal(onPressed: () => _penaltyAction(row, 'APPROVE'), child: const Text('APPROVE')),
          ],
        ),
      );

  void _push(Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  Future<void> _openJoining() async {
    final managers = _directory
        .where((row) => row['is_active'] == true)
        .toList();
    await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => CorporateJoiningWizard(
          managers: managers,
          onCompleted: _load,
        ),
      ),
    );
  }

  Future<void> _openEmployee(Map<String, dynamic> row) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => EmployeeHrFileScreen(employeeId: id)),
    );
    await _load();
  }

  void _peopleHint(String message) {
    setState(() => _page = 1);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _reviewLeave(Map<String, dynamic> row, String status) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    try {
      await _hrms.reviewLeave(leaveId: id, status: status, note: 'Reviewed from Corporate HR Operations.');
      await _load();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _payrollAction(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    try {
      await _hrms.payrollAction(id, action);
      await _load();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _penaltyAction(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    try {
      await _hrms.penaltyAction(id, action);
      await _load();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _generatePayroll() async {
    try {
      final count = await _hrms.generatePayroll(_monthValue);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$count payroll drafts generated.')));
      await _load();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _downloadPayroll() async {
    try {
      final path = await _hrms.downloadPayroll(_monthValue);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Salary register saved: $path')));
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
    );
  }
}

class _HrmsAppBar extends StatelessWidget implements PreferredSizeWidget {
  const _HrmsAppBar();

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) => AppBar(
        title: const Text('Employee HRMS'),
      );
}

class _QuickAction {
  const _QuickAction(this.label, this.icon, this.onTap);

  final String label;
  final IconData icon;
  final VoidCallback onTap;
}
