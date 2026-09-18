import 'package:flutter/material.dart';

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
    if (_designationFilter != 'ALL' && designation != _designationFilter) return false;
    if (_accountFilter == 'ACTIVE' && !active) return false;
    if (_accountFilter == 'INACTIVE' && active) return false;
    return matchesAllSearchTerms(_query, [
      (employee['name'] ?? '').toString(),
      (employee['employee_id'] ?? '').toString(),
      (employee['phone'] ?? '').toString(),
      (employee['email'] ?? '').toString(),
      designation,
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
    String designation = 'ENGINEER', gender = 'OTHER';
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
                        decoration: const InputDecoration(labelText: 'Designation'),
                        items: _designations
                            .map((v) => DropdownMenuItem(value: v, child: Text(v == 'ALL' ? 'All designations' : v)))
                            .toList(),
                        onChanged: (v) => setState(() => _designationFilter = v ?? 'ALL'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _accountFilter,
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
                        '${employee['employee_id']} • ${employee['phone']}\n${employee['designation']} • ₹${employee['salary']}',
                      ),
                      isThreeLine: true,
                      trailing: Icon(
                        employee['is_active'] == true
                            ? Icons.verified_rounded
                            : Icons.block_rounded,
                        color: employee['is_active'] == true
                            ? Colors.green
                            : Colors.red,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
  );
}
