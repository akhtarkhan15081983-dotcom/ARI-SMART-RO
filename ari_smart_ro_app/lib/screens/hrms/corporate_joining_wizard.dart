import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../services/corporate_hrms_service.dart';

class CorporateJoiningWizard extends StatefulWidget {
  const CorporateJoiningWizard({
    super.key,
    required this.managers,
    required this.onCompleted,
  });

  final List<Map<String, dynamic>> managers;
  final VoidCallback onCompleted;

  @override
  State<CorporateJoiningWizard> createState() => _CorporateJoiningWizardState();
}

class _CorporateJoiningWizardState extends State<CorporateJoiningWizard> {
  final _service = CorporateHrmsService();
  final _formKey = GlobalKey<FormState>();
  final _documents = <String, PlatformFile>{};
  final _documentNumbers = <String, TextEditingController>{};

  int _step = 0;
  bool _saving = false;

  final firstName = TextEditingController();
  final lastName = TextEditingController();
  final phone = TextEditingController();
  final email = TextEditingController();
  final dob = TextEditingController();
  final address = TextEditingController();
  final city = TextEditingController();
  final state = TextEditingController();
  final pincode = TextEditingController();
  final emergencyName = TextEditingController();
  final emergencyPhone = TextEditingController();
  final department = TextEditingController();
  final jobTitle = TextEditingController();
  final grade = TextEditingController();
  final workLocation = TextEditingController();
  final salary = TextEditingController();
  final bankName = TextEditingController();
  final bankAccount = TextEditingController();
  final ifsc = TextEditingController();
  final password = TextEditingController();

  String gender = 'OTHER';
  String designation = 'ENGINEER';
  String employmentType = 'PROBATION';
  int probationMonths = 3;
  int? reportingManagerId;
  DateTime joiningDate = DateTime.now();
  bool policyAcknowledged = false;
  bool sopAcknowledged = false;
  bool safetyAcknowledged = false;

  static const documentTypes = <String, String>{
    'PHOTO': 'Photo',
    'AADHAAR': 'Aadhaar',
    'PAN': 'PAN',
    'ADDRESS_PROOF': 'Address Proof',
    'BANK_PROOF': 'Bank Proof',
    'QUALIFICATION': 'Qualification',
    'PREVIOUS_EMPLOYMENT': 'Previous Employment',
    'OTHER': 'Other company-required document',
  };

  @override
  void initState() {
    super.initState();
    for (final type in documentTypes.keys) {
      _documentNumbers[type] = TextEditingController();
    }
  }

  @override
  void dispose() {
    for (final controller in [
      firstName,
      lastName,
      phone,
      email,
      dob,
      address,
      city,
      state,
      pincode,
      emergencyName,
      emergencyPhone,
      department,
      jobTitle,
      grade,
      workLocation,
      salary,
      bankName,
      bankAccount,
      ifsc,
      password,
      ..._documentNumbers.values,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  String _date(DateTime value) =>
      '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  InputDecoration _decoration(String label, {String? hint}) => InputDecoration(
        labelText: label,
        hintText: hint,
        border: const OutlineInputBorder(),
        isDense: true,
      );

  @override
  Widget build(BuildContext context) {
    final desktop = MediaQuery.sizeOf(context).width >= 900;
    return Scaffold(
      appBar: AppBar(title: const Text('New Employee Joining')),
      body: Form(
        key: _formKey,
        child: Stepper(
          type: desktop ? StepperType.horizontal : StepperType.vertical,
          currentStep: _step,
          onStepTapped: (value) => setState(() => _step = value),
          controlsBuilder: (context, details) => Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Row(
              children: [
                if (_step > 0)
                  OutlinedButton(
                    onPressed: _saving ? null : () => setState(() => _step -= 1),
                    child: const Text('BACK'),
                  ),
                const Spacer(),
                FilledButton.icon(
                  onPressed: _saving
                      ? null
                      : (_step == 5 ? _submit : () => setState(() => _step += 1)),
                  icon: _saving
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(_step == 5 ? Icons.how_to_reg : Icons.arrow_forward),
                  label: Text(_saving
                      ? 'CREATING...'
                      : (_step == 5 ? 'CREATE EMPLOYEE' : 'CONTINUE')),
                ),
              ],
            ),
          ),
          steps: [
            Step(
              title: const Text('Personal'),
              isActive: _step >= 0,
              content: _card('Personal & emergency information', [
                _two(
                  TextFormField(
                    controller: firstName,
                    decoration: _decoration('First name *'),
                    validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null,
                  ),
                  TextFormField(controller: lastName, decoration: _decoration('Last name')),
                ),
                _gap(),
                _two(
                  TextFormField(
                    controller: phone,
                    keyboardType: TextInputType.phone,
                    decoration: _decoration('Mobile *'),
                    validator: (v) => (v ?? '').trim().length == 10 ? null : '10 digits required',
                  ),
                  TextFormField(controller: email, decoration: _decoration('Email')),
                ),
                _gap(),
                _two(
                  TextFormField(controller: dob, decoration: _decoration('DOB', hint: 'YYYY-MM-DD')),
                  DropdownButtonFormField<String>(
                    initialValue: gender,
                    decoration: _decoration('Gender'),
                    items: const [
                      DropdownMenuItem(value: 'MALE', child: Text('Male')),
                      DropdownMenuItem(value: 'FEMALE', child: Text('Female')),
                      DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                    ],
                    onChanged: (v) => setState(() => gender = v ?? 'OTHER'),
                  ),
                ),
                _gap(),
                TextFormField(controller: address, maxLines: 2, decoration: _decoration('Residential address')),
                _gap(),
                _three(
                  TextFormField(controller: city, decoration: _decoration('City')),
                  TextFormField(controller: state, decoration: _decoration('State')),
                  TextFormField(controller: pincode, decoration: _decoration('Pincode')),
                ),
                _gap(),
                _two(
                  TextFormField(controller: emergencyName, decoration: _decoration('Emergency contact name')),
                  TextFormField(controller: emergencyPhone, decoration: _decoration('Emergency contact number')),
                ),
              ]),
            ),
            Step(
              title: const Text('Employment'),
              isActive: _step >= 1,
              content: _card('Employment setup', [
                _two(
                  DropdownButtonFormField<String>(
                    initialValue: designation,
                    decoration: _decoration('Designation'),
                    items: const [
                      DropdownMenuItem(value: 'ENGINEER', child: Text('Engineer')),
                      DropdownMenuItem(value: 'OFFICE', child: Text('Office Staff')),
                      DropdownMenuItem(value: 'CALLING', child: Text('Calling Staff')),
                      DropdownMenuItem(value: 'MANAGER', child: Text('Manager')),
                    ],
                    onChanged: (v) => setState(() => designation = v ?? designation),
                  ),
                  TextFormField(
                    controller: jobTitle,
                    decoration: _decoration('Job title *'),
                    validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null,
                  ),
                ),
                _gap(),
                _three(
                  TextFormField(
                    controller: department,
                    decoration: _decoration('Department *'),
                    validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null,
                  ),
                  TextFormField(controller: grade, decoration: _decoration('Grade / level')),
                  TextFormField(controller: workLocation, decoration: _decoration('Work location')),
                ),
                _gap(),
                _two(
                  DropdownButtonFormField<String>(
                    initialValue: employmentType,
                    decoration: _decoration('Employment type'),
                    items: const [
                      DropdownMenuItem(value: 'PROBATION', child: Text('Probation')),
                      DropdownMenuItem(value: 'PERMANENT', child: Text('Permanent')),
                      DropdownMenuItem(value: 'CONTRACT', child: Text('Contract')),
                      DropdownMenuItem(value: 'TRAINEE', child: Text('Trainee')),
                    ],
                    onChanged: (v) => setState(() => employmentType = v ?? employmentType),
                  ),
                  DropdownButtonFormField<int>(
                    initialValue: probationMonths,
                    decoration: _decoration('Probation months'),
                    items: const [1, 3, 6, 12]
                        .map((m) => DropdownMenuItem(value: m, child: Text('$m month${m == 1 ? '' : 's'}')))
                        .toList(),
                    onChanged: (v) => setState(() => probationMonths = v ?? 3),
                  ),
                ),
                _gap(),
                _two(
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.event_available),
                    title: const Text('Joining date'),
                    subtitle: Text(_date(joiningDate)),
                    onTap: _pickJoiningDate,
                  ),
                  DropdownButtonFormField<int?>(
                    initialValue: reportingManagerId,
                    isExpanded: true,
                    decoration: _decoration('Reporting manager'),
                    items: [
                      const DropdownMenuItem<int?>(value: null, child: Text('Not assigned yet')),
                      ...widget.managers.map((row) => DropdownMenuItem<int?>(
                            value: (row['id'] as num?)?.toInt(),
                            child: Text('${row['name']} • ${row['job_title'] ?? row['designation']}'),
                          )),
                    ],
                    onChanged: (v) => setState(() => reportingManagerId = v),
                  ),
                ),
              ]),
            ),
            Step(
              title: const Text('Payroll'),
              isActive: _step >= 2,
              content: _card('Payroll & bank setup', [
                _two(
                  TextFormField(controller: salary, keyboardType: TextInputType.number, decoration: _decoration('Monthly salary')),
                  TextFormField(controller: bankName, decoration: _decoration('Bank name')),
                ),
                _gap(),
                _two(
                  TextFormField(controller: bankAccount, decoration: _decoration('Bank account number')),
                  TextFormField(controller: ifsc, decoration: _decoration('IFSC')),
                ),
              ]),
            ),
            Step(
              title: const Text('Documents'),
              isActive: _step >= 3,
              content: _card('Actual joining document uploads', [
                const Text(
                  'Mandatory documents remain MISSING until a real file is selected and uploaded. HR must verify each document before READY FOR DUTY.',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 12),
                ...documentTypes.entries.map(_documentRow),
              ]),
            ),
            Step(
              title: const Text('Controls'),
              isActive: _step >= 4,
              content: _card('Security, acknowledgements & login', [
                TextFormField(
                  controller: password,
                  obscureText: true,
                  decoration: _decoration('Temporary password *'),
                  validator: (v) => (v ?? '').length < 8 ? 'Minimum 8 characters' : null,
                ),
                _gap(),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: policyAcknowledged,
                  onChanged: (v) => setState(() => policyAcknowledged = v ?? false),
                  title: const Text('Company policy acknowledged'),
                ),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: sopAcknowledged,
                  onChanged: (v) => setState(() => sopAcknowledged = v ?? false),
                  title: const Text('SOP acknowledged'),
                ),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: safetyAcknowledged,
                  onChanged: (v) => setState(() => safetyAcknowledged = v ?? false),
                  title: const Text('Safety induction acknowledged'),
                ),
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.face_retouching_natural),
                  title: Text('Face + device registration'),
                  subtitle: Text('Completed on employee device and must pass before READY FOR DUTY.'),
                ),
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.school_outlined),
                  title: Text('Mandatory training'),
                  subtitle: Text('Training completion remains a separate READY FOR DUTY gate.'),
                ),
              ]),
            ),
            Step(
              title: const Text('Review'),
              isActive: _step >= 5,
              content: _card('Final HR review', [
                _review('Employee', '${firstName.text} ${lastName.text}'.trim()),
                _review('Employment', employmentType),
                _review('Department', department.text.trim()),
                _review('Documents selected', '${_documents.length}/${documentTypes.length}'),
                _review('Joining date', _date(joiningDate)),
                const Divider(height: 28),
                const Text(
                  'Employee creation does not mark READY FOR DUTY. Documents, face/device security, mandatory training, manager review and HR review remain enforced.',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _documentRow(MapEntry<String, String> entry) {
    final selected = _documents[entry.key];
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(selected == null ? Icons.upload_file : Icons.check_circle_outline),
                    title: Text(entry.value),
                    subtitle: Text(selected?.name ?? (entry.key == 'OTHER' ? 'Optional / company-required' : 'Mandatory')),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => _pickDocument(entry.key),
                  icon: const Icon(Icons.attach_file),
                  label: Text(selected == null ? 'SELECT' : 'CHANGE'),
                ),
              ],
            ),
            if (entry.key == 'AADHAAR' || entry.key == 'PAN')
              TextField(
                controller: _documentNumbers[entry.key],
                decoration: _decoration('${entry.value} number'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _card(String title, List<Widget> children) => ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1050),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                const SizedBox(height: 16),
                ...children,
              ],
            ),
          ),
        ),
      );

  Widget _two(Widget a, Widget b) => LayoutBuilder(
        builder: (context, constraints) => constraints.maxWidth < 700
            ? Column(children: [a, _gap(), b])
            : Row(children: [Expanded(child: a), const SizedBox(width: 12), Expanded(child: b)]),
      );

  Widget _three(Widget a, Widget b, Widget c) => LayoutBuilder(
        builder: (context, constraints) => constraints.maxWidth < 780
            ? Column(children: [a, _gap(), b, _gap(), c])
            : Row(children: [
                Expanded(child: a),
                const SizedBox(width: 12),
                Expanded(child: b),
                const SizedBox(width: 12),
                Expanded(child: c),
              ]),
      );

  Widget _review(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          SizedBox(width: 180, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700))),
          Expanded(child: Text(value.isEmpty ? 'Pending' : value)),
        ]),
      );

  Widget _gap() => const SizedBox(height: 12);

  Future<void> _pickDocument(String type) async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      withData: true,
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() => _documents[type] = result.files.single);
    }
  }

  Future<void> _pickJoiningDate() async {
    final value = await showDatePicker(
      context: context,
      initialDate: joiningDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (value != null) setState(() => joiningDate = value);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      _message('Complete all required joining fields.');
      return;
    }
    setState(() => _saving = true);
    try {
      final created = await _service.createEmployee({
        'first_name': firstName.text.trim(),
        'last_name': lastName.text.trim(),
        'phone': phone.text.trim(),
        'email': email.text.trim(),
        'designation': designation,
        'gender': gender,
        'joining_date': _date(joiningDate),
        'salary': salary.text.trim().isEmpty ? '0' : salary.text.trim(),
        'job_title': jobTitle.text.trim(),
        'department': department.text.trim(),
        'grade': grade.text.trim(),
        'reporting_manager_id': reportingManagerId,
        'address': address.text.trim(),
        'city': city.text.trim(),
        'state': state.text.trim(),
        'pincode': pincode.text.trim(),
        'emergency_name': emergencyName.text.trim(),
        'emergency_contact': emergencyPhone.text.trim(),
        'initial_password': password.text,
      });
      final employee = Map<String, dynamic>.from(created['employee'] as Map);
      final employeeId = (employee['id'] as num).toInt();

      await _service.updateProfile(employeeId, {
        if (dob.text.trim().isNotEmpty) 'date_of_birth': dob.text.trim(),
        'address': address.text.trim(),
        'city': city.text.trim(),
        'state': state.text.trim(),
        'pincode': pincode.text.trim(),
        'emergency_name': emergencyName.text.trim(),
        'emergency_contact': emergencyPhone.text.trim(),
        'job_title': jobTitle.text.trim(),
        'department': department.text.trim(),
        'grade': grade.text.trim(),
        'salary': salary.text.trim().isEmpty ? '0' : salary.text.trim(),
        'reporting_manager_id': reportingManagerId,
      });

      await _service.updateLifecycle(employeeId, {
        'employment_type': employmentType,
        'work_location': workLocation.text.trim(),
        'probation_months': probationMonths,
        'policy_acknowledged': policyAcknowledged,
        'sop_acknowledged': sopAcknowledged,
        'safety_training_acknowledged': safetyAcknowledged,
        'payroll_details_complete': bankAccount.text.trim().isNotEmpty && ifsc.text.trim().isNotEmpty,
        'joining_checklist': {
          'bank_name': bankName.text.trim(),
          'bank_account_last4': bankAccount.text.trim().length >= 4
              ? bankAccount.text.trim().substring(bankAccount.text.trim().length - 4)
              : bankAccount.text.trim(),
          'ifsc': ifsc.text.trim().toUpperCase(),
        },
        'note': 'Corporate joining wizard completed by HR.',
      });

      for (final entry in _documents.entries) {
        await _service.uploadEmployeeDocument(
          employeeId,
          documentType: entry.key,
          file: entry.value,
          documentNumber: _documentNumbers[entry.key]?.text.trim() ?? '',
        );
      }

      if (!mounted) return;
      widget.onCompleted();
      Navigator.pop(context, true);
      _message('${employee['employee_id']} created. Uploaded documents are pending HR verification.');
    } catch (error) {
      _message(error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _message(String value) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value)));
  }
}
