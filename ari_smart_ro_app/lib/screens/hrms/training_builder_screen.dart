import 'package:flutter/material.dart';

import '../../services/training_service.dart';

class TrainingBuilderScreen extends StatefulWidget {
  const TrainingBuilderScreen({super.key});

  @override
  State<TrainingBuilderScreen> createState() => _TrainingBuilderScreenState();
}

class _TrainingBuilderScreenState extends State<TrainingBuilderScreen> {
  final _service = const TrainingService();
  bool _loading = true;
  List<Map<String, dynamic>> _courses = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _show(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final rows = await _service.adminCourses();
      if (mounted) setState(() => _courses = rows);
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _editCourse({Map<String, dynamic>? course}) async {
    final title = TextEditingController(text: (course?['title'] ?? '').toString());
    final description = TextEditingController(text: (course?['description'] ?? '').toString());
    final passing = TextEditingController(text: (course?['passing_score'] ?? 80).toString());
    final due = TextEditingController(text: (course?['due_days'] ?? 30).toString());
    final grace = TextEditingController(text: (course?['grace_days'] ?? 2).toString());
    final penalty = TextEditingController(text: (course?['penalty_amount'] ?? '0').toString());
    final certificateDays = TextEditingController(text: (course?['certificate_valid_days'] ?? 365).toString());
    final trainerReviews = TextEditingController(text: (course?['required_trainer_reviews'] ?? 0).toString());
    final trainerAverage = TextEditingController(text: (course?['minimum_trainer_average'] ?? 3).toString());
    String audience = (course?['audience'] ?? 'ALL').toString();
    bool mandatory = course?['is_mandatory'] != false;
    bool certificateEnabled = course?['certificate_enabled'] != false;
    bool saving = false;

    final saved = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(course == null ? 'Create Training Course' : 'Edit Course Settings'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(controller: title, decoration: const InputDecoration(labelText: 'Course title *')),
                  const SizedBox(height: 10),
                  TextField(
                    controller: description,
                    minLines: 3,
                    maxLines: 6,
                    decoration: const InputDecoration(
                      labelText: 'Course description',
                      hintText: 'What will employees learn and why?',
                    ),
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: audience,
                    decoration: const InputDecoration(labelText: 'Audience'),
                    items: const [
                      DropdownMenuItem(value: 'ALL', child: Text('All employees')),
                      DropdownMenuItem(value: 'ENGINEER', child: Text('Engineers')),
                      DropdownMenuItem(value: 'CALLING', child: Text('Calling staff')),
                      DropdownMenuItem(value: 'OFFICE', child: Text('Office staff')),
                      DropdownMenuItem(value: 'MANAGER', child: Text('Managers')),
                    ],
                    onChanged: (value) {
                      if (value != null) setLocal(() => audience = value);
                    },
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(child: TextField(controller: passing, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Pass %'))),
                      const SizedBox(width: 8),
                      Expanded(child: TextField(controller: due, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Due days'))),
                      const SizedBox(width: 8),
                      Expanded(child: TextField(controller: grace, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Grace days'))),
                    ],
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: penalty,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Non-compliance penalty draft amount',
                      helperText: 'Admin approval remains required before payroll deduction.',
                    ),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Mandatory training'),
                    subtitle: const Text('Published mandatory courses auto-assign to eligible employees.'),
                    value: mandatory,
                    onChanged: (value) => setLocal(() => mandatory = value),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Certificate enabled'),
                    value: certificateEnabled,
                    onChanged: (value) => setLocal(() => certificateEnabled = value),
                  ),
                  if (certificateEnabled) ...[
                    Row(
                      children: [
                        Expanded(child: TextField(controller: certificateDays, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Certificate validity days'))),
                        const SizedBox(width: 8),
                        Expanded(child: TextField(controller: trainerReviews, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Required trainer reviews'))),
                      ],
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: trainerAverage,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Minimum trainer average (1-5)'),
                    ),
                  ],
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(dialogContext, false),
              child: const Text('CANCEL'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (title.text.trim().isEmpty) {
                        _show('Course title is required.');
                        return;
                      }
                      setLocal(() => saving = true);
                      try {
                        final payload = <String, dynamic>{
                          'title': title.text.trim(),
                          'description': description.text.trim(),
                          'audience': audience,
                          'passing_score': int.tryParse(passing.text) ?? 80,
                          'due_days': int.tryParse(due.text) ?? 30,
                          'grace_days': int.tryParse(grace.text) ?? 2,
                          'penalty_amount': penalty.text.trim().isEmpty ? '0' : penalty.text.trim(),
                          'is_mandatory': mandatory,
                          'certificate_enabled': certificateEnabled,
                          'certificate_valid_days': int.tryParse(certificateDays.text) ?? 365,
                          'required_trainer_reviews': int.tryParse(trainerReviews.text) ?? 0,
                          'minimum_trainer_average': double.tryParse(trainerAverage.text) ?? 3,
                        };
                        if (course == null) {
                          await _service.createCourse(payload);
                        } else {
                          await _service.updateCourse((course['id'] as num).toInt(), payload);
                        }
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (e) {
                        _show(e.toString().replaceFirst('Exception: ', ''));
                        setLocal(() => saving = false);
                      }
                    },
              child: Text(course == null ? 'CREATE DRAFT' : 'SAVE'),
            ),
          ],
        ),
      ),
    );

    for (final controller in [title, description, passing, due, grace, penalty, certificateDays, trainerReviews, trainerAverage]) {
      controller.dispose();
    }
    if (saved == true) await _load();
  }

  Future<void> _editLesson(Map<String, dynamic> course, {Map<String, dynamic>? lesson}) async {
    final lessons = List<Map<String, dynamic>>.from(course['lessons'] as List? ?? const []);
    final title = TextEditingController(text: (lesson?['title'] ?? '').toString());
    final material = TextEditingController(text: (lesson?['content'] ?? '').toString());
    final takeaway = TextEditingController(text: (lesson?['key_takeaway'] ?? '').toString());
    final practice = TextEditingController(text: (lesson?['practice_task'] ?? '').toString());
    final trainer = TextEditingController(text: (lesson?['trainer_script'] ?? '').toString());
    final videoUrl = TextEditingController(text: (lesson?['video_url'] ?? '').toString());
    final resourceUrl = TextEditingController(text: (lesson?['resource_url'] ?? '').toString());
    final resourceLabel = TextEditingController(text: (lesson?['resource_label'] ?? '').toString());
    final day = TextEditingController(text: (lesson?['day_number'] ?? (lessons.length + 1)).toString());
    final duration = TextEditingController(text: (lesson?['duration_minutes'] ?? 60).toString());
    bool saving = false;

    final saved = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(lesson == null ? 'Add Detailed Lesson' : 'Edit Lesson'),
          content: SizedBox(
            width: 620,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(controller: title, decoration: const InputDecoration(labelText: 'Lesson title *')),
                  const SizedBox(height: 10),
                  TextField(
                    controller: material,
                    minLines: 10,
                    maxLines: 18,
                    decoration: const InputDecoration(
                      labelText: 'Detailed training material *',
                      hintText: 'Concepts + examples + real scenario + do/dont + procedure + explanation',
                      alignLabelWithHint: true,
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(controller: takeaway, minLines: 2, maxLines: 3, decoration: const InputDecoration(labelText: 'Key takeaway')),
                  const SizedBox(height: 10),
                  TextField(controller: practice, minLines: 3, maxLines: 6, decoration: const InputDecoration(labelText: 'Practical task / role-play')),
                  const SizedBox(height: 10),
                  TextField(controller: trainer, minLines: 4, maxLines: 8, decoration: const InputDecoration(labelText: 'Trainer script / Admin ko kya sikhana hai')),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(child: TextField(controller: day, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Day / order'))),
                      const SizedBox(width: 8),
                      Expanded(child: TextField(controller: duration, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Duration minutes'))),
                    ],
                  ),
                  const SizedBox(height: 10),
                  TextField(controller: videoUrl, decoration: const InputDecoration(labelText: 'Training video URL (optional)')),
                  const SizedBox(height: 10),
                  TextField(controller: resourceLabel, decoration: const InputDecoration(labelText: 'Resource label (optional)')),
                  const SizedBox(height: 10),
                  TextField(controller: resourceUrl, decoration: const InputDecoration(labelText: 'Resource URL (optional)')),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: saving ? null : () => Navigator.pop(dialogContext, false), child: const Text('CANCEL')),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (title.text.trim().isEmpty || material.text.trim().length < 80) {
                        _show('Add a title and meaningful material of at least 80 characters.');
                        return;
                      }
                      setLocal(() => saving = true);
                      try {
                        final payload = <String, dynamic>{
                          'title': title.text.trim(),
                          'content': material.text.trim(),
                          'key_takeaway': takeaway.text.trim(),
                          'practice_task': practice.text.trim(),
                          'trainer_script': trainer.text.trim(),
                          'day_number': int.tryParse(day.text) ?? 1,
                          'duration_minutes': int.tryParse(duration.text) ?? 60,
                          'video_url': videoUrl.text.trim(),
                          'resource_label': resourceLabel.text.trim(),
                          'resource_url': resourceUrl.text.trim(),
                        };
                        final courseId = (course['id'] as num).toInt();
                        if (lesson == null) {
                          payload['order'] = int.tryParse(day.text) ?? (lessons.length + 1);
                          await _service.addLesson(courseId, payload);
                        } else {
                          await _service.updateLesson(courseId, (lesson['id'] as num).toInt(), payload);
                        }
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (e) {
                        _show(e.toString().replaceFirst('Exception: ', ''));
                        setLocal(() => saving = false);
                      }
                    },
              child: const Text('SAVE LESSON'),
            ),
          ],
        ),
      ),
    );

    for (final controller in [title, material, takeaway, practice, trainer, videoUrl, resourceUrl, resourceLabel, day, duration]) {
      controller.dispose();
    }
    if (saved == true) await _load();
  }

  Future<void> _editQuestion(Map<String, dynamic> course, {Map<String, dynamic>? question}) async {
    final q = TextEditingController(text: (question?['question'] ?? '').toString());
    final a = TextEditingController(text: (question?['option_a'] ?? '').toString());
    final b = TextEditingController(text: (question?['option_b'] ?? '').toString());
    final c = TextEditingController(text: (question?['option_c'] ?? '').toString());
    final d = TextEditingController(text: (question?['option_d'] ?? '').toString());
    final explanation = TextEditingController(text: (question?['explanation'] ?? '').toString());
    String correct = (question?['correct_option'] ?? 'A').toString();
    bool saving = false;

    final saved = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(question == null ? 'Add Test Question' : 'Edit Test Question'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                children: [
                  TextField(controller: q, minLines: 2, maxLines: 4, decoration: const InputDecoration(labelText: 'Question *')),
                  const SizedBox(height: 8),
                  TextField(controller: a, decoration: const InputDecoration(labelText: 'Option A *')),
                  const SizedBox(height: 8),
                  TextField(controller: b, decoration: const InputDecoration(labelText: 'Option B *')),
                  const SizedBox(height: 8),
                  TextField(controller: c, decoration: const InputDecoration(labelText: 'Option C *')),
                  const SizedBox(height: 8),
                  TextField(controller: d, decoration: const InputDecoration(labelText: 'Option D *')),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: correct,
                    decoration: const InputDecoration(labelText: 'Correct answer'),
                    items: const [
                      DropdownMenuItem(value: 'A', child: Text('A')),
                      DropdownMenuItem(value: 'B', child: Text('B')),
                      DropdownMenuItem(value: 'C', child: Text('C')),
                      DropdownMenuItem(value: 'D', child: Text('D')),
                    ],
                    onChanged: (value) {
                      if (value != null) setLocal(() => correct = value);
                    },
                  ),
                  const SizedBox(height: 10),
                  TextField(controller: explanation, minLines: 2, maxLines: 4, decoration: const InputDecoration(labelText: 'Why this answer is correct')),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: saving ? null : () => Navigator.pop(dialogContext, false), child: const Text('CANCEL')),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if ([q, a, b, c, d].any((x) => x.text.trim().isEmpty)) {
                        _show('Question and all four options are required.');
                        return;
                      }
                      setLocal(() => saving = true);
                      try {
                        final payload = <String, dynamic>{
                          'question': q.text.trim(),
                          'option_a': a.text.trim(),
                          'option_b': b.text.trim(),
                          'option_c': c.text.trim(),
                          'option_d': d.text.trim(),
                          'correct_option': correct,
                          'explanation': explanation.text.trim(),
                        };
                        final courseId = (course['id'] as num).toInt();
                        if (question == null) {
                          await _service.addQuestion(courseId, payload);
                        } else {
                          await _service.updateQuestion(courseId, (question['id'] as num).toInt(), payload);
                        }
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (e) {
                        _show(e.toString().replaceFirst('Exception: ', ''));
                        setLocal(() => saving = false);
                      }
                    },
              child: const Text('SAVE QUESTION'),
            ),
          ],
        ),
      ),
    );

    for (final controller in [q, a, b, c, d, explanation]) {
      controller.dispose();
    }
    if (saved == true) await _load();
  }

  Future<void> _publish(Map<String, dynamic> course) async {
    final next = course['is_published'] != true;
    try {
      await _service.updateCourse((course['id'] as num).toInt(), {'is_published': next});
      _show(next ? 'Course published.' : 'Course unpublished and returned to draft state.');
      await _load();
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _assign(Map<String, dynamic> course) async {
    try {
      final result = await _service.assignCourse((course['id'] as num).toInt());
      _show(
        'Assigned: ' +
            (result['created'] ?? 0).toString() +
            ' new • ' +
            (result['already_assigned'] ?? 0).toString() +
            ' already assigned.',
      );
      await _load();
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Training Builder')),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () => _editCourse(),
          icon: const Icon(Icons.add),
          label: const Text('NEW COURSE'),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(14, 14, 14, 100),
                  children: [
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: Text(
                          'Admin flow: Create draft course → add detailed lessons/material → add test questions → set certificate rules → publish → assign. Training history is protected once assignments exist.',
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    if (_courses.isEmpty)
                      const Padding(
                        padding: EdgeInsets.only(top: 100),
                        child: Center(child: Text('No courses yet. Tap NEW COURSE.')),
                      ),
                    ..._courses.map((course) {
                      final lessons = List<Map<String, dynamic>>.from(course['lessons'] as List? ?? const []);
                      final questions = List<Map<String, dynamic>>.from(course['questions'] as List? ?? const []);
                      final published = course['is_published'] == true;
                      final subtitle =
                          (published ? 'PUBLISHED' : 'DRAFT') +
                          ' • ' +
                          (course['audience'] ?? '').toString() +
                          ' • ' +
                          lessons.length.toString() +
                          ' lessons • ' +
                          questions.length.toString() +
                          ' questions • pass ' +
                          (course['passing_score'] ?? 80).toString() +
                          '%\nCertificate: ' +
                          (course['certificate_enabled'] == true ? 'Yes' : 'No') +
                          ' • Trainer reviews: ' +
                          (course['required_trainer_reviews'] ?? 0).toString();

                      return Card(
                        margin: const EdgeInsets.only(bottom: 14),
                        child: ExpansionTile(
                          leading: CircleAvatar(
                            child: Icon(published ? Icons.public_rounded : Icons.edit_note_rounded),
                          ),
                          title: Text((course['title'] ?? '').toString(), style: const TextStyle(fontWeight: FontWeight.w800)),
                          subtitle: Text(subtitle),
                          childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                          children: [
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                FilledButton.tonalIcon(onPressed: () => _editCourse(course: course), icon: const Icon(Icons.settings_outlined), label: const Text('SETTINGS')),
                                FilledButton.tonalIcon(onPressed: () => _editLesson(course), icon: const Icon(Icons.menu_book_outlined), label: const Text('ADD LESSON')),
                                FilledButton.tonalIcon(onPressed: () => _editQuestion(course), icon: const Icon(Icons.quiz_outlined), label: const Text('ADD TEST QUESTION')),
                                FilledButton.icon(
                                  onPressed: () => _publish(course),
                                  icon: Icon(published ? Icons.visibility_off_outlined : Icons.publish_rounded),
                                  label: Text(published ? 'UNPUBLISH' : 'PUBLISH'),
                                ),
                                if (published)
                                  FilledButton.icon(onPressed: () => _assign(course), icon: const Icon(Icons.assignment_ind_rounded), label: const Text('ASSIGN ELIGIBLE')),
                              ],
                            ),
                            const SizedBox(height: 14),
                            Align(alignment: Alignment.centerLeft, child: Text('Training material', style: Theme.of(context).textTheme.titleMedium)),
                            ...lessons.map(
                              (lesson) => ListTile(
                                contentPadding: EdgeInsets.zero,
                                leading: const Icon(Icons.article_outlined),
                                title: Text('Day ' + (lesson['day_number'] ?? '').toString() + ' • ' + (lesson['title'] ?? '').toString()),
                                subtitle: Text(
                                  (lesson['duration_minutes'] ?? 0).toString() +
                                      ' min • ' +
                                      (lesson['content'] ?? '').toString().length.toString() +
                                      ' characters',
                                ),
                                trailing: IconButton(
                                  onPressed: () => _editLesson(course, lesson: lesson),
                                  icon: const Icon(Icons.edit_outlined),
                                  tooltip: 'Edit lesson',
                                ),
                              ),
                            ),
                            const Divider(),
                            Align(alignment: Alignment.centerLeft, child: Text('Test questions', style: Theme.of(context).textTheme.titleMedium)),
                            ...questions.map(
                              (question) => ListTile(
                                contentPadding: EdgeInsets.zero,
                                leading: const Icon(Icons.help_outline_rounded),
                                title: Text((question['question'] ?? '').toString()),
                                subtitle: Text('Correct: ' + (question['correct_option'] ?? '').toString()),
                                trailing: IconButton(
                                  onPressed: () => _editQuestion(course, question: question),
                                  icon: const Icon(Icons.edit_outlined),
                                  tooltip: 'Edit question',
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
      );
}
