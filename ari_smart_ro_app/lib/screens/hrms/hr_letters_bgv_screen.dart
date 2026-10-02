import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/corporate_hrms_service.dart';

class HrLettersBgvScreen extends StatefulWidget {
  const HrLettersBgvScreen({super.key});

  @override
  State<HrLettersBgvScreen> createState() => _HrLettersBgvScreenState();
}

class _HrLettersBgvScreenState extends State<HrLettersBgvScreen> {
  final _service = CorporateHrmsService();
  final _search = TextEditingController();

  bool _loading = true;
  String? _error;
  String _role = '';
  String _query = '';
  int _section = 0;
  Map<String, dynamic> _dashboard = const {};
  Map<String, dynamic> _policy = const {};
  List<Map<String, dynamic>> _templates = const [];
  List<Map<String, dynamic>> _workflows = const [];
  List<Map<String, dynamic>> _letters = const [];
  List<Map<String, dynamic>> _cases = const [];

  bool get _canManage => const {'ADMIN', 'OFFICE'}.contains(_role);
  bool get _canApprove => _role == 'ADMIN';
  bool get _canBgvManage => const {'ADMIN', 'OFFICE'}.contains(_role);
  bool get _canBgvDecide => _role == 'ADMIN';

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
      final results = await Future.wait<dynamic>([
        _service.lettersDashboard(),
        _service.letterTemplates(),
        _service.letterWorkflows(),
        _service.issuedLetters(),
        _service.bgvCases(),
        _service.bgvPolicy(),
      ]);
      _dashboard = Map<String, dynamic>.from(results[0] as Map);
      _templates = List<Map<String, dynamic>>.from(results[1] as List);
      _workflows = List<Map<String, dynamic>>.from(results[2] as List);
      _letters = List<Map<String, dynamic>>.from(results[3] as List);
      _cases = List<Map<String, dynamic>>.from(results[4] as List);
      _policy = Map<String, dynamic>.from(results[5] as Map);
    } catch (error) {
      _error = error.toString().replaceFirst('Exception: ', '');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        appBar: AppBar(title: Text('HR Letters & Background Verification')),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('HR Letters & Background Verification')),
        body: Center(
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.cloud_off_outlined, size: 42),
                  const SizedBox(height: 12),
                  Text(_error!, textAlign: TextAlign.center),
                  const SizedBox(height: 14),
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
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('HR Letters & Background Verification'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final desktop = constraints.maxWidth >= 1050;
          final content = IndexedStack(
            index: _section,
            children: [
              _dashboardView(),
              _templatesView(),
              _lettersView(),
              _bgvView(),
            ],
          );
          if (!desktop) return content;
          return Row(
            children: [
              NavigationRail(
                selectedIndex: _section,
                labelType: NavigationRailLabelType.all,
                onDestinationSelected: (value) => setState(() => _section = value),
                destinations: const [
                  NavigationRailDestination(
                    icon: Icon(Icons.space_dashboard_outlined),
                    selectedIcon: Icon(Icons.space_dashboard),
                    label: Text('Command Center'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.description_outlined),
                    selectedIcon: Icon(Icons.description),
                    label: Text('Templates'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.mark_email_read_outlined),
                    selectedIcon: Icon(Icons.mark_email_read),
                    label: Text('Letters'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.verified_user_outlined),
                    selectedIcon: Icon(Icons.verified_user),
                    label: Text('BGV'),
                  ),
                ],
              ),
              const VerticalDivider(width: 1),
              Expanded(child: content),
            ],
          );
        },
      ),
      bottomNavigationBar: MediaQuery.sizeOf(context).width >= 1050
          ? null
          : NavigationBar(
              selectedIndex: _section,
              onDestinationSelected: (value) => setState(() => _section = value),
              destinations: const [
                NavigationDestination(icon: Icon(Icons.space_dashboard_outlined), label: 'Dashboard'),
                NavigationDestination(icon: Icon(Icons.description_outlined), label: 'Templates'),
                NavigationDestination(icon: Icon(Icons.mark_email_read_outlined), label: 'Letters'),
                NavigationDestination(icon: Icon(Icons.verified_user_outlined), label: 'BGV'),
              ],
            ),
    );
  }

  Widget _dashboardView() {
    final letters = Map<String, dynamic>.from(_dashboard['letters'] as Map? ?? const {});
    final bgv = Map<String, dynamic>.from(_dashboard['bgv'] as Map? ?? const {});
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          _hero(),
          const SizedBox(height: 18),
          const Text('Digital HR Letters', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          LayoutBuilder(
            builder: (context, constraints) => Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _metric('Active templates', letters['templates_active'], Icons.description_outlined, constraints.maxWidth),
                _metric('Draft', letters['draft'], Icons.edit_note_outlined, constraints.maxWidth),
                _metric('Pending approval', letters['pending_approval'], Icons.approval_outlined, constraints.maxWidth),
                _metric('Approved', letters['approved'], Icons.task_alt_outlined, constraints.maxWidth),
                _metric('Issued', letters['issued'], Icons.mark_email_read_outlined, constraints.maxWidth),
                _metric('Acknowledgement due', letters['ack_pending'], Icons.pending_actions_outlined, constraints.maxWidth),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const Text('Background Verification', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final status in const ['NOT_STARTED', 'IN_PROGRESS', 'CLEAR', 'CONDITIONAL', 'FAILED', 'WAIVED'])
                    _statusChip(status, bgv[status] ?? 0),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _policyCard(),
        ],
      ),
    );
  }

  Widget _hero() => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF23395D), Color(0xFF4062A6)]),
          borderRadius: BorderRadius.circular(22),
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('ARI SMART RO • CORPORATE HR', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800)),
            SizedBox(height: 6),
            Text('Digital HR Letters + BGV Command Center', style: TextStyle(color: Colors.white, fontSize: 27, fontWeight: FontWeight.w900)),
            SizedBox(height: 6),
            Text('Versioned letters, approval control, immutable issue records, acknowledgements and auditable background verification.', style: TextStyle(color: Colors.white70)),
          ],
        ),
      );

  Widget _metric(String label, dynamic value, IconData icon, double width) {
    final cardWidth = width >= 1200 ? (width - 20) / 3 : width >= 700 ? (width - 10) / 2 : width;
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
                    Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _policyCard() {
    final mandatory = _policy['mandatory_before_ready'] == true;
    final required = List<String>.from((_policy['required_checks'] as List? ?? const []).map((e) => e.toString()));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(mandatory ? Icons.lock_outline : Icons.lock_open_outlined),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    mandatory ? 'BGV is mandatory before READY FOR DUTY' : 'BGV is optional before READY FOR DUTY',
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                ),
                if (_canBgvDecide)
                  OutlinedButton(
                    onPressed: () => _updatePolicy(!mandatory),
                    child: Text(mandatory ? 'MAKE OPTIONAL' : 'MAKE MANDATORY'),
                  ),
              ],
            ),
            if (required.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(spacing: 6, runSpacing: 6, children: required.map((e) => Chip(label: Text(e))).toList()),
            ],
            const SizedBox(height: 8),
            const Text('Admin READY override remains reasoned and audited; enabling BGV does not auto-mark anyone READY.'),
          ],
        ),
      ),
    );
  }

  Widget _templatesView() {
    final rows = _filterRows(_templates, ['name', 'letter_type', 'subject']);
    return _sectionList(
      title: 'Letter Templates',
      subtitle: 'Create new versions instead of overwriting issued history.',
      action: _canManage ? FilledButton.icon(onPressed: _createTemplate, icon: const Icon(Icons.add), label: const Text('NEW TEMPLATE')) : null,
      rows: rows,
      builder: (row) => Card(
        child: ListTile(
          leading: const CircleAvatar(child: Icon(Icons.description_outlined)),
          title: Text('${row['name'] ?? ''} • v${row['version'] ?? 1}', style: const TextStyle(fontWeight: FontWeight.w900)),
          subtitle: Text('${row['letter_type'] ?? ''}\n${row['subject'] ?? ''}'),
          isThreeLine: true,
          trailing: _canManage
              ? OutlinedButton(
                  onPressed: () => _templateToggle(row),
                  child: Text(row['is_active'] == true ? 'DEACTIVATE' : 'ACTIVATE'),
                )
              : _statusChip(row['is_active'] == true ? 'ACTIVE' : 'INACTIVE', null),
        ),
      ),
    );
  }

  Widget _lettersView() {
    final flows = _filterRows(_workflows, ['employee_name', 'employee_code', 'letter_type', 'subject', 'status']);
    final issued = _filterRows(_letters, ['employee_name', 'employee_code', 'letter_type', 'subject', 'acknowledgement_status']);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          _searchHeader('Letter Workflows', 'Draft, approval and issue control', _canManage ? FilledButton.icon(onPressed: _createWorkflow, icon: const Icon(Icons.add), label: const Text('NEW LETTER')) : null),
          const SizedBox(height: 12),
          if (flows.isEmpty) _empty('No letter workflows found.') else ...flows.map(_workflowCard),
          const SizedBox(height: 22),
          const Text('Issued Letters • Read Only', style: TextStyle(fontSize: 21, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          if (issued.isEmpty) _empty('No issued letters found.') else ...issued.map(_issuedCard),
        ],
      ),
    );
  }

  Widget _workflowCard(Map<String, dynamic> row) {
    final status = '${row['status'] ?? ''}'.toUpperCase();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text('${row['employee_name'] ?? ''} • ${row['employee_code'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900))),
                _statusChip(status, null),
              ],
            ),
            const SizedBox(height: 6),
            Text('${row['letter_type'] ?? ''} • ${row['subject'] ?? ''}'),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (_canManage && status == 'DRAFT') OutlinedButton(onPressed: () => _workflowAction(row, 'SUBMIT'), child: const Text('SUBMIT APPROVAL')),
                if (_canApprove && status == 'PENDING_APPROVAL') FilledButton(onPressed: () => _workflowAction(row, 'APPROVE'), child: const Text('APPROVE')),
                if (_canApprove && status == 'PENDING_APPROVAL') OutlinedButton(onPressed: () => _workflowAction(row, 'REJECT', reasonRequired: true), child: const Text('REJECT')),
                if (_canManage && status == 'APPROVED') FilledButton(onPressed: () => _workflowAction(row, 'ISSUE'), child: const Text('ISSUE IMMUTABLE LETTER')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _issuedCard(Map<String, dynamic> row) => Card(
        child: ExpansionTile(
          leading: const Icon(Icons.lock_outline),
          title: Text('${row['employee_name'] ?? ''} • ${row['letter_type'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900)),
          subtitle: Text('${row['subject'] ?? ''}'),
          trailing: _statusChip('${row['acknowledgement_status'] ?? 'PENDING'}', null),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            Align(alignment: Alignment.centerLeft, child: SelectableText('SHA-256: ${row['content_hash'] ?? ''}')),
            const SizedBox(height: 8),
            const Align(alignment: Alignment.centerLeft, child: Text('Issued snapshot is final and read-only.', style: TextStyle(fontWeight: FontWeight.w800))),
          ],
        ),
      );

  Widget _bgvView() {
    final rows = _filterRows(_cases, ['candidate_name', 'employee_name', 'employee_code', 'overall_status']);
    return _sectionList(
      title: 'Background Verification',
      subtitle: 'Candidate and employee checks with explicit final decision.',
      action: null,
      rows: rows,
      builder: _bgvCaseCard,
    );
  }

  Widget _bgvCaseCard(Map<String, dynamic> row) {
    final status = '${row['overall_status'] ?? 'NOT_STARTED'}'.toUpperCase();
    final checks = List<Map<String, dynamic>>.from((row['checks'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Card(
      child: ExpansionTile(
        title: Text(
          '${row['employee_name']?.toString().isNotEmpty == true ? row['employee_name'] : row['candidate_name'] ?? 'BGV Case'}',
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        subtitle: Text('Employee ${row['employee_code'] ?? '-'} • Case #${row['id']}'),
        trailing: _statusChip(status, null),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          const Align(alignment: Alignment.centerLeft, child: Text('Verification checklist', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900))),
          const SizedBox(height: 8),
          if (checks.isEmpty) const Align(alignment: Alignment.centerLeft, child: Text('No checks recorded yet.')),
          for (final check in checks)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fact_check_outlined),
              title: Text('${check['check_type'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800)),
              subtitle: Text('${check['notes'] ?? ''}'),
              trailing: _statusChip('${check['status'] ?? 'PENDING'}', null),
            ),
          if (_canBgvManage) ...[
            const Divider(),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: () => _addBgvCheck(row),
                icon: const Icon(Icons.add_task),
                label: const Text('ADD / UPDATE CHECK'),
              ),
            ),
          ],
          if (_canBgvDecide) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton(onPressed: () => _bgvDecision(row, 'CLEAR'), child: const Text('MARK CLEAR')),
                  OutlinedButton(onPressed: () => _bgvDecision(row, 'CONDITIONAL'), child: const Text('CONDITIONAL')),
                  OutlinedButton(onPressed: () => _bgvDecision(row, 'FAILED'), child: const Text('FAILED')),
                  OutlinedButton(onPressed: () => _bgvDecision(row, 'WAIVED'), child: const Text('WAIVE WITH REASON')),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _sectionList({required String title, required String subtitle, required Widget? action, required List<Map<String, dynamic>> rows, required Widget Function(Map<String, dynamic>) builder}) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            _searchHeader(title, subtitle, action),
            const SizedBox(height: 12),
            if (rows.isEmpty) _empty('Nothing to show yet.') else ...rows.map(builder),
          ],
        ),
      );

  Widget _searchHeader(String title, String subtitle, Widget? action) => LayoutBuilder(
        builder: (context, constraints) {
          final search = SizedBox(
            width: constraints.maxWidth >= 760 ? 340 : constraints.maxWidth,
            child: TextField(
              controller: _search,
              onChanged: (value) => setState(() => _query = value.trim().toLowerCase()),
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search / filter', border: OutlineInputBorder()),
            ),
          );
          return Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(width: constraints.maxWidth >= 760 ? 360 : constraints.maxWidth, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w900)), Text(subtitle)])),
              search,
              if (action != null) action,
            ],
          );
        },
      );

  List<Map<String, dynamic>> _filterRows(List<Map<String, dynamic>> rows, List<String> keys) {
    if (_query.isEmpty) return rows;
    return rows.where((row) => keys.any((key) => '${row[key] ?? ''}'.toLowerCase().contains(_query))).toList();
  }

  Widget _empty(String message) => Card(child: Padding(padding: const EdgeInsets.all(24), child: Center(child: Text(message))));

  Widget _statusChip(String status, dynamic value) => Chip(
        label: Text(value == null ? status.replaceAll('_', ' ') : '${status.replaceAll('_', ' ')} • $value'),
      );

  Future<String?> _askReason(String title, {bool required = true}) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(controller: controller, maxLines: 3, decoration: const InputDecoration(labelText: 'Reason / note', border: OutlineInputBorder())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          FilledButton(
            onPressed: () {
              final value = controller.text.trim();
              if (required && value.isEmpty) return;
              Navigator.pop(context, value);
            },
            child: const Text('CONFIRM'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<void> _workflowAction(Map<String, dynamic> row, String action, {bool reasonRequired = false}) async {
    String reason = '';
    if (reasonRequired || action == 'APPROVE') {
      final value = await _askReason('$action ${row['letter_type'] ?? 'letter'}', required: reasonRequired);
      if (value == null) return;
      reason = value;
    }
    try {
      await _service.letterWorkflowAction(row['id'] as int, action, reason: reason);
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  Future<void> _templateToggle(Map<String, dynamic> row) async {
    try {
      await _service.letterTemplateAction(row['id'] as int, row['is_active'] == true ? 'DEACTIVATE' : 'ACTIVATE');
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  Future<void> _createTemplate() async {
    final name = TextEditingController();
    final subject = TextEditingController();
    final body = TextEditingController();
    String type = 'APPOINTMENT';
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('New Letter Template Version'),
          content: SizedBox(
            width: 520,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(controller: name, decoration: const InputDecoration(labelText: 'Template name')),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: type,
                    decoration: const InputDecoration(labelText: 'Letter type'),
                    items: const ['APPOINTMENT', 'CONFIRMATION', 'PROMOTION', 'INCREMENT', 'WARNING', 'NOTICE', 'TRANSFER', 'SEPARATION', 'EXPERIENCE'].map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                    onChanged: (value) => setLocal(() => type = value ?? type),
                  ),
                  const SizedBox(height: 10),
                  TextField(controller: subject, decoration: const InputDecoration(labelText: 'Subject template')),
                  const SizedBox(height: 10),
                  TextField(controller: body, minLines: 5, maxLines: 9, decoration: const InputDecoration(labelText: 'Body template', hintText: 'Use {{employee_name}}, {{employee_id}}, {{effective_date}}', border: OutlineInputBorder())),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('CREATE VERSION')),
          ],
        ),
      ),
    );
    if (ok == true && name.text.trim().isNotEmpty && subject.text.trim().isNotEmpty && body.text.trim().isNotEmpty) {
      try {
        await _service.createLetterTemplate({'name': name.text.trim(), 'letter_type': type, 'subject': subject.text.trim(), 'body': body.text.trim(), 'is_active': true});
        await _load();
      } catch (error) {
        _snack(error);
      }
    }
    name.dispose();
    subject.dispose();
    body.dispose();
  }

  Future<void> _createWorkflow() async {
    if (_templates.where((e) => e['is_active'] == true).isEmpty) {
      _snack('Create an active letter template first.');
      return;
    }
    final employee = TextEditingController();
    final date = TextEditingController(text: DateTime.now().toIso8601String().split('T').first);
    int templateId = _templates.firstWhere((e) => e['is_active'] == true)['id'] as int;
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('Create HR Letter Draft'),
          content: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: employee, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Employee database ID')),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  initialValue: templateId,
                  decoration: const InputDecoration(labelText: 'Template'),
                  items: _templates.where((e) => e['is_active'] == true).map((e) => DropdownMenuItem(value: e['id'] as int, child: Text('${e['name']} • ${e['letter_type']} v${e['version']}'))).toList(),
                  onChanged: (value) => setLocal(() => templateId = value ?? templateId),
                ),
                const SizedBox(height: 10),
                TextField(controller: date, decoration: const InputDecoration(labelText: 'Effective date (YYYY-MM-DD)')),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('CREATE DRAFT')),
          ],
        ),
      ),
    );
    if (ok == true) {
      final employeeId = int.tryParse(employee.text.trim());
      if (employeeId == null) {
        _snack('Valid employee ID is required.');
      } else {
        try {
          await _service.createLetterWorkflow({'employee_id': employeeId, 'template_id': templateId, 'effective_date': date.text.trim(), 'context': <String, dynamic>{}});
          await _load();
        } catch (error) {
          _snack(error);
        }
      }
    }
    employee.dispose();
    date.dispose();
  }

  Future<void> _addBgvCheck(Map<String, dynamic> row) async {
    final notes = TextEditingController();
    final reference = TextEditingController();
    String type = 'IDENTITY';
    String status = 'IN_PROGRESS';
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: const Text('BGV Verification Check'),
          content: SizedBox(
            width: 500,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: type,
                  decoration: const InputDecoration(labelText: 'Check type'),
                  items: const ['IDENTITY', 'ADDRESS', 'EDUCATION', 'EMPLOYMENT', 'CRIMINAL_POLICE', 'REFERENCE'].map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                  onChanged: (value) => setLocal(() => type = value ?? type),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  initialValue: status,
                  decoration: const InputDecoration(labelText: 'Status'),
                  items: const ['PENDING', 'IN_PROGRESS', 'VERIFIED', 'FAILED', 'NOT_APPLICABLE'].map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                  onChanged: (value) => setLocal(() => status = value ?? status),
                ),
                const SizedBox(height: 10),
                TextField(controller: reference, decoration: const InputDecoration(labelText: 'Evidence / verification reference')),
                const SizedBox(height: 10),
                TextField(controller: notes, maxLines: 3, decoration: const InputDecoration(labelText: 'Authorized notes', border: OutlineInputBorder())),
                const SizedBox(height: 8),
                const Text('Do not enter full Aadhaar/PAN numbers. Sensitive identity values are not required here.'),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('SAVE CHECK')),
          ],
        ),
      ),
    );
    if (ok == true) {
      try {
        await _service.upsertBgvCheck(row['id'] as int, {'check_type': type, 'status': status, 'evidence_reference': reference.text.trim(), 'notes': notes.text.trim(), 'details': <String, dynamic>{}});
        await _load();
      } catch (error) {
        _snack(error);
      }
    }
    notes.dispose();
    reference.dispose();
  }

  Future<void> _bgvDecision(Map<String, dynamic> row, String decision) async {
    final reason = await _askReason('$decision BGV decision', required: decision == 'WAIVED' || decision != 'CLEAR');
    if (reason == null) return;
    try {
      await _service.decideBgv(row['id'] as int, decision, reason: reason);
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  Future<void> _updatePolicy(bool mandatory) async {
    final reason = await _askReason(mandatory ? 'Enable mandatory BGV READY gate?' : 'Make BGV optional?', required: false);
    if (reason == null) return;
    try {
      await _service.updateBgvPolicy(mandatoryBeforeReady: mandatory);
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  void _snack(Object message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message.toString().replaceFirst('Exception: ', ''))));
  }
}
