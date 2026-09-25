import 'package:flutter/material.dart';

import '../../models/complaint_model.dart';
import '../../models/customer_model.dart';
import '../../models/engineer_model.dart';
import '../../services/api_service.dart';
import '../../services/complaint_service.dart';
import '../../services/customer_service.dart';
import '../../services/engineer_service.dart';
import '../../utils/complaint_customer_scope.dart';

class NewComplaintScreen extends StatefulWidget {
  const NewComplaintScreen({super.key});

  @override
  State<NewComplaintScreen> createState() => _NewComplaintScreenState();
}

class _NewComplaintScreenState extends State<NewComplaintScreen> {
  final CustomerService _customerService = CustomerService();
  final EngineerService _engineerService = EngineerService();
  final ComplaintService _complaintService = ComplaintService();
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _scheduledDateController = TextEditingController();

  List<CustomerModel> _customers = [];
  List<EngineerModel> _engineers = [];
  CustomerModel? _selectedCustomer;
  EngineerModel? _selectedEngineer;
  DateTime? _scheduledDate;
  String _role = '';
  bool _loadingCustomers = true;
  bool _loadingEngineers = true;
  bool _submitting = false;
  String _complaintType = 'RO_NOT_WORKING';
  String _priority = 'NORMAL';

  bool get _isCustomer => _role == 'CUSTOMER';

  final List<Map<String, String>> _complaintTypes = const [
    {'value': 'RO_NOT_WORKING', 'label': 'RO Not Working'},
    {'value': 'WATER_LEAKAGE', 'label': 'Water Leakage'},
    {'value': 'LOW_WATER_FLOW', 'label': 'Low Water Flow'},
    {'value': 'BAD_TASTE', 'label': 'Bad Taste / Smell'},
    {'value': 'ELECTRICAL', 'label': 'Electrical Problem'},
    {'value': 'FILTER_PROBLEM', 'label': 'Filter Problem'},
    {'value': 'PUMP_PROBLEM', 'label': 'Motor / Pump Problem'},
    {'value': 'OTHER', 'label': 'Other'},
  ];

  final List<Map<String, String>> _priorities = const [
    {'value': 'NORMAL', 'label': 'Normal'},
    {'value': 'URGENT', 'label': 'Urgent'},
    {'value': 'EMERGENCY', 'label': 'Emergency'},
  ];

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    final role = (await ApiService.getRole() ?? '').trim().toUpperCase();
    if (!mounted) return;
    setState(() => _role = role);

    final scope = complaintCustomerScopeForRole(role);
    if (scope == ComplaintCustomerScope.own) {
      await _loadOwnCustomer();
      if (mounted) {
        setState(() {
          _loadingCustomers = false;
          _loadingEngineers = false;
        });
      }
      return;
    }

    if (scope == ComplaintCustomerScope.assigned) {
      await Future.wait([_loadAssignedCustomers(), _loadEngineers()]);
      return;
    }

    await Future.wait([_loadAllCustomers(), _loadEngineers()]);
  }

  Future<void> _loadOwnCustomer() async {
    try {
      final customers = await _customerService.getCustomers();
      if (!mounted) return;
      if (customers.isEmpty) {
        _message('Customer profile not found.');
        return;
      }
      setState(() {
        _customers = customers;
        _selectedCustomer = customers.first;
      });
    } catch (e) {
      _message('Unable to load your customer profile.');
    }
  }

  Future<void> _loadAssignedCustomers() async {
    try {
      final customers = await _customerService.getMyCustomers();
      if (!mounted) return;
      setState(() {
        _customers = customers;
        _loadingCustomers = false;
        if (customers.length == 1) _selectedCustomer = customers.first;
      });
    } catch (e) {
      if (mounted) setState(() => _loadingCustomers = false);
      _message('Unable to load assigned customers.');
    }
  }

  Future<void> _loadAllCustomers() async {
    try {
      final customers = await _customerService.getCustomers();
      if (!mounted) return;
      setState(() {
        _customers = customers;
        _loadingCustomers = false;
      });
    } catch (e) {
      if (mounted) setState(() => _loadingCustomers = false);
      _message('Unable to load customers.');
    }
  }

  Future<void> _loadEngineers() async {
    try {
      final engineers = await _engineerService.getEngineers();
      if (!mounted) return;
      setState(() {
        _engineers = engineers;
        _loadingEngineers = false;
      });
    } catch (e) {
      if (mounted) setState(() => _loadingEngineers = false);
      _message('Unable to load engineers.');
    }
  }

  void _message(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }

  Future<void> _pickScheduledDate() async {
    if (_isCustomer) return;
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _scheduledDate ?? now,
      firstDate: now,
      lastDate: DateTime(now.year + 2),
    );
    if (date == null || !mounted) return;
    setState(() {
      _scheduledDate = date;
      _scheduledDateController.text = _formatDate(date);
    });
  }

  bool _matches(CustomerModel customer, String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return true;
    return [
      customer.customerName,
      customer.customerId,
      customer.phone,
      customer.cardNumber,
      customer.oldCardNumber,
    ].join(' ').toLowerCase().contains(q);
  }

  Future<void> _chooseCustomer() async {
    if (_isCustomer || _loadingCustomers || _submitting) return;
    final selected = await showModalBottomSheet<CustomerModel>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _CustomerSearchSheet(
        customers: _customers,
        selected: _selectedCustomer,
        matches: _matches,
      ),
    );
    if (selected != null && mounted) {
      setState(() => _selectedCustomer = selected);
    }
  }

  Future<void> _submit() async {
    if (_submitting || !(_formKey.currentState?.validate() ?? false)) return;
    if (_selectedCustomer == null) {
      _message(_isCustomer ? 'Customer profile not found.' : 'Please select a customer.');
      return;
    }

    setState(() => _submitting = true);
    try {
      final ComplaintModel complaint = await _complaintService.createComplaint(
        customer: _selectedCustomer!.id,
        complaintType: _complaintType,
        description: _descriptionController.text.trim(),
        priority: _isCustomer ? 'NORMAL' : _priority,
        engineer: _isCustomer ? null : _selectedEngineer?.id,
        scheduledDate: _isCustomer || _scheduledDate == null
            ? null
            : _formatDate(_scheduledDate!),
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          icon: const Icon(Icons.check_circle, color: Colors.green, size: 48),
          title: const Text('Complaint Created'),
          content: Text('Complaint ID: ${complaint.complaintId}'),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      _message(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Widget _customerSelector() {
    if (_loadingCustomers) {
      return const Center(child: Padding(
        padding: EdgeInsets.all(16),
        child: CircularProgressIndicator(),
      ));
    }
    if (_isCustomer) {
      final c = _selectedCustomer;
      return Card(
        child: ListTile(
          leading: const Icon(Icons.verified_user),
          title: Text(c?.customerName ?? 'Customer'),
          subtitle: Text(c == null ? 'Profile unavailable' : '${c.customerId} • ${c.phone}'),
        ),
      );
    }
    return InkWell(
      onTap: _chooseCustomer,
      child: InputDecorator(
        decoration: const InputDecoration(
          labelText: 'Customer',
          prefixIcon: Icon(Icons.person_search),
          suffixIcon: Icon(Icons.search),
          border: OutlineInputBorder(),
        ),
        child: _selectedCustomer == null
            ? Text('Search from ${_customers.length} customer(s)')
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _selectedCustomer!.customerName,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  Text('${_selectedCustomer!.customerId} • ${_selectedCustomer!.phone}'),
                ],
              ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Complaint'), centerTitle: true),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Customer', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 10),
            _customerSelector(),
            const SizedBox(height: 20),
            DropdownButtonFormField<String>(
              initialValue: _complaintType,
              decoration: const InputDecoration(
                labelText: 'Complaint Type',
                prefixIcon: Icon(Icons.build_circle_outlined),
                border: OutlineInputBorder(),
              ),
              items: _complaintTypes
                  .map((item) => DropdownMenuItem(
                        value: item['value'],
                        child: Text(item['label'] ?? ''),
                      ))
                  .toList(),
              onChanged: _submitting
                  ? null
                  : (value) {
                      if (value != null) setState(() => _complaintType = value);
                    },
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _descriptionController,
              minLines: 4,
              maxLines: 7,
              enabled: !_submitting,
              decoration: const InputDecoration(
                labelText: 'Complaint Description',
                hintText: 'Describe the customer issue clearly...',
                alignLabelWithHint: true,
                border: OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.trim().length < 5) {
                  return 'Please enter a clear complaint description';
                }
                return null;
              },
            ),
            if (!_isCustomer) ...[
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: _priority,
                decoration: const InputDecoration(
                  labelText: 'Priority',
                  prefixIcon: Icon(Icons.priority_high),
                  border: OutlineInputBorder(),
                ),
                items: _priorities
                    .map((item) => DropdownMenuItem(
                          value: item['value'],
                          child: Text(item['label'] ?? ''),
                        ))
                    .toList(),
                onChanged: _submitting
                    ? null
                    : (value) {
                        if (value != null) setState(() => _priority = value);
                      },
              ),
              const SizedBox(height: 14),
              if (_loadingEngineers)
                const Center(child: CircularProgressIndicator())
              else
                DropdownButtonFormField<EngineerModel>(
                  initialValue: _selectedEngineer,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Assign Engineer',
                    prefixIcon: Icon(Icons.engineering),
                    border: OutlineInputBorder(),
                  ),
                  hint: const Text('Select engineer (optional)'),
                  items: _engineers
                      .map((engineer) => DropdownMenuItem(
                            value: engineer,
                            child: Text(engineer.name, overflow: TextOverflow.ellipsis),
                          ))
                      .toList(),
                  onChanged: _submitting
                      ? null
                      : (value) => setState(() => _selectedEngineer = value),
                ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _scheduledDateController,
                readOnly: true,
                onTap: _pickScheduledDate,
                decoration: const InputDecoration(
                  labelText: 'Scheduled Date',
                  hintText: 'Optional',
                  prefixIcon: Icon(Icons.calendar_today),
                  border: OutlineInputBorder(),
                ),
              ),
            ],
            const SizedBox(height: 24),
            SizedBox(
              height: 52,
              child: FilledButton.icon(
                onPressed: _submitting ? null : _submit,
                icon: _submitting
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send),
                label: Text(_submitting ? 'Creating Complaint...' : 'Create Complaint'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    _scheduledDateController.dispose();
    super.dispose();
  }
}

class _CustomerSearchSheet extends StatefulWidget {
  const _CustomerSearchSheet({
    required this.customers,
    required this.selected,
    required this.matches,
  });

  final List<CustomerModel> customers;
  final CustomerModel? selected;
  final bool Function(CustomerModel, String) matches;

  @override
  State<_CustomerSearchSheet> createState() => _CustomerSearchSheetState();
}

class _CustomerSearchSheetState extends State<_CustomerSearchSheet> {
  final TextEditingController _controller = TextEditingController();
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final filtered = widget.customers.where((c) => widget.matches(c, _query)).toList();
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: Container(
          height: MediaQuery.of(context).size.height * .82,
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Search Customer (${widget.customers.length})',
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: TextField(
                  controller: _controller,
                  autofocus: true,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: const InputDecoration(
                    hintText: 'Name, phone, customer ID, card...',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: filtered.isEmpty
                    ? const Center(child: Text('No customer found'))
                    : ListView.separated(
                        itemCount: filtered.length,
                        separatorBuilder: (_, _) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final customer = filtered[index];
                          final selected = widget.selected?.id == customer.id;
                          return ListTile(
                            leading: const CircleAvatar(child: Icon(Icons.person)),
                            title: Text(customer.customerName),
                            subtitle: Text(
                              '${customer.phone} • ${customer.customerId}\n${customer.cardNumber}',
                            ),
                            trailing: selected
                                ? const Icon(Icons.check_circle, color: Colors.green)
                                : null,
                            onTap: () => Navigator.pop(context, customer),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
