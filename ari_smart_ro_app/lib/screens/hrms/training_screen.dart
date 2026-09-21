import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

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
                      onOpen: () async {
                        await Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => TrainingCourseScreen(
                              assignmentId: (row['id'] as num).toInt(),
                              adminView: scope == 'ADMIN',
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
  const TrainingCourseScreen({
    super.key,
    required this.assignmentId,
    this.adminView = false,
  });
  final int assignmentId;
  final bool adminView;

  @override
  State<TrainingCourseScreen> createState() => _TrainingCourseScreenState();
}

class _TrainingCourseScreenState extends State<TrainingCourseScreen> {
  final _service = const TrainingService();
  bool _loading = true;
  Map<String, dynamic> _course = {};
  final Map<int, String> _answers = {};
  final Set<int> _watchedVideos = {};

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

  Future<void> _completeLesson(int lessonId, {required bool hasVideo}) async {
    try {
      await _service.completeLesson(
        widget.assignmentId,
        lessonId,
        videoWatched: !hasVideo || _watchedVideos.contains(lessonId),
      );
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  Future<void> _reviewLesson(Map<String, dynamic> lesson) async {
    int behaviour = ((lesson['trainer_review'] as Map?)?['behaviour_score'] as num?)?.toInt() ?? 3;
    int communication = ((lesson['trainer_review'] as Map?)?['communication_score'] as num?)?.toInt() ?? 3;
    int knowledge = ((lesson['trainer_review'] as Map?)?['knowledge_score'] as num?)?.toInt() ?? 3;
    final existing = Map<String, dynamic>.from(
      lesson['trainer_review'] as Map? ?? const <String, dynamic>{},
    );
    final strengths = TextEditingController(text: (existing['strengths'] ?? '').toString());
    final gaps = TextEditingController(text: (existing['gaps'] ?? '').toString());
    final coaching = TextEditingController(text: (existing['coaching_action'] ?? '').toString());
    final notes = TextEditingController(text: (existing['notes'] ?? '').toString());

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Trainer Review • Day ${lesson['day_number'] ?? lesson['order']}'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  '1 = needs urgent coaching • 5 = excellent',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                _ScorePicker(
                  label: 'Behaviour / व्यवहार',
                  value: behaviour,
                  onChanged: (v) => setDialogState(() => behaviour = v),
                ),
                _ScorePicker(
                  label: 'Communication / संवाद',
                  value: communication,
                  onChanged: (v) => setDialogState(() => communication = v),
                ),
                _ScorePicker(
                  label: 'Knowledge / ज्ञान',
                  value: knowledge,
                  onChanged: (v) => setDialogState(() => knowledge = v),
                ),
                TextField(
                  controller: strengths,
                  decoration: const InputDecoration(labelText: 'Strengths / अच्छाइयाँ'),
                  minLines: 2,
                  maxLines: 3,
                ),
                TextField(
                  controller: gaps,
                  decoration: const InputDecoration(labelText: 'Gaps / कमियाँ'),
                  minLines: 2,
                  maxLines: 3,
                ),
                TextField(
                  controller: coaching,
                  decoration: const InputDecoration(
                    labelText: 'What Admin should teach next / सुधार कैसे करें',
                  ),
                  minLines: 2,
                  maxLines: 4,
                ),
                TextField(
                  controller: notes,
                  decoration: const InputDecoration(labelText: 'Trainer notes'),
                  minLines: 2,
                  maxLines: 4,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Save Review'),
            ),
          ],
        ),
      ),
    );

    if (save == true) {
      try {
        await _service.saveTrainerReview(
          widget.assignmentId,
          (lesson['id'] as num).toInt(),
          behaviourScore: behaviour,
          communicationScore: communication,
          knowledgeScore: knowledge,
          strengths: strengths.text,
          gaps: gaps.text,
          coachingAction: coaching.text,
          notes: notes.text,
        );
        await _load();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Trainer review saved.')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
          );
        }
      }
    }
    strengths.dispose();
    gaps.dispose();
    coaching.dispose();
    notes.dispose();
  }


  Future<void> _issueCertificate() async {
    try {
      await _service.issueCertificate(widget.assignmentId);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('ARI certification issued successfully.')),
        );
      }
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
                  '30-day plan: ' +
                      (_course['planned_days'] ?? 0).toString() +
                      ' days • ' +
                      (_course['planned_minutes'] ?? 0).toString() +
                      ' planned minutes • 60 min/day\nPassing score: ' +
                      (_course['passing_score'] ?? 80).toString() +
                      '% • Due: ' +
                      (_course['due_date'] ?? '-').toString(),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 16),
                _CertificationCard(
                  certification: Map<String, dynamic>.from(
                    _course['certification'] as Map? ?? const <String, dynamic>{},
                  ),
                  adminView: widget.adminView,
                  onIssue: _issueCertificate,
                ),
                const SizedBox(height: 16),
                ...lessons.map(
                  (lesson) {
                    final lessonId = (lesson['id'] as num).toInt();
                    final videoAsset = (lesson['video_asset'] ?? '').toString();
                    final hasVideo = videoAsset.isNotEmpty;
                    return Card(
                    child: ExpansionTile(
                      leading: Icon(
                        lesson['completed'] == true
                            ? Icons.check_circle
                            : Icons.menu_book_outlined,
                      ),
                      title: Text((lesson['title'] ?? '').toString()),
                      subtitle: Text(
                        'Day ' +
                            (lesson['day_number'] ?? lesson['order'] ?? '').toString() +
                            ' • ' +
                            (lesson['duration_minutes'] ?? 60).toString() +
                            ' min\n' +
                            (lesson['key_takeaway'] ?? '').toString(),
                      ),
                      children: [
                        if (hasVideo)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                            child: _TrainingVideo(
                              assetPath: videoAsset,
                              onCompleted: () => setState(
                                () => _watchedVideos.add(lessonId),
                              ),
                            ),
                          ),
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text((lesson['content'] ?? '').toString()),
                        ),
                        if ((lesson['practice_task'] ?? '').toString().isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                            child: Text(
                              'Practice / अभ्यास:\n' + (lesson['practice_task'] ?? '').toString(),
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                        if (widget.adminView &&
                            (lesson['trainer_script'] ?? '').toString().isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                            child: Text(
                              'Trainer script / Admin क्या सिखाए:\n' +
                                  (lesson['trainer_script'] ?? '').toString(),
                            ),
                          ),
                        if (widget.adminView)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                            child: FilledButton.tonalIcon(
                              onPressed: () => _reviewLesson(lesson),
                              icon: const Icon(Icons.rate_review_outlined),
                              label: Text(
                                lesson['trainer_review'] == null
                                    ? 'ADD TRAINER REVIEW'
                                    : 'UPDATE TRAINER REVIEW',
                              ),
                            ),
                          ),
                        if (!widget.adminView && lesson['completed'] != true)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                            child: FilledButton.icon(
                              onPressed: hasVideo &&
                                      !_watchedVideos.contains(lessonId)
                                  ? null
                                  : () => _completeLesson(
                                        lessonId,
                                        hasVideo: hasVideo,
                                      ),
                              icon: const Icon(Icons.check),
                              label: Text(
                                hasVideo && !_watchedVideos.contains(lessonId)
                                    ? 'वीडियो पूरा देखें / WATCH VIDEO'
                                    : 'पूरा हुआ / MARK COMPLETE',
                              ),
                            ),
                          ),
                      ],
                    ),
                  );
                  },
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
                else if (!widget.adminView && allLessonsDone) ...[
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

class _CertificationCard extends StatelessWidget {
  const _CertificationCard({
    required this.certification,
    required this.adminView,
    required this.onIssue,
  });

  final Map<String, dynamic> certification;
  final bool adminView;
  final VoidCallback onIssue;

  @override
  Widget build(BuildContext context) {
    final issued = certification['issued'] == true;
    final eligible = certification['eligible'] == true;
    final certificate = Map<String, dynamic>.from(
      certification['certificate'] as Map? ?? const <String, dynamic>{},
    );
    final requirements = Map<String, dynamic>.from(
      certification['requirements'] as Map? ?? const <String, dynamic>{},
    );

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.workspace_premium_rounded, size: 30),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    issued ? 'ARI Certified Professional' : 'ARI Certification',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (issued) ...[
              Text('Certificate: ${certificate['certificate_number'] ?? '-'}'),
              Text('Status: ${certificate['status'] ?? '-'}'),
              Text('Final score: ${certificate['final_score'] ?? 0}%'),
              Text('Valid until: ${certificate['valid_until'] ?? '-'}'),
              Text(
                'Verification code: ${certificate['verification_code'] ?? '-'}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ] else ...[
              Text(
                eligible
                    ? 'All certification requirements are complete.'
                    : 'Complete all 30 days, pass the quiz and complete Trainer reviews to qualify.',
              ),
              const SizedBox(height: 8),
              Text(
                'Trainer reviews: ${requirements['reviews_received'] ?? 0}/${requirements['required_reviews'] ?? 0} • '
                'Average: ${requirements['trainer_average'] ?? 0}/5 • minimum 3/5',
              ),
              if (adminView && eligible) ...[
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: onIssue,
                  icon: const Icon(Icons.workspace_premium),
                  label: const Text('ISSUE ARI CERTIFICATE'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}


class _TrainingVideo extends StatefulWidget {
  const _TrainingVideo({required this.assetPath, required this.onCompleted});
  final String assetPath;
  final VoidCallback onCompleted;

  @override
  State<_TrainingVideo> createState() => _TrainingVideoState();
}

class _TrainingVideoState extends State<_TrainingVideo> {
  late final VideoPlayerController _controller;
  bool _completed = false;

  @override
  void initState() {
    super.initState();
    _controller = VideoPlayerController.asset(widget.assetPath)
      ..initialize().then((_) {
        if (mounted) setState(() {});
      });
    _controller.addListener(_listen);
  }

  void _listen() {
    if (_completed || !_controller.value.isInitialized) return;
    final duration = _controller.value.duration;
    final position = _controller.value.position;
    if (duration > Duration.zero && position >= duration - const Duration(milliseconds: 400)) {
      _completed = true;
      widget.onCompleted();
    }
  }

  @override
  void dispose() {
    _controller.removeListener(_listen);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_controller.value.isInitialized) {
      return const AspectRatio(
        aspectRatio: 16 / 9,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: AspectRatio(
            aspectRatio: _controller.value.aspectRatio,
            child: VideoPlayer(_controller),
          ),
        ),
        VideoProgressIndicator(_controller, allowScrubbing: false),
        FilledButton.tonalIcon(
          onPressed: () => setState(() {
            _controller.value.isPlaying
                ? _controller.pause()
                : _controller.play();
          }),
          icon: Icon(_controller.value.isPlaying ? Icons.pause : Icons.play_arrow),
          label: Text(
            _controller.value.isPlaying
                ? 'रोकें / PAUSE'
                : _completed
                    ? 'दोबारा देखें / REPLAY'
                    : 'वीडियो देखें / PLAY',
          ),
        ),
      ],
    );
  }
}


class _ScorePicker extends StatelessWidget {
  const _ScorePicker({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final int value;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(child: Text(label)),
          DropdownButton<int>(
            value: value,
            items: List.generate(
              5,
              (index) => DropdownMenuItem(
                value: index + 1,
                child: Text('${index + 1}/5'),
              ),
            ),
            onChanged: (v) {
              if (v != null) onChanged(v);
            },
          ),
        ],
      );
}
