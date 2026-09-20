import 'package:flutter/material.dart';

import '../../services/training_service.dart';

class TrainingScreen extends StatefulWidget {
  const TrainingScreen({super.key});

  @override
  State<TrainingScreen> createState() => _TrainingScreenState();
}

class _TrainingScreenState extends State<TrainingScreen> {
  final _service = const TrainingService();
  bool _loading = true;
  Map<String, dynamic> _data = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _service.listAssignments();
      if (mounted) setState(() => _data = data);
    } catch (e) {
      if (mounted) _show(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _show(String text) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  @override
  Widget build(BuildContext context) {
    final scope = (_data['scope'] ?? '').toString();
    final rows = List<Map<String, dynamic>>.from(
      _data['assignments'] as List? ?? const [],
    );
    return Scaffold(
      appBar: AppBar(title: const Text('Employee Training')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(14),
                children: [
                  if (scope == 'ADMIN')
                    _AdminSummary(
                      summary: Map<String, dynamic>.from(
                        _data['summary'] as Map? ?? const {},
                      ),
                    ),
                  if (rows.isEmpty)
                    const Padding(
                      padding: EdgeInsets.only(top: 120),
                      child: Center(child: Text('No training assigned.')),
                    ),
                  ...rows.map(
                    (row) => _AssignmentCard(
                      row: row,
                      adminView: scope == 'ADMIN',
                      onOpen: scope == 'ADMIN'
                          ? null
                          : () async {
                              await Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => TrainingCourseScreen(
                                    assignmentId: (row['id'] as num).toInt(),
                                  ),
                                ),
                              );
                              await _load();
                            },
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _AdminSummary extends StatelessWidget {
  const _AdminSummary({required this.summary});
  final Map<String, dynamic> summary;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _metric('Total', summary['total']),
              _metric('Completed', summary['completed']),
              _metric('Overdue', summary['overdue']),
              _metric('Penalty review', summary['pending_penalty_review']),
              _metric('Due ≤2 days', summary['due_next_2_days']),
            ],
          ),
        ),
      );

  Widget _metric(String label, dynamic value) =>
      Chip(label: Text(label + ': ' + (value ?? 0).toString()));
}

class _AssignmentCard extends StatelessWidget {
  const _AssignmentCard({
    required this.row,
    required this.adminView,
    required this.onOpen,
  });

  final Map<String, dynamic> row;
  final bool adminView;
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    final status = (row['status'] ?? '').toString();
    final overdue = status == 'OVERDUE';
    final completed = status == 'COMPLETED';
    final title = adminView
        ? (row['employee_name'] ?? '').toString() +
            ' • ' +
            (row['title'] ?? '').toString()
        : (row['title'] ?? '').toString();

    return Card(
      child: ListTile(
        onTap: onOpen,
        leading: CircleAvatar(
          child: Icon(
            completed
                ? Icons.verified_rounded
                : overdue
                    ? Icons.warning_amber_rounded
                    : Icons.school_outlined,
          ),
        ),
        title: Text(title),
        subtitle: Text(
          [
            'Status: ' + status,
            'Progress: ' + (row['progress_percent'] ?? 0).toString() + '%',
            'Quiz: ' +
                (row['quiz_score'] ?? 0).toString() +
                '% / pass ' +
                (row['passing_score'] ?? 80).toString() +
                '%',
            'Due: ' + (row['due_date'] ?? '-').toString(),
            if (row['compliance_strike'] == true) 'Compliance strike recorded',
            if (row['penalty_created'] == true)
              'Penalty draft created for Admin review',
          ].join('\n'),
        ),
        trailing: onOpen == null ? null : const Icon(Icons.chevron_right),
      ),
    );
  }
}

class TrainingCourseScreen extends StatefulWidget {
  const TrainingCourseScreen({super.key, required this.assignmentId});
  final int assignmentId;

  @override
  State<TrainingCourseScreen> createState() => _TrainingCourseScreenState();
}

class _TrainingCourseScreenState extends State<TrainingCourseScreen> {
  final _service = const TrainingService();
  bool _loading = true;
  Map<String, dynamic> _course = {};
  final Map<int, String> _answers = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final row = await _service.detail(widget.assignmentId);
      if (mounted) setState(() => _course = row);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _completeLesson(int lessonId) async {
    try {
      await _service.completeLesson(widget.assignmentId, lessonId);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  Future<void> _submitQuiz() async {
    final questions = List<Map<String, dynamic>>.from(
      _course['questions'] as List? ?? const [],
    );
    if (_answers.length != questions.length) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please answer every quiz question.')),
      );
      return;
    }
    try {
      final result = await _service.submitQuiz(widget.assignmentId, _answers);
      if (!mounted) return;
      final passed = result['passed'] == true;
      final score = (result['score'] ?? 0).toString();
      final passScore = (result['passing_score'] ?? 80).toString();
      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(passed ? 'Training Passed' : 'Try Again'),
          content: Text(
            passed
                ? 'Great. You scored ' +
                    score +
                    '% and completed the mandatory training.'
                : 'You scored ' +
                    score +
                    '%. Passing score is ' +
                    passScore +
                    '%. Review the lessons and try again.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      _answers.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final lessons = List<Map<String, dynamic>>.from(
      _course['lessons'] as List? ?? const [],
    );
    final questions = List<Map<String, dynamic>>.from(
      _course['questions'] as List? ?? const [],
    );
    final allLessonsDone =
        lessons.isNotEmpty && lessons.every((row) => row['completed'] == true);
    final completed = _course['status'] == 'COMPLETED';

    return Scaffold(
      appBar: AppBar(title: Text((_course['title'] ?? 'Training').toString())),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(14),
              children: [
                Text(
                  (_course['description'] ?? '').toString(),
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 12),
                Text(
                  'Passing score: ' +
                      (_course['passing_score'] ?? 80).toString() +
                      '% • Due: ' +
                      (_course['due_date'] ?? '-').toString(),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 16),
                ...lessons.map(
                  (lesson) => Card(
                    child: ExpansionTile(
                      leading: Icon(
                        lesson['completed'] == true
                            ? Icons.check_circle
                            : Icons.menu_book_outlined,
                      ),
                      title: Text(
                        (lesson['order'] ?? '').toString() +
                            '. ' +
                            (lesson['title'] ?? '').toString(),
                      ),
                      subtitle: Text(
                        (lesson['key_takeaway'] ?? '').toString(),
                      ),
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text((lesson['content'] ?? '').toString()),
                        ),
                        if (lesson['completed'] != true)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                            child: FilledButton.icon(
                              onPressed: () => _completeLesson(
                                (lesson['id'] as num).toInt(),
                              ),
                              icon: const Icon(Icons.check),
                              label: const Text('MARK LESSON COMPLETE'),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                if (completed)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(18),
                      child: Row(
                        children: [
                          Icon(Icons.verified, size: 32),
                          SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Mandatory training completed successfully.',
                              style: TextStyle(fontWeight: FontWeight.w800),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else if (allLessonsDone) ...[
                  Text(
                    'Final Quiz',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  ...questions.map((q) {
                    final id = (q['id'] as num).toInt();
                    final options = Map<String, dynamic>.from(
                      q['options'] as Map? ?? const {},
                    );
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              (q['order'] ?? '').toString() +
                                  '. ' +
                                  (q['question'] ?? '').toString(),
                              style:
                                  const TextStyle(fontWeight: FontWeight.w800),
                            ),
                            ...options.entries.map(
                              (entry) => RadioListTile<String>(
                                value: entry.key,
                                groupValue: _answers[id],
                                onChanged: (value) => setState(
                                  () => _answers[id] = value!,
                                ),
                                title: Text(
                                  entry.key + '. ' + entry.value.toString(),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                  FilledButton.icon(
                    onPressed: _submitQuiz,
                    icon: const Icon(Icons.quiz_outlined),
                    label: const Text('SUBMIT FINAL QUIZ'),
                  ),
                ] else
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: Text(
                      'Complete every lesson to unlock the final quiz.',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
              ],
            ),
    );
  }
}
