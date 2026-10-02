import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/corporate_hrms_service.dart';

class RecruitmentScreen extends StatefulWidget {
  const RecruitmentScreen({super.key});

  @override
  State<RecruitmentScreen> createState() => _RecruitmentScreenState();
}

class _RecruitmentScreenState extends State<RecruitmentScreen> {
  final _service = CorporateHrmsService();
  final _search = TextEditingController();

  bool _loading = true;
  String? _error;
  String _role = '';
  String _query = '';
  int _section = 0;
  Map<String, dynamic> _summary = const {};
  List<Map<String, dynamic>> _requisitions = const [];
  List<Map<String, dynamic>> _jobs = const [];
  List<Map<String, dynamic>> _candidates = const [];
  List<Map<String, dynamic>> _applications = const [];
  List<Map<String, dynamic>> _interviews = const [];
  List<Map<String, dynamic>> _offers = const [];

  bool get _canManage => const {'ADMIN', 'OFFICE'}.contains(_role);
  bool get _canApprove => _role == 'ADMIN';
  bool get _canInterview => const {'ADMIN', 'MANAGER'}.contains(_role);
  bool get _canConvert => _role == 'ADMIN';

  static const _stages = [
    'APPLIED',
    'SCREENING',
    'INTERVIEW',
    'SELECTED',
    'OFFERED',
    'JOINED',
  ];

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
      final values = await Future.wait([
        _service.recruitmentSummary(),
        _service.recruitmentRequisitions(),
        _service.recruitmentJobs(),
        _service.recruitmentCandidates(),
        _service.recruitmentApplications(),
        _service.recruitmentInterviews(),
        _service.recruitmentOffers(),
      ]);
      _summary = Map<String, dynamic>.from(values[0] as Map);
      _requisitions = List<Map<String, dynamic>>.from(values[1] as List);
      _jobs = List<Map<String, dynamic>>.from(values[2] as List);
      _candidates = List<Map<String, dynamic>>.from(values[3] as List);
      _applications = List<Map<String, dynamic>>.from(values[4] as List);
      _interviews = List<Map<String, dynamic>>.from(values[5] as List);
      _offers = List<Map<String, dynamic>>.from(values[6] as List);
    } catch (error) {
      _error = error.toString().replaceFirst('Exception: ', '');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Talent Acquisition'),
        actions: [
          IconButton(onPressed: _load, tooltip: 'Refresh', icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _errorView()
              : LayoutBuilder(builder: _workspace),
    );
  }

  Widget _errorView() => Center(
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
                  const Text('Recruitment workspace could not load', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
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

  Widget _workspace(BuildContext context, BoxConstraints constraints) {
    final desktop = constraints.maxWidth >= 1050;
    final sections = [
      _dashboard(),
      _requisitionPage(),
      _pipelinePage(),
      _interviewPage(),
      _offerPage(),
    ];
    final destinations = const [
      NavigationRailDestination(icon: Icon(Icons.space_dashboard_outlined), selectedIcon: Icon(Icons.space_dashboard), label: Text('Dashboard')),
      NavigationRailDestination(icon: Icon(Icons.assignment_outlined), selectedIcon: Icon(Icons.assignment), label: Text('Requisitions')),
      NavigationRailDestination(icon: Icon(Icons.account_tree_outlined), selectedIcon: Icon(Icons.account_tree), label: Text('Pipeline')),
      NavigationRailDestination(icon: Icon(Icons.record_voice_over_outlined), selectedIcon: Icon(Icons.record_voice_over), label: Text('Interviews')),
      NavigationRailDestination(icon: Icon(Icons.description_outlined), selectedIcon: Icon(Icons.description), label: Text('Offers')),
    ];
    return Column(
      children: [
        _topBar(),
        const Divider(height: 1),
        Expanded(
          child: Row(
            children: [
              if (desktop)
                NavigationRail(
                  selectedIndex: _section,
                  labelType: NavigationRailLabelType.all,
                  destinations: destinations,
                  onDestinationSelected: (value) => setState(() => _section = value),
                ),
              if (desktop) const VerticalDivider(width: 1),
              Expanded(child: sections[_section]),
            ],
          ),
        ),
        if (!desktop)
          NavigationBar(
            selectedIndex: _section,
            onDestinationSelected: (value) => setState(() => _section = value),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.space_dashboard_outlined), label: 'Dashboard'),
              NavigationDestination(icon: Icon(Icons.assignment_outlined), label: 'Requests'),
              NavigationDestination(icon: Icon(Icons.account_tree_outlined), label: 'Pipeline'),
              NavigationDestination(icon: Icon(Icons.record_voice_over_outlined), label: 'Interview'),
              NavigationDestination(icon: Icon(Icons.description_outlined), label: 'Offers'),
            ],
          ),
      ],
    );
  }

  Widget _topBar() => Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Row(
          children: [
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Recruitment Command Center', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
                  Text('Manpower approval → interview → offer → joining conversion'),
                ],
              ),
            ),
            if (_canManage)
              FilledButton.icon(
                onPressed: _newRequisition,
                icon: const Icon(Icons.add),
                label: const Text('MANPOWER REQUEST'),
              ),
          ],
        ),
      );

  Widget _dashboard() {
    final req = Map<String, dynamic>.from(_summary['requisitions'] as Map? ?? const {});
    final jobs = Map<String, dynamic>.from(_summary['jobs'] as Map? ?? const {});
    final ats = Map<String, dynamic>.from(_summary['ats'] as Map? ?? const {});
    final queue = Map<String, dynamic>.from(_summary['action_queue'] as Map? ?? const {});
    final metrics = <(String, dynamic, IconData)>[
      ('Open requisitions', req['total'], Icons.assignment_outlined),
      ('Pending approvals', req['pending_approval'], Icons.approval_outlined),
      ('Open vacancies', jobs['open_vacancies'], Icons.work_outline),
      ('Screening', ats['screening'], Icons.manage_search_outlined),
      ('Interviews due', ats['interviews_due'], Icons.record_voice_over_outlined),
      ('Feedback pending', ats['interview_feedback_pending'], Icons.rate_review_outlined),
      ('Selected • no offer', ats['selected_awaiting_offer'], Icons.person_search_outlined),
      ('Offer approvals', ats['offers_awaiting_approval'], Icons.fact_check_outlined),
      ('Awaiting response', ats['offers_awaiting_response'], Icons.mark_email_unread_outlined),
      ('Accepted • joining', ats['accepted_awaiting_conversion'], Icons.how_to_reg_outlined),
      ('Joined this month', ats['joined_this_month'], Icons.celebration_outlined),
    ];
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF173B67), Color(0xFF245E9E)]),
              borderRadius: BorderRadius.circular(22),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('ARI SMART RO • TALENT ACQUISITION', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800)),
                SizedBox(height: 6),
                Text('Hire with control, evidence and auditability.', style: TextStyle(color: Colors.white, fontSize: 27, fontWeight: FontWeight.w900)),
                SizedBox(height: 6),
                Text('No silent stage jumps. Interviews, selection, offers and employee conversion follow controlled backend gates.', style: TextStyle(color: Colors.white70)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth;
              final columns = width >= 1200 ? 4 : width >= 700 ? 2 : 1;
              final cardWidth = (width - ((columns - 1) * 10)) / columns;
              return Wrap(
                spacing: 10,
                runSpacing: 10,
                children: metrics.map((m) => SizedBox(width: cardWidth, child: _metric(m.$1, m.$2, m.$3))).toList(),
              );
            },
          ),
          const SizedBox(height: 18),
          const Text('Recruitment action queue', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _queueChip('Requisition approval', queue['requisition_approval_due']),
                  _queueChip('Interview overdue', queue['interview_overdue']),
                  _queueChip('Feedback pending', queue['feedback_pending']),
                  _queueChip('Offer approval', queue['offer_approval_pending']),
                  _queueChip('Offer expiry', queue['offer_expiry_approaching']),
                  _queueChip('Accepted waiting joining', queue['accepted_waiting_joining']),
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          const Text('Pipeline health', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          _pipelineSummary(),
        ],
      ),
    );
  }

  Widget _metric(String label, dynamic value, IconData icon) => Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(child: Icon(icon)),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${value ?? 0}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
                Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
              ])),
            ],
          ),
        ),
      );

  Widget _queueChip(String label, dynamic value) => Chip(label: Text('$label • ${value ?? 0}'));

  Widget _pipelineSummary() {
    final pipeline = Map<String, dynamic>.from(_summary['pipeline'] as Map? ?? const {});
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            ..._stages.map((stage) => _stageChip(stage, pipeline[stage] ?? 0)),
            _stageChip('REJECTED', pipeline['REJECTED'] ?? 0),
            _stageChip('WITHDRAWN', pipeline['WITHDRAWN'] ?? 0),
          ],
        ),
      ),
    );
  }

  Widget _stageChip(String stage, dynamic count) => Chip(
        avatar: CircleAvatar(radius: 12, child: Text('$count', style: const TextStyle(fontSize: 10))),
        label: Text(stage.replaceAll('_', ' ')),
      );

  Widget _requisitionPage() => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _sectionHeader('Manpower Requisitions', 'Controlled manpower demand and approvals.',
                action: _canManage ? FilledButton.icon(onPressed: _newRequisition, icon: const Icon(Icons.add), label: const Text('NEW REQUEST')) : null),
            const SizedBox(height: 12),
            if (_requisitions.isEmpty) _empty('No manpower requisitions yet.'),
            ..._requisitions.map(_requisitionCard),
            const SizedBox(height: 18),
            const Text('Job Openings', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            if (_jobs.isEmpty) _empty('No active job openings yet.'),
            ..._jobs.map(_jobCard),
          ],
        ),
      );

  Widget _requisitionCard(Map<String, dynamic> row) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Expanded(child: Text('${row['job_title'] ?? '-'}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900))),
              _status('${row['status'] ?? '-'}'),
            ]),
            const SizedBox(height: 6),
            Text('${row['department'] ?? '-'} • ${row['positions'] ?? 0} position(s) • ${row['employment_type'] ?? '-'}'),
            Text('${row['location'] ?? '-'} • Target: ${row['target_joining_date'] ?? '-'}'),
            if ((row['justification'] ?? '').toString().isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text('${row['justification']}')),
            if (_canApprove && '${row['status']}'.toUpperCase() == 'PENDING_APPROVAL')
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Wrap(spacing: 8, children: [
                  OutlinedButton(onPressed: () => _requisitionDecision(row, 'REJECT'), child: const Text('REJECT')),
                  FilledButton(onPressed: () => _requisitionDecision(row, 'APPROVE'), child: const Text('APPROVE')),
                ]),
              ),
          ]),
        ),
      );

  Widget _jobCard(Map<String, dynamic> row) => Card(
        child: ListTile(
          leading: const CircleAvatar(child: Icon(Icons.work_outline)),
          title: Text('${row['title'] ?? '-'}', style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: Text('Vacancies: ${row['vacancies'] ?? 0}\n${row['requirements'] ?? ''}'),
          trailing: _status('${row['status'] ?? '-'}'),
        ),
      );

  Widget _pipelinePage() {
    final filtered = _applications.where((row) {
      final q = _query.trim().toLowerCase();
      if (q.isEmpty) return true;
      return [row['candidate_name'], row['job_title'], row['stage']].any((v) => '${v ?? ''}'.toLowerCase().contains(q));
    }).toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionHeader('Candidate Pipeline', 'APPLIED → SCREENING → INTERVIEW → SELECTED → OFFERED → JOINED'),
          const SizedBox(height: 10),
          TextField(
            controller: _search,
            onChanged: (value) => setState(() => _query = value),
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search candidate, role or stage...', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          LayoutBuilder(builder: (context, constraints) {
            if (constraints.maxWidth >= 980) return _pipelineDesktop(filtered);
            return Column(children: filtered.map(_applicationCard).toList());
          }),
          if (filtered.isEmpty) _empty('No candidates match this filter.'),
        ],
      ),
    );
  }

  Widget _pipelineDesktop(List<Map<String, dynamic>> rows) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ..._stages.map((stage) => _pipelineColumn(stage, rows.where((e) => '${e['stage']}'.toUpperCase() == stage).toList())),
            _pipelineColumn('REJECTED', rows.where((e) => '${e['stage']}'.toUpperCase() == 'REJECTED').toList()),
            _pipelineColumn('WITHDRAWN', rows.where((e) => '${e['stage']}'.toUpperCase() == 'WITHDRAWN').toList()),
          ],
        ),
      );

  Widget _pipelineColumn(String stage, List<Map<String, dynamic>> rows) => SizedBox(
        width: 250,
        child: Padding(
          padding: const EdgeInsets.only(right: 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [Expanded(child: Text(stage, style: const TextStyle(fontWeight: FontWeight.w900))), CircleAvatar(radius: 12, child: Text('${rows.length}', style: const TextStyle(fontSize: 10)))]),
            const SizedBox(height: 8),
            ...rows.map(_applicationCard),
          ]),
        ),
      );

  Widget _applicationCard(Map<String, dynamic> row) {
    final stage = '${row['stage'] ?? '-'}'.toUpperCase();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('${row['candidate_name'] ?? '-'}', style: const TextStyle(fontWeight: FontWeight.w900)),
          Text('${row['job_title'] ?? '-'}'),
          const SizedBox(height: 6),
          Align(alignment: Alignment.centerLeft, child: _status(stage)),
          if (_canApprove && stage == 'INTERVIEW')
            Wrap(spacing: 6, children: [
              TextButton(onPressed: () => _candidateDecision(row, 'REJECT'), child: const Text('REJECT')),
              FilledButton.tonal(onPressed: () => _candidateDecision(row, 'SELECT'), child: const Text('SELECT')),
            ]),
          if (_canApprove && stage == 'REJECTED')
            TextButton(onPressed: () => _candidateDecision(row, 'REOPEN'), child: const Text('REOPEN')),
          if (_canConvert && stage == 'OFFERED')
            TextButton(onPressed: () => _convertIfAccepted(row), child: const Text('CHECK / CONVERT JOINING')),
          if (row['converted_employee_id'] != null)
            Text('Employee ID: ${row['converted_employee_id']} • ONBOARDING / CREATED', style: const TextStyle(fontWeight: FontWeight.w700)),
        ]),
      ),
    );
  }

  Widget _interviewPage() {
    final rows = _interviews.where((row) {
      final q = _query.trim().toLowerCase();
      if (q.isEmpty) return true;
      return [row['candidate_name'], row['job_title'], row['round_type'], row['status']].any((v) => '${v ?? ''}'.toLowerCase().contains(q));
    }).toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionHeader('Interview Schedule', 'Assigned interview rounds with final feedback evidence.'),
          const SizedBox(height: 10),
          TextField(
            onChanged: (value) => setState(() => _query = value),
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search interviews...', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 10),
          if (rows.isEmpty) _empty('No interviews are assigned or scheduled.'),
          ...rows.map(_interviewCard),
        ],
      ),
    );
  }

  Widget _interviewCard(Map<String, dynamic> row) {
    final completed = '${row['status']}'.toUpperCase() == 'COMPLETED';
    final feedbackSubmitted = row['feedback_submitted'] == true;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text('${row['candidate_name'] ?? '-'} • ${row['job_title'] ?? '-'}', style: const TextStyle(fontWeight: FontWeight.w900))),
            _status('${row['status'] ?? '-'}'),
          ]),
          Text('Round ${row['round_number'] ?? '-'} • ${row['round_type'] ?? '-'}'),
          Text('${row['scheduled_at'] ?? '-'} • ${row['location'] ?? row['meeting_reference'] ?? '-'}'),
          Text('Interviewer: ${row['interviewer_name'] ?? '-'}'),
          if (feedbackSubmitted)
            const Padding(padding: EdgeInsets.only(top: 6), child: Text('Feedback submitted • FINAL / READ ONLY', style: TextStyle(fontWeight: FontWeight.w800))),
          if (_canInterview && !completed && !feedbackSubmitted)
            Align(alignment: Alignment.centerLeft, child: FilledButton.tonal(onPressed: () => _feedback(row), child: const Text('SUBMIT FEEDBACK'))),
          if (_canInterview && !completed && feedbackSubmitted)
            Align(alignment: Alignment.centerLeft, child: FilledButton(onPressed: () => _interviewAction(row, 'COMPLETE'), child: const Text('COMPLETE INTERVIEW'))),
        ]),
      ),
    );
  }

  Widget _offerPage() => RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _sectionHeader('Offers & Joining Conversion', 'Draft → approval → issue → candidate response → employee onboarding.'),
            const SizedBox(height: 10),
            if (_offers.isEmpty) _empty('No offers yet. Selected candidates are ready for controlled offer creation.'),
            ..._offers.map(_offerCard),
          ],
        ),
      );

  Widget _offerCard(Map<String, dynamic> row) {
    final status = '${row['status'] ?? '-'}'.toUpperCase();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text('${row['candidate_name'] ?? '-'} • ${row['job_title'] ?? '-'}', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900))),
            _status(status),
          ]),
          Text('${row['department'] ?? '-'} • ${row['designation'] ?? '-'} • ${row['employment_type'] ?? '-'}'),
          Text('Joining: ${row['proposed_joining_date'] ?? '-'} • Work location: ${row['work_location'] ?? '-'}'),
          Text('Compensation: ₹${row['compensation'] ?? 0} • Valid till: ${row['validity_date'] ?? '-'}'),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            if (_canManage && status == 'DRAFT') FilledButton.tonal(onPressed: () => _offerAction(row, 'SUBMIT'), child: const Text('SUBMIT APPROVAL')),
            if (_canApprove && status == 'PENDING_APPROVAL') FilledButton(onPressed: () => _offerAction(row, 'APPROVE'), child: const Text('APPROVE')),
            if (_canManage && status == 'APPROVED') FilledButton(onPressed: () => _offerAction(row, 'ISSUE'), child: const Text('ISSUE OFFER')),
            if (_canManage && status == 'ISSUED') ...[
              FilledButton.tonal(onPressed: () => _offerAction(row, 'ACCEPT'), child: const Text('RECORD ACCEPTANCE')),
              OutlinedButton(onPressed: () => _offerAction(row, 'DECLINE'), child: const Text('RECORD DECLINE')),
            ],
            if (_canConvert && status == 'ACCEPTED') FilledButton.icon(onPressed: () => _convertOffer(row), icon: const Icon(Icons.how_to_reg), label: const Text('CONVERT TO EMPLOYEE')),
          ]),
          if (status == 'ISSUED' || status == 'ACCEPTED' || status == 'DECLINED')
            const Padding(padding: EdgeInsets.only(top: 8), child: Text('Issued offer terms are historical and immutable.', style: TextStyle(fontWeight: FontWeight.w700))),
        ]),
      ),
    );
  }

  Widget _sectionHeader(String title, String subtitle, {Widget? action}) => Row(
        children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
            Text(subtitle),
          ])),
          if (action != null) action,
        ],
      );

  Widget _empty(String text) => Card(
        child: Padding(
          padding: const EdgeInsets.all(22),
          child: Center(child: Text(text)),
        ),
      );

  Widget _status(String text) => Chip(
        visualDensity: VisualDensity.compact,
        label: Text(text.replaceAll('_', ' ')),
      );

  Future<void> _newRequisition() async {
    final department = TextEditingController();
    final title = TextEditingController();
    final positions = TextEditingController(text: '1');
    final location = TextEditingController();
    final justification = TextEditingController();
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New manpower requisition'),
        content: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: department, decoration: const InputDecoration(labelText: 'Department')),
              TextField(controller: title, decoration: const InputDecoration(labelText: 'Job title')),
              TextField(controller: positions, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Positions')),
              TextField(controller: location, decoration: const InputDecoration(labelText: 'Location')),
              TextField(controller: justification, maxLines: 3, decoration: const InputDecoration(labelText: 'Business justification')),
            ]),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          FilledButton(onPressed: () => Navigator.pop(context, {
            'department': department.text.trim(),
            'job_title': title.text.trim(),
            'positions': int.tryParse(positions.text) ?? 1,
            'location': location.text.trim(),
            'justification': justification.text.trim(),
            'employment_type': 'PROBATION',
          }), child: const Text('SUBMIT')),
        ],
      ),
    );
    department.dispose(); title.dispose(); positions.dispose(); location.dispose(); justification.dispose();
    if (result == null) return;
    try {
      await _service.createRequisition(result);
      await _load();
    } catch (error) { _showError(error); }
  }

  Future<void> _requisitionDecision(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    final reason = action == 'REJECT' ? await _reason('Reject requisition', 'Rejection reason') : '';
    if (action == 'REJECT' && (reason == null || reason.trim().isEmpty)) return;
    try {
      await _service.requisitionAction(id, action, reason: reason ?? '');
      await _load();
    } catch (error) { _showError(error); }
  }

  Future<void> _candidateDecision(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    final reason = await _reason('$action candidate', action == 'SELECT' ? 'Selection decision note' : '$action reason');
    if (reason == null || reason.trim().isEmpty) return;
    try {
      await _service.recruitmentDecision(id, action, reason: reason);
      await _load();
    } catch (error) { _showError(error); }
  }

  Future<void> _feedback(Map<String, dynamic> row) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    int rating = 4;
    String recommendation = 'HIRE';
    final strengths = TextEditingController();
    final concerns = TextEditingController();
    final notes = TextEditingController();
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setLocal) => AlertDialog(
        title: const Text('Final interview feedback'),
        content: SizedBox(width: 520, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButtonFormField<int>(initialValue: rating, decoration: const InputDecoration(labelText: 'Rating'), items: [1,2,3,4,5].map((e) => DropdownMenuItem(value: e, child: Text('$e / 5'))).toList(), onChanged: (v) => setLocal(() => rating = v ?? 4)),
          DropdownButtonFormField<String>(initialValue: recommendation, decoration: const InputDecoration(labelText: 'Recommendation'), items: const ['STRONG_HIRE','HIRE','HOLD','NO_HIRE'].map((e) => DropdownMenuItem(value: e, child: Text(e.replaceAll('_', ' ')))).toList(), onChanged: (v) => setLocal(() => recommendation = v ?? 'HIRE')),
          TextField(controller: strengths, decoration: const InputDecoration(labelText: 'Strengths'), maxLines: 2),
          TextField(controller: concerns, decoration: const InputDecoration(labelText: 'Concerns'), maxLines: 2),
          TextField(controller: notes, decoration: const InputDecoration(labelText: 'Notes'), maxLines: 3),
          const SizedBox(height: 10),
          const Text('Submitting makes this feedback final and immutable.', style: TextStyle(fontWeight: FontWeight.w800)),
        ]))),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          FilledButton(onPressed: () => Navigator.pop(context, {'rating': rating, 'recommendation': recommendation, 'strengths': strengths.text.trim(), 'concerns': concerns.text.trim(), 'notes': notes.text.trim()}), child: const Text('SUBMIT FINAL')),
        ],
      )),
    );
    strengths.dispose(); concerns.dispose(); notes.dispose();
    if (result == null) return;
    try {
      await _service.submitInterviewFeedback(id, result);
      await _load();
    } catch (error) { _showError(error); }
  }

  Future<void> _interviewAction(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    try {
      await _service.interviewAction(id, action);
      await _load();
    } catch (error) { _showError(error); }
  }

  Future<void> _offerAction(Map<String, dynamic> row, String action) async {
    final id = (row['id'] as num?)?.toInt();
    if (id == null) return;
    String reason = '';
    if (const {'APPROVE','ACCEPT','DECLINE'}.contains(action)) {
      final value = await _reason('$action offer', action == 'APPROVE' ? 'Approval note' : 'Response evidence / note');
      if (value == null) return;
      reason = value;
    }
    try {
      await _service.offerAction(id, action, reason: reason, evidence: action == 'ACCEPT' || action == 'DECLINE' ? {'recorded_in': 'HRMS', 'method': 'HR_RECORDED'} : const {});
      await _load();
    } catch (error) { _showError(error); }
  }

  Future<void> _convertOffer(Map<String, dynamic> row) async {
    final appId = (row['application_id'] as num?)?.toInt();
    if (appId == null) return;
    await _convert(appId);
  }

  Future<void> _convertIfAccepted(Map<String, dynamic> row) async {
    final appId = (row['id'] as num?)?.toInt();
    if (appId == null) return;
    final offer = _offers.cast<Map<String, dynamic>?>().firstWhere((e) => e?['application_id'] == appId && '${e?['status']}'.toUpperCase() == 'ACCEPTED', orElse: () => null);
    if (offer == null) {
      _showMessage('Accepted offer is required before employee conversion.');
      return;
    }
    await _convert(appId);
  }

  Future<void> _convert(int applicationId) async {
    try {
      final result = await _service.convertCandidate(applicationId);
      _showMessage('Employee ${result['employee_code'] ?? result['employee_id']} created • ONBOARDING / CREATED');
      await _load();
    } catch (error) {
      final text = error.toString();
      if (text.toLowerCase().contains('capacity')) {
        final reason = await _reason('Admin vacancy override', 'Mandatory override reason');
        if (reason == null || reason.trim().isEmpty) return;
        try {
          final result = await _service.convertCandidate(applicationId, capacityOverride: true, overrideReason: reason);
          _showMessage('Employee ${result['employee_code'] ?? result['employee_id']} created with audited capacity override.');
          await _load();
        } catch (second) { _showError(second); }
      } else {
        _showError(error);
      }
    }
  }

  Future<String?> _reason(String title, String label) async {
    final controller = TextEditingController();
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(controller: controller, autofocus: true, maxLines: 3, decoration: InputDecoration(labelText: label, border: const OutlineInputBorder())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          FilledButton(onPressed: () => Navigator.pop(context, controller.text.trim()), child: const Text('CONFIRM')),
        ],
      ),
    );
    controller.dispose();
    return value;
  }

  void _showError(Object error) => _showMessage(error.toString().replaceFirst('Exception: ', ''));

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }
}
