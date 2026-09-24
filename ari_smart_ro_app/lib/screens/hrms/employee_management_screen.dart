import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../services/employee_management_service.dart';
import '../../utils/search_utils.dart';

class EmployeeManagementScreen extends StatefulWidget {
  const EmployeeManagementScreen({super.key});

  @override
  State<EmployeeManagementScreen> createState() =>
      _EmployeeManagementScreenState();
}

class _EmployeeManagementScreenState extends State<EmployeeManagementScreen> {
  final _service = EmployeeManagementService();
  List<Map<String, dynamic>> _employees = const [];
  String _company = 'Company';
  String? _error;
  bool _loading = true;
  final _searchController = TextEditingController();
  String _query = '';
  String _designationFilter = 'ALL';
  String _accountFilter = 'ALL';
  String _locationFilter = 'ALL';
  bool _canDelegateCustomerEdit = false;

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

  List<Map<String, dynamic>> get _filteredEmployees => _employees.where((employee) {
    final designation = (employee['designation'] ?? '').toString().toUpperCase();
    final active = employee['is_active'] == true;
    final locationReceived = employee['location_received'] == true;
    if (_designationFilter != 'ALL' && designation != _designationFilter) return false;
    if (_accountFilter == 'ACTIVE' && !active) return false;
    if (_accountFilter == 'INACTIVE' && active) return false;
    if (_locationFilter == 'RECEIVED' && !locationReceived) return false;
    if (_locationFilter == 'MISSING' && locationReceived) return false;
    return matchesAllSearchTerms(_query, [
      (employee['name'] ?? '').toString(),
      (employee['employee_id'] ?? '').toString(),
      (employee['phone'] ?? '').toString(),
      (employee['email'] ?? '').toString(),
      designation,
      locationReceived ? 'location received' : 'location missing',
    ]);
  }).toList();

  List<String> get _designations => <String>{
    'ALL',
    ..._employees
        .map((e) => (e['designation'] ?? '').toString().toUpperCase())
        .where((v) => v.isNotEmpty),
  }.toList();

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.list();
      if (!mounted) return;
      setState(() {
        _company = (data['company'] as Map?)?['name']?.toString() ?? 'Company';
        _canDelegateCustomerEdit = data['can_delegate_customer_edit'] == true;
        _employees = (data['employees'] as List<dynamic>? ?? const [])
            .map((row) => Map<String, dynamic>.from(row as Map))
            .toList();
      });
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error.toString().replaceFirst('Exception: ', ''),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _add() async {
    final formKey = GlobalKey<FormState>();
    final firstName = TextEditingController(),
        lastName = TextEditingController();
    final phone = TextEditingController(), email = TextEditingController();
    final salary = TextEditingController(), password = TextEditingController();
    final jobTitle = TextEditingController(), department = TextEditingController();
    final grade = TextEditingController(), address = TextEditingController();
    final city = TextEditingController(), state = TextEditingController();
    final emergencyName = TextEditingController(), emergencyContact = TextEditingController();
    String designation = 'ENGINEER', gender = 'OTHER';
    int? reportingManagerId;
    DateTime joiningDate = DateTime.now();
    bool saving = false, obscure = true;
    final saved =
        await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (context) => StatefulBuilder(
            builder: (context, setLocal) => AlertDialog(
              title: const Text('Add employee'),
              content: SizedBox(
                width: 520,
                child: Form(
                  key: formKey,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextFormField(
                          controller: firstName,
                          decoration: const InputDecoration(
                            labelText: 'First name *',
                          ),
                          validator: (v) =>
                              v == null || v.trim().isEmpty ? 'Required' : null,
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: lastName,
                          decoration: const InputDecoration(
                            labelText: 'Last name',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: phone,
                          keyboardType: TextInputType.phone,
                          maxLength: 10,
                          decoration: const InputDecoration(
                            labelText: 'Mobile number *',
                          ),
                          validator: (v) => v?.length == 10
                              ? null
                              : 'Enter 10-digit mobile number',
                        ),
                        TextFormField(
                          controller: email,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(labelText: 'Email'),
                        ),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<String>(
                          initialValue: designation,
                          decoration: const InputDecoration(
                            labelText: 'Designation *',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'ENGINEER',
                              child: Text('Engineer'),
                            ),
                            DropdownMenuItem(
                              value: 'OFFICE',
                              child: Text('Office staff'),
                            ),
                            DropdownMenuItem(
                              value: 'CALLING',
                              child: Text('Calling staff'),
                            ),
                            DropdownMenuItem(
                              value: 'MANAGER',
                              child: Text('Manager'),
                            ),
                          ],
                          onChanged: (value) => designation = value!,
                        ),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<String>(
                          initialValue: gender,
                          decoration: const InputDecoration(
                            labelText: 'Gender *',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'MALE',
                              child: Text('Male'),
                            ),
                            DropdownMenuItem(
                              value: 'FEMALE',
                              child: Text('Female'),
                            ),
                            DropdownMenuItem(
                              value: 'OTHER',
                              child: Text('Other'),
                            ),
                          ],
                          onChanged: (value) => gender = value!,
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: salary,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Monthly salary',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: jobTitle,
                          decoration: const InputDecoration(
                            labelText: 'Job title',
                            hintText: 'Senior Engineer / Team Leader',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: department,
                          decoration: const InputDecoration(labelText: 'Department'),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: grade,
                          decoration: const InputDecoration(labelText: 'Grade / level'),
                        ),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<int?>(
                          initialValue: reportingManagerId,
                          isExpanded: true,
                          decoration: const InputDecoration(labelText: 'Reporting manager'),
                          items: [
                            const DropdownMenuItem<int?>(
                              value: null,
                              child: Text('No reporting manager'),
                            ),
                            ..._employees
                                .where((e) => e['is_active'] == true)
                                .map(
                                  (e) => DropdownMenuItem<int?>(
                                    value: (e['id'] as num).toInt(),
                                    child: Text('${e['name']} • ${e['designation']}'),
                                  ),
                                ),
                          ],
                          onChanged: (value) =>
                              setLocal(() => reportingManagerId = value),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: address,
                          maxLines: 2,
                          decoration: const InputDecoration(labelText: 'Address'),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: city,
                          decoration: const InputDecoration(labelText: 'City'),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: state,
                          decoration: const InputDecoration(labelText: 'State'),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: emergencyName,
                          decoration: const InputDecoration(labelText: 'Emergency contact name'),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: emergencyContact,
                          keyboardType: TextInputType.phone,
                          maxLength: 10,
                          decoration: const InputDecoration(labelText: 'Emergency contact number'),
                        ),
                        const SizedBox(height: 10),
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.event_available_rounded),
                          title: const Text('Joining date'),
                          subtitle: Text(
                            '${joiningDate.day}/${joiningDate.month}/${joiningDate.year}',
                          ),
                          onTap: () async {
                            final value = await showDatePicker(
                              context: context,
                              initialDate: joiningDate,
                              firstDate: DateTime(2020),
                              lastDate: DateTime.now().add(
                                const Duration(days: 365),
                              ),
                            );
                            if (value != null) {
                              setLocal(() => joiningDate = value);
                            }
                          },
                        ),
                        TextFormField(
                          controller: password,
                          obscureText: obscure,
                          decoration: InputDecoration(
                            labelText: 'Temporary password *',
                            helperText:
                                'Use 8+ characters with letters, number and symbol',
                            suffixIcon: IconButton(
                              onPressed: () =>
                                  setLocal(() => obscure = !obscure),
                              icon: Icon(
                                obscure
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                              ),
                            ),
                          ),
                          validator: (v) => (v?.length ?? 0) < 8
                              ? 'Use at least 8 characters'
                              : null,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: saving
                      ? null
                      : () => Navigator.pop(context, false),
                  child: const Text('CANCEL'),
                ),
                FilledButton.icon(
                  onPressed: saving
                      ? null
                      : () async {
                          if (!formKey.currentState!.validate()) return;
                          setLocal(() => saving = true);
                          try {
                            await _service.create({
                              'first_name': firstName.text.trim(),
                              'last_name': lastName.text.trim(),
                              'phone': phone.text.trim(),
                              'email': email.text.trim(),
                              'designation': designation,
                              'gender': gender,
                              'joining_date':
                                  '${joiningDate.year}-${joiningDate.month.toString().padLeft(2, '0')}-${joiningDate.day.toString().padLeft(2, '0')}',
                              'salary': salary.text.trim().isEmpty
                                  ? '0'
                                  : salary.text.trim(),
                              'job_title': jobTitle.text.trim(),
                              'department': department.text.trim(),
                              'grade': grade.text.trim(),
                              'reporting_manager_id': reportingManagerId,
                              'address': address.text.trim(),
                              'city': city.text.trim(),
                              'state': state.text.trim(),
                              'emergency_name': emergencyName.text.trim(),
                              'emergency_contact': emergencyContact.text.trim(),
                              'initial_password': password.text,
                            });
                            if (context.mounted) Navigator.pop(context, true);
                          } catch (error) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    error.toString().replaceFirst(
                                      'Exception: ',
                                      '',
                                    ),
                                  ),
                                ),
                              );
                            }
                            setLocal(() => saving = false);
                          }
                        },
                  icon: saving
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.person_add_alt_1_rounded),
                  label: Text(saving ? 'CREATING...' : 'CREATE EMPLOYEE'),
                ),
              ],
            ),
          ),
        ) ??
        false;
    await Future<void>.delayed(const Duration(milliseconds: 350));
    for (final controller in [
      firstName,
      lastName,
      phone,
      email,
      salary,
      password,
      jobTitle,
      department,
      grade,
      address,
      city,
      state,
      emergencyName,
      emergencyContact,
    ]) {
      controller.dispose();
    }
    if (saved) {
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Employee created successfully.')),
        );
      }
    }
  }

  Future<void> _showIdCard(Map<String, dynamic> employee) async {
    final idCard = Map<String, dynamic>.from(
      employee['id_card'] as Map? ?? const {},
    );
    final onboarding = Map<String, dynamic>.from(
      employee['onboarding'] as Map? ?? const {},
    );
    final photo = (employee['photo'] ?? '').toString();
    final code = (idCard['verification_code'] ?? '').toString();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Official Employee ID'),
        content: SizedBox(
          width: 420,
          child: SingleChildScrollView(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 46,
                  backgroundImage: photo.isNotEmpty ? NetworkImage(photo) : null,
                  child: photo.isEmpty ? const Icon(Icons.person, size: 42) : null,
                ),
                const SizedBox(height: 12),
                Text(
                  employee['name'].toString(),
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                ),
                Text(
                  employee['job_title']?.toString().isNotEmpty == true
                      ? employee['job_title'].toString()
                      : employee['designation'].toString(),
                ),
                const SizedBox(height: 8),
                Text(
                  "Employee ID: ${employee['employee_id']}",
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 14),
                if (code.isNotEmpty)
                  QrImageView(data: 'ARI-EMP:$code', size: 150),
                const SizedBox(height: 8),
                Text('Verification: $code'),
                Text("Valid until: ${idCard['valid_until'] ?? '-'}"),
                const Divider(height: 26),
                Text(
                  "Onboarding: ${onboarding['status'] ?? '-'}",
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                Text(
                  onboarding['ready'] == true
                      ? 'Ready for duty'
                      : 'Pending joining requirements',
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CLOSE'),
          ),
        ],
      ),
    );
  }

  Future<void> _career(Map<String, dynamic> employee) async {
    try {
      var data = await _service.career((employee['id'] as num).toInt());
      if (!mounted) return;

      Future<void> refresh(StateSetter setLocal) async {
        data = await _service.career((employee['id'] as num).toInt());
        if (mounted) setLocal(() {});
      }

      await showDialog<void>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, setLocal) {
            final current = Map<String, dynamic>.from(
              data['employee'] as Map? ?? const {},
            );
            final history = (data['history'] as List<dynamic>? ?? const [])
                .map((e) => Map<String, dynamic>.from(e as Map))
                .toList();

            return AlertDialog(
              title: Text('Career • ${current['name'] ?? employee['name']}'),
              content: SizedBox(
                width: 620,
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                current['job_title']?.toString().isNotEmpty == true
                                    ? current['job_title'].toString()
                                    : current['designation']?.toString() ?? '',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '${current['department'] ?? 'No department'} • '
                                'Grade ${current['grade']?.toString().isEmpty == false ? current['grade'] : '-'}',
                              ),
                              Text('Salary ₹${current['salary'] ?? 0}'),
                              Text(
                                'Reports to: ${(current['reporting_manager'] as Map?)?['name'] ?? 'Not assigned'}',
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        onPressed: () async {
                          final created = await _createCareerMovement(
                            dialogContext,
                            current,
                          );
                          if (created && dialogContext.mounted) {
                            await refresh(setLocal);
                          }
                        },
                        icon: const Icon(Icons.trending_up_rounded),
                        label: const Text('NEW PROMOTION / CAREER CHANGE'),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Career history',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      if (history.isEmpty)
                        const Text('No career movement recorded yet.')
                      else
                        ...history.map(
                          (row) => Card(
                            child: Column(
                              children: [
                                ListTile(
                                  leading: const CircleAvatar(
                                    child: Icon(Icons.work_history_outlined),
                                  ),
                                  title: Text(
                                    row['movement_type']
                                        .toString()
                                        .replaceAll('_', ' '),
                                  ),
                                  subtitle: Text(
                                    '${row['effective_date']} • ${row['status']}\n'
                                    '${row['old_job_title']?.toString().isEmpty == false ? row['old_job_title'] : row['old_designation']}'
                                    ' → '
                                    '${row['new_job_title']?.toString().isEmpty == false ? row['new_job_title'] : row['new_designation']}\n'
                                    '₹${row['old_salary'] ?? '-'} → ₹${row['new_salary'] ?? '-'}\n'
                                    '${row['reason']}',
                                  ),
                                  isThreeLine: false,
                                ),
                                if (row['status'] == 'DRAFT')
                                  Padding(
                                    padding: const EdgeInsets.fromLTRB(
                                      12,
                                      0,
                                      12,
                                      12,
                                    ),
                                    child: Row(
                                      children: [
                                        Expanded(
                                          child: OutlinedButton(
                                            onPressed: () async {
                                              await _service.careerAction(
                                                employeeId:
                                                    (employee['id'] as num)
                                                        .toInt(),
                                                movementId:
                                                    (row['id'] as num).toInt(),
                                                action: 'CANCEL',
                                              );
                                              if (dialogContext.mounted) {
                                                await refresh(setLocal);
                                              }
                                            },
                                            child: const Text('CANCEL DRAFT'),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: FilledButton(
                                            onPressed: () async {
                                              await _service.careerAction(
                                                employeeId:
                                                    (employee['id'] as num)
                                                        .toInt(),
                                                movementId:
                                                    (row['id'] as num).toInt(),
                                                action: 'APPROVE',
                                              );
                                              if (dialogContext.mounted) {
                                                await refresh(setLocal);
                                                await _load();
                                              }
                                            },
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
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('CLOSE'),
                ),
              ],
            );
          },
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  Future<bool> _createCareerMovement(
    BuildContext dialogContext,
    Map<String, dynamic> current,
  ) async {
    String movementType = 'PROMOTION';
    String designation = (current['designation'] ?? 'ENGINEER').toString();
    final title = TextEditingController(
      text: current['job_title']?.toString() ?? '',
    );
    final department = TextEditingController(
      text: current['department']?.toString() ?? '',
    );
    final grade = TextEditingController(
      text: current['grade']?.toString() ?? '',
    );
    final salary = TextEditingController(
      text: current['salary']?.toString() ?? '',
    );
    final reason = TextEditingController();
    DateTime effectiveDate = DateTime.now();
    int? managerId = (current['reporting_manager'] as Map?)?['id'] as int?;

    final saved = await showDialog<bool>(
          context: dialogContext,
          builder: (context) => StatefulBuilder(
            builder: (context, setLocal) => AlertDialog(
              title: const Text('New career movement'),
              content: SizedBox(
                width: 520,
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: movementType,
                        decoration: const InputDecoration(
                          labelText: 'Movement type',
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'PROMOTION',
                            child: Text('Promotion'),
                          ),
                          DropdownMenuItem(
                            value: 'DESIGNATION_CHANGE',
                            child: Text('Designation change'),
                          ),
                          DropdownMenuItem(
                            value: 'SALARY_REVISION',
                            child: Text('Salary revision'),
                          ),
                          DropdownMenuItem(
                            value: 'TRANSFER',
                            child: Text('Department transfer'),
                          ),
                          DropdownMenuItem(
                            value: 'MANAGER_CHANGE',
                            child: Text('Reporting manager change'),
                          ),
                          DropdownMenuItem(
                            value: 'DEMOTION',
                            child: Text('Demotion'),
                          ),
                        ],
                        onChanged: (v) =>
                            setLocal(() => movementType = v ?? 'PROMOTION'),
                      ),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<String>(
                        initialValue: designation,
                        decoration: const InputDecoration(
                          labelText: 'Operational designation',
                          helperText:
                              'Controls app permissions. Use Job title for Senior Engineer / Team Leader etc.',
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'ENGINEER',
                            child: Text('Engineer'),
                          ),
                          DropdownMenuItem(
                            value: 'OFFICE',
                            child: Text('Office staff'),
                          ),
                          DropdownMenuItem(
                            value: 'CALLING',
                            child: Text('Calling staff'),
                          ),
                          DropdownMenuItem(
                            value: 'MANAGER',
                            child: Text('Manager'),
                          ),
                        ],
                        onChanged: (v) =>
                            setLocal(() => designation = v ?? designation),
                      ),
                      TextField(
                        controller: title,
                        decoration: const InputDecoration(
                          labelText: 'Job title',
                          hintText: 'Senior Engineer / Team Leader',
                        ),
                      ),
                      TextField(
                        controller: department,
                        decoration: const InputDecoration(
                          labelText: 'Department',
                        ),
                      ),
                      TextField(
                        controller: grade,
                        decoration: const InputDecoration(
                          labelText: 'Grade / level',
                        ),
                      ),
                      TextField(
                        controller: salary,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        decoration: const InputDecoration(
                          labelText: 'Monthly salary',
                        ),
                      ),
                      DropdownButtonFormField<int?>(
                        initialValue: managerId,
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Reporting manager',
                        ),
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('No reporting manager'),
                          ),
                          ..._employees
                              .where(
                                (e) =>
                                    e['is_active'] == true &&
                                    e['id'] != current['id'],
                              )
                              .map(
                                (e) => DropdownMenuItem<int?>(
                                  value: (e['id'] as num).toInt(),
                                  child: Text(
                                    '${e['name']} • ${e['designation']}',
                                  ),
                                ),
                              ),
                        ],
                        onChanged: (v) => setLocal(() => managerId = v),
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.event_available_outlined),
                        title: const Text('Effective date'),
                        subtitle: Text(
                          '${effectiveDate.day}/${effectiveDate.month}/${effectiveDate.year}',
                        ),
                        onTap: () async {
                          final value = await showDatePicker(
                            context: context,
                            initialDate: effectiveDate,
                            firstDate: DateTime(2020),
                            lastDate: DateTime.now().add(
                              const Duration(days: 3650),
                            ),
                          );
                          if (value != null) {
                            setLocal(() => effectiveDate = value);
                          }
                        },
                      ),
                      TextField(
                        controller: reason,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Reason / HR note *',
                        ),
                      ),
                    ],
                  ),
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
        ) ??
        false;

    if (!saved || reason.text.trim().isEmpty) {
      title.dispose();
      department.dispose();
      grade.dispose();
      salary.dispose();
      reason.dispose();
      return false;
    }

    try {
      await _service.createCareerMovement(
        employeeId: (current['id'] as num).toInt(),
        payload: {
          'movement_type': movementType,
          'new_designation': designation,
          'new_job_title': title.text.trim(),
          'new_department': department.text.trim(),
          'new_grade': grade.text.trim(),
          'new_salary': salary.text.trim(),
          'new_reporting_manager_id': managerId,
          'effective_date':
              '${effectiveDate.year}-${effectiveDate.month.toString().padLeft(2, '0')}-${effectiveDate.day.toString().padLeft(2, '0')}',
          'reason': reason.text.trim(),
        },
      );
      return true;
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
      return false;
    } finally {
      title.dispose();
      department.dispose();
      grade.dispose();
      salary.dispose();
      reason.dispose();
    }
  }

  Future<void> _setCustomerEditPermission(
    Map<String, dynamic> employee,
  ) async {
    if (!_canDelegateCustomerEdit) return;
    final current = employee['can_edit_customer'] == true;
    final allow = !current;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(
          allow
              ? 'Allow customer editing?'
              : 'Remove customer editing permission?',
        ),
        content: Text(
          allow
              ? '${employee['name']} will be able to edit customer master details and customer status.'
              : '${employee['name']} will no longer be able to edit customer master details or customer status.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(allow ? 'ALLOW' : 'REMOVE'),
          ),
        ],
      ),
    ) ?? false;
    if (!confirmed) return;

    try {
      await _service.setCustomerEditPermission(
        employeeId: (employee['id'] as num).toInt(),
        isAllowed: allow,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              allow
                  ? 'Customer edit permission granted.'
                  : 'Customer edit permission removed.',
            ),
          ),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  Future<void> _resetLoginDevice(Map<String, dynamic> employee) async {
    if (!_canDelegateCustomerEdit) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Reset login device?'),
        content: Text(
          '${employee['name']} will be signed out from the currently registered phone. '
          'On the next successful login, the new phone will become the only allowed device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('RESET DEVICE'),
          ),
        ],
      ),
    ) ?? false;
    if (!confirmed) return;

    try {
      await _service.resetLoginDevice(
        employeeId: (employee['id'] as num).toInt(),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Login device reset. Old phone is blocked; next login will register the new phone.',
            ),
          ),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  Future<void> _setEmployeeActive(
    Map<String, dynamic> employee,
    bool active,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(active ? 'Reactivate employee?' : 'Deactivate employee?'),
        content: Text(
          active
              ? '${employee['name']} will be able to login again.'
              : '${employee['name']} login will be disabled while old work history stays available.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(active ? 'REACTIVATE' : 'DEACTIVATE'),
          ),
        ],
      ),
    ) ?? false;
    if (!confirmed) return;

    try {
      await _service.lifecycle(
        employeeId: (employee['id'] as num).toInt(),
        action: active ? 'reactivate' : 'deactivate',
      );
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error.toString().replaceFirst('Exception: ', ''),
            ),
          ),
        );
      }
    }
  }

  Future<void> _removeTestEmployee(Map<String, dynamic> employee) async {
    final controller = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Remove test employee'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'This works only when the employee has no linked attendance, jobs, payroll, customers or other work history. Otherwise deactivate the account.',
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(labelText: 'Type DELETE'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('REMOVE'),
          ),
        ],
      ),
    ) ?? false;

    if (!confirmed) {
      controller.dispose();
      return;
    }

    try {
      await _service.lifecycle(
        employeeId: (employee['id'] as num).toInt(),
        action: 'permanent_delete',
        confirm: controller.text.trim(),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Test employee removed.')),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error.toString().replaceFirst('Exception: ', ''),
            ),
          ),
        );
      }
    } finally {
      controller.dispose();
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Employees')),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: _add,
      icon: const Icon(Icons.person_add_alt_1_rounded),
      label: const Text('ADD EMPLOYEE'),
    ),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
        ? Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!, textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: _load, child: const Text('RETRY')),
                ],
              ),
            ),
          )
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
              children: [
                Text(_company, style: Theme.of(context).textTheme.titleLarge),
                Text('${_filteredEmployees.length} of ${_employees.length} employees in this workspace'),
                const SizedBox(height: 12),
                TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    hintText: 'Search name, employee ID, phone, email...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _query = '');
                            },
                            icon: const Icon(Icons.clear),
                          ),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _designationFilter,
                        isExpanded: true,
                        decoration: const InputDecoration(labelText: 'Designation'),
                        items: _designations
                            .map(
                              (v) => DropdownMenuItem(
                                value: v,
                                child: Text(
                                  v == 'ALL' ? 'All designations' : v,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            )
                            .toList(),
                        onChanged: (v) => setState(() => _designationFilter = v ?? 'ALL'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _accountFilter,
                        isExpanded: true,
                        decoration: const InputDecoration(labelText: 'Account'),
                        items: const [
                          DropdownMenuItem(value: 'ALL', child: Text('All')),
                          DropdownMenuItem(value: 'ACTIVE', child: Text('Active')),
                          DropdownMenuItem(value: 'INACTIVE', child: Text('Inactive')),
                        ],
                        onChanged: (v) => setState(() => _accountFilter = v ?? 'ALL'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  initialValue: _locationFilter,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Location status',
                    prefixIcon: Icon(Icons.location_on_outlined),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'ALL',
                      child: Text('All employees'),
                    ),
                    DropdownMenuItem(
                      value: 'RECEIVED',
                      child: Text('Location received'),
                    ),
                    DropdownMenuItem(
                      value: 'MISSING',
                      child: Text('Location missing'),
                    ),
                  ],
                  onChanged: (v) =>
                      setState(() => _locationFilter = v ?? 'ALL'),
                ),
                const SizedBox(height: 16),
                if (_employees.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(28),
                      child: Center(
                        child: Text(
                          'No employees yet. Tap ADD EMPLOYEE to create the first account.',
                        ),
                      ),
                    ),
                  ),
                if (_employees.isNotEmpty && _filteredEmployees.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(22),
                      child: Center(child: Text('No matching employees found.')),
                    ),
                  ),
                ..._filteredEmployees.map(
                  (employee) => Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        child: Text(
                          employee['name']
                              .toString()
                              .substring(0, 1)
                              .toUpperCase(),
                        ),
                      ),
                      title: Text(employee['name'].toString()),
                      subtitle: Text(
                        '${employee['employee_id']} • ${employee['phone']}\n'
                        '${employee['job_title']?.toString().isNotEmpty == true ? employee['job_title'] : employee['designation']}'
                        '${employee['department']?.toString().isEmpty == false ? ' • ${employee['department']}' : ''}'
                        ' • ₹${employee['salary']}\n'
                        '${employee['location_received'] == true ? 'Location received' : 'Location missing'}'
                        '${employee['last_location_updated'] == null ? '' : ' • last update ${employee['last_location_updated']}'}'
                        '${employee['login_device_bound'] == true ? '\nLogin phone: registered' : '\nLogin phone: not registered'}',
                      ),
                      isThreeLine: true,
                      trailing: PopupMenuButton<String>(
                        tooltip: 'Employee actions',
                        onSelected: (value) {
                          if (value == 'id_card') {
                            _showIdCard(employee);
                          } else if (value == 'career') {
                            _career(employee);
                          } else if (value == 'customer_edit') {
                            _setCustomerEditPermission(employee);
                          } else if (value == 'reset_login_device') {
                            _resetLoginDevice(employee);
                          } else if (value == 'deactivate') {
                            _setEmployeeActive(employee, false);
                          } else if (value == 'reactivate') {
                            _setEmployeeActive(employee, true);
                          } else if (value == 'remove_test') {
                            _removeTestEmployee(employee);
                          }
                        },
                        itemBuilder: (_) => [
                          const PopupMenuItem(
                            value: 'id_card',
                            child: ListTile(
                              leading: Icon(Icons.badge_rounded),
                              title: Text('View Digital ID'),
                            ),
                          ),
                          const PopupMenuItem(
                            value: 'career',
                            child: ListTile(
                              leading: Icon(Icons.trending_up_rounded),
                              title: Text('Career & Promotion'),
                            ),
                          ),
                          if (_canDelegateCustomerEdit)
                            PopupMenuItem(
                              value: 'reset_login_device',
                              child: ListTile(
                                leading: const Icon(Icons.phonelink_erase_rounded),
                                title: const Text('Reset Login Device'),
                                subtitle: Text(
                                  employee['login_device_bound'] == true
                                      ? 'A phone is currently registered'
                                      : 'No phone is currently registered',
                                ),
                              ),
                            ),
                          if (_canDelegateCustomerEdit)
                            PopupMenuItem(
                              value: 'customer_edit',
                              child: ListTile(
                                leading: Icon(
                                  employee['can_edit_customer'] == true
                                      ? Icons.lock_open_rounded
                                      : Icons.admin_panel_settings_outlined,
                                ),
                                title: Text(
                                  employee['can_edit_customer'] == true
                                      ? 'Remove Customer Edit Access'
                                      : 'Allow Customer Edit Access',
                                ),
                                subtitle: Text(
                                  employee['can_edit_customer'] == true
                                      ? 'Admin delegated permission is active'
                                      : 'Admin-only permission',
                                ),
                              ),
                            ),
                          const PopupMenuDivider(),
                          if (employee['is_active'] == true)
                            const PopupMenuItem(
                              value: 'deactivate',
                              child: ListTile(
                                leading: Icon(Icons.block_outlined),
                                title: Text('Deactivate'),
                              ),
                            )
                          else
                            const PopupMenuItem(
                              value: 'reactivate',
                              child: ListTile(
                                leading: Icon(Icons.restore),
                                title: Text('Reactivate'),
                              ),
                            ),
                          const PopupMenuDivider(),
                          const PopupMenuItem(
                            value: 'remove_test',
                            child: ListTile(
                              leading: Icon(Icons.delete_outline),
                              title: Text('Remove test employee'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
  );
}
