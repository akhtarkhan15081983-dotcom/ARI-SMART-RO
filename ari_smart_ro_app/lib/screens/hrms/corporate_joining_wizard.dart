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
  final aadhaar = TextEditingController();
  final pan = TextEditingController();
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
  bool incentiveEligible = true;
  bool overtimeEligible = true;
  bool policyAcknowledged = false;
  bool sopAcknowledged = false;
  bool safetyAcknowledged = false;
  bool aadhaarAvailable = false;
  bool panAvailable = false;
  bool addressProofAvailable = false;
  bool bankProofAvailable = false;
  bool qualificationAvailable = false;

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
      aadhaar,
      pan,
      department,
      jobTitle,
      grade,
      workLocation,
      salary,
      bankName,
      bankAccount,
      ifsc,
      password,
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

  Widget _gap() => const SizedBox(height: 12);

  @override
  Widget build(BuildContext context) {
    final desktop = MediaQuery.sizeOf(context).width >= 900;
    return Scaffold(
      appBar: AppBar(
        title: const Text('New Employee Joining'),
        actions: const [
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Center(child: Text('CORPORATE ONBOARDING')),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: Stepper(
          type: desktop ? StepperType.horizontal : StepperType.vertical,
          currentStep: _step,
          onStepTapped: (value) => setState(() => _step = value),
          controlsBuilder: (context, details) => Padding(
            padding: const EdgeInsets.only(top: 20),
            child: Row(
              children: [
                if (_step > 0)
                  OutlinedButton.icon(
                    onPressed: _saving
                        ? null
                        : () => setState(() => _step -= 1),
                    icon: const Icon(Icons.arrow_back),
                    label: const Text('BACK'),
                  ),
                const Spacer(),
                FilledButton.icon(
                  onPressed: _saving
                      ? null
                      : (_step == 6
                          ? _submit
                          : () => setState(() => _step += 1)),
                  icon: _saving
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(_step == 6 ? Icons.how_to_reg : Icons.arrow_forward),
                  label: Text(_saving
                      ? 'CREATING...'
                      : (_step == 6 ? 'CREATE EMPLOYEE' : 'CONTINUE')),
                ),
              ],
            ),
          ),
          steps: [
            Step(
              title: const Text('Personal'),
              isActive: _step >= 0,
              content: _section('Personal details', [
                _two(
                  TextFormField(
                    controller: firstName,
                    decoration: _decoration('First name *'),
                    validator: (v) => v == null || v.trim().isEmpty ? 'Required' : null,
                  ),
                  TextFormField(
                    controller: lastName,
                    decoration: _decoration('Last name'),
                  ),
                ),
                _gap(),
                _two(
                  TextFormField(
                    controller: phone,
                    keyboardType: TextInputType.phone,
                    maxLength: 10,
                    decoration: _decoration('Mobile *'),
                    validator: (v) => (v ?? '').length == 10 ? null : '10 digits required',
                  ),
                  TextFormField(
                    controller: email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: _decoration('Email'),
                  ),
                ),
                _gap(),
                _two(
                  TextFormField(
                    controller: dob,
                    decoration: _decoration('DOB', hint: 'YYYY-MM-DD'),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: gender,
                    decoration: _decoration('Gender *'),
                    items: const [
                      DropdownMenuItem(value: 'MALE', child: Text('Male')),
                      DropdownMenuItem(value: 'FEMALE', child: Text('Female')),
                      DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                    ],
                    onChanged: (v) => setState(() => gender = v ?? 'OTHER'),
                  ),
                ),
                _gap(),
                TextFormField(
                  controller: address,
                  maxLines: 2,
                  decoration: _decoration('Residential address'),
                ),
                _gap(),
                _three(
                  TextFormField(controller: city, decoration: _decoration('City')),
                  TextFormField(controller: state, decoration: _decoration('State')),
                  TextFormField(
                    controller: pincode,
                    keyboardType: TextInputType.number,
                    decoration: _decoration('Pincode'),
                  ),
                ),
                _gap(),
                _two(
                  TextFormField(
                    controller: emergencyName,
                    decoration: _decoration('Emergency contact name'),
                  ),
                  TextFormField(
                    controller: emergencyPhone,
                    keyboardType: TextInputType.phone,
                    decoration: _decoration('Emergency contact number'),
                  ),
                ),
              ]),
            ),
            Step(
              title: const Text('Employment'),
              isActive: _step >= 1,
              content: _section('Employment details', [
                _two(
                  DropdownButtonFormField<String>(
                    initialValue: designation,
                    decoration: _decoration('Designation *'),
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
                    validator: (v) => v == null || v.trim().isEmpty ? 'Required' : null,
                  ),
                ),
                _gap(),
                _three(
                  TextFormField(
                    controller: department,
                    decoration: _decoration('Department *'),
                    validator: (v) => v == null || v.trim().isEmpty ? 'Required' : null,
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
                    decoration: _decoration('Probation period'),
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
                    trailing: const Icon(Icons.edit_calendar),
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
              title: const Text('Compensation'),
              isActive: _step >= 2,
              content: _section('Compensation & payroll setup', [
                _two(
                  TextFormField(
                    controller: salary,
                    keyboardType: TextInputType.number,
                    decoration: _decoration('Monthly salary'),
                  ),
                  TextFormField(controller: bankName, decoration: _decoration('Bank name')),
                ),
                _gap(),
                _two(
                  TextFormField(controller: bankAccount, decoration: _decoration('Bank account number')),
                  TextFormField(controller: ifsc, decoration: _decoration('IFSC')),
                ),
                _gap(),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Incentive eligible'),
                  value: incentiveEligible,
                  onChanged: (v) => setState(() => incentiveEligible = v),
                ),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Overtime eligible'),
                  value: overtimeEligible,
                  onChanged: (v) => setState(() => overtimeEligible = v),
                ),
              ]),
            ),
            Step(
              title: const Text('Documents'),
              isActive: _step >= 3,
              content: _section('Joining documents', [
                _two(
                  TextFormField(
                    controller: aadhaar,
                    keyboardType: TextInputType.number,
                    decoration: _decoration('Aadhaar number'),
                    onChanged: (_) => setState(() => aadhaarAvailable = aadhaar.text.trim().isNotEmpty),
                  ),
                  TextFormField(
                    controller: pan,
                    decoration: _decoration('PAN number'),
                    onChanged: (_) => setState(() => panAvailable = pan.text.trim().isNotEmpty),
                  ),
                ),
                _gap(),
                CheckboxListTile(
                  value: addressProofAvailable,
                  onChanged: (v) => setState(() => addressProofAvailable = v ?? false),
                  title: const Text('Address proof available'),
                  subtitle: const Text('Document record will remain pending verification until HR verifies it.'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
                CheckboxListTile(
                  value: bankProofAvailable,
                  onChanged: (v) => setState(() => bankProofAvailable = v ?? false),
                  title: const Text('Bank proof available'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
                CheckboxListTile(
                  value: qualificationAvailable,
                  onChanged: (v) => setState(() => qualificationAvailable = v ?? false),
                  title: const Text('Qualification / technical certificate available'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text(
                    'HRMS will keep these as pending/unverified until the actual document record is verified. READY FOR DUTY cannot bypass missing mandatory documents without an audited HR override.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ]),
            ),
            Step(
              title: const Text('Security'),
              isActive: _step >= 4,
              content: _section('Security & access', [
                TextFormField(
                  controller: password,
                  obscureText: true,
                  decoration: _decoration('Temporary password *', hint: '8+ characters with number/symbol'),
                  validator: (v) => (v ?? '').length < 8 ? 'Minimum 8 characters' : null,
                ),
                _gap(),
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.badge_outlined),
                  title: Text('Employee ID'),
                  subtitle: Text('Generated automatically after employee creation.'),
                ),
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.face_retouching_natural),
                  title: Text('Face enrollment'),
                  subtitle: Text('Must be completed and verified before READY FOR DUTY.'),
                ),
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.phonelink_lock),
                  title: Text('Device registration'),
                  subtitle: Text('Attendance/login device binding is completed on the employee device.'),
                ),
              ]),
            ),
            Step(
              title: const Text('Training'),
              isActive: _step >= 5,
              content: _section('Training & joining acknowledgements', [
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.school_outlined),
                  title: Text('Mandatory 30-day ARI training'),
                  subtitle: Text('Existing mandatory training assignment system will auto-sync for the employee.'),
                ),
                CheckboxListTile(
                  value: policyAcknowledged,
                  onChanged: (v) => setState(() => policyAcknowledged = v ?? false),
                  title: const Text('Company policy acknowledged'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
                CheckboxListTile(
                  value: sopAcknowledged,
                  onChanged: (v) => setState(() => sopAcknowledged = v ?? false),
                  title: const Text('SOP acknowledged'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
                CheckboxListTile(
                  value: safetyAcknowledged,
                  onChanged: (v) => setState(() => safetyAcknowledged = v ?? false),
                  title: const Text('Safety & customer-service induction acknowledged'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
              ]),
            ),
            Step(
              title: const Text('Review'),
              isActive: _step >= 6,
              content: _section('Final HR review', [
                _reviewRow('Employee', '${firstName.text} ${lastName.text}'.trim()),
                _reviewRow('Role', '$jobTitle • $department'),
                _reviewRow('Joining', _date(joiningDate)),
                _reviewRow('Employment', '$employmentType • $probationMonths month probation'),
                _reviewRow('Manager', reportingManagerId == null ? 'Pending assignment' : 'Assigned'),
                _reviewRow('Documents declared', '${[
                  aadhaarAvailable,
                  panAvailable,
                  addressProofAvailable,
                  bankProofAvailable,
                  qualificationAvailable,
                ].where((e) => e).length}/5'),
                _reviewRow('Policy/SOP/Safety', '${policyAcknowledged && sopAcknowledged && safetyAcknowledged ? 'Acknowledged' : 'Pending'}'),
                const Divider(height: 28),
                const Text(
                  'Creating the employee does not automatically mark them READY FOR DUTY. Documents, face/device security, mandatory training and HR review remain gated and auditable.',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _section(String title, List<Widget> children) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1050),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 18),
                  ...children,
                ],
              ),
            ),
          ),
        ),
      );

  Widget _two(Widget a, Widget b) => LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 700) {
            return Column(children: [a, _gap(), b]);
          }
          return Row(children: [Expanded(child: a), const SizedBox(width: 12), Expanded(child: b)]);
        },
      );

  Widget _three(Widget a, Widget b, Widget c) => LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 780) {
            return Column(children: [a, _gap(), b, _gap(), c]);
          }
          return Row(children: [
            Expanded(child: a),
            const SizedBox(width: 12),
            Expanded(child: b),
            const SizedBox(width: 12),
            Expanded(child: c),
          ]);
        },
      );

  Widget _reviewRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 180, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700))),
            Expanded(child: Text(value.isEmpty ? 'Pending' : value)),
          ],
        ),
      );

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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Complete the required joining fields.')),
      );
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
        'aadhaar_number': aadhaar.text.trim(),
        'pan_number': pan.text.trim().toUpperCase(),
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
        'role_access_assigned': true,
        'compensation_profile': {
          'salary_structure': 'MONTHLY',
          'incentive_eligible': incentiveEligible,
          'overtime_eligible': overtimeEligible,
        },
        'joining_checklist': {
          'aadhaar_declared': aadhaarAvailable,
          'pan_declared': panAvailable,
          'address_proof_declared': addressProofAvailable,
          'bank_proof_declared': bankProofAvailable,
          'qualification_declared': qualificationAvailable,
          'bank_name': bankName.text.trim(),
          'bank_account_last4': bankAccount.text.trim().length >= 4
              ? bankAccount.text.trim().substring(bankAccount.text.trim().length - 4)
              : bankAccount.text.trim(),
          'ifsc': ifsc.text.trim().toUpperCase(),
        },
        'note': 'Corporate joining wizard completed by HR.',
      });

      if (!mounted) return;
      widget.onCompleted();
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${employee['employee_id']} created. Complete documents, security, training and HR review before Ready for Duty.',
          ),
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}
