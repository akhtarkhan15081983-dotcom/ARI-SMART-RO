import 'package:flutter/material.dart';

import '../../models/complaint_model.dart';
import '../../models/customer_model.dart';
import '../../models/engineer_model.dart';

import '../../services/api_service.dart';
import '../../services/complaint_service.dart';
import '../../services/customer_service.dart';
import '../../services/engineer_service.dart';

class NewComplaintScreen extends StatefulWidget {
  const NewComplaintScreen({super.key});

  @override
  State<NewComplaintScreen> createState() => _NewComplaintScreenState();
}

class _NewComplaintScreenState extends State<NewComplaintScreen> {
  // ============================================================
  // SERVICES
  // ============================================================

  final CustomerService _customerService = CustomerService();

  final EngineerService _engineerService = EngineerService();

  final ComplaintService _complaintService = ComplaintService();

  // ============================================================
  // FORM
  // ============================================================

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  final TextEditingController _descriptionController = TextEditingController();

  final TextEditingController _scheduledDateController =
      TextEditingController();

  // ============================================================
  // DATA
  // ============================================================

  List<CustomerModel> _customers = [];

  List<EngineerModel> _engineers = [];

  CustomerModel? _selectedCustomer;

  EngineerModel? _selectedEngineer;

  DateTime? _scheduledDate;

  // ============================================================
  // STATE
  // ============================================================

  String _role = "";

  bool _isCustomer = false;

  bool _loadingCustomers = true;

  bool _loadingEngineers = true;

  bool _submitting = false;

  String _complaintType = "RO_NOT_WORKING";

  String _priority = "NORMAL";

  // ============================================================
  // COMPLAINT TYPES
  // ============================================================

  final List<Map<String, String>> _complaintTypes = const [
    {"value": "RO_NOT_WORKING", "label": "RO Not Working"},
    {"value": "WATER_LEAKAGE", "label": "Water Leakage"},
    {"value": "LOW_WATER_FLOW", "label": "Low Water Flow"},
    {"value": "BAD_TASTE", "label": "Bad Taste / Smell"},
    {"value": "NO_POWER", "label": "Power Problem"},
    {"value": "FILTER_PROBLEM", "label": "Filter Problem"},
    {"value": "MOTOR_PROBLEM", "label": "Motor / Pump Problem"},
    {"value": "OTHER", "label": "Other"},
  ];

  // ============================================================
  // PRIORITIES
  // ============================================================

  final List<Map<String, String>> _priorities = const [
    {"value": "NORMAL", "label": "Normal"},
    {"value": "URGENT", "label": "Urgent"},
    {"value": "EMERGENCY", "label": "Emergency"},
  ];

  // ============================================================
  // INIT
  // ============================================================

  @override
  void initState() {
    super.initState();

    _initialize();
  }

  // ============================================================
  // INITIALIZE
  // ============================================================

  Future<void> _initialize() async {
    final role = await ApiService.getRole();

    final normalizedRole = (role ?? "").trim().toUpperCase();

    final customerMode = normalizedRole == "CUSTOMER";

    debugPrint("========================================");

    debugPrint("COMPLAINT SCREEN ROLE: $normalizedRole");

    debugPrint("COMPLAINT SCREEN CUSTOMER: $customerMode");

    debugPrint("========================================");

    if (!mounted) return;

    setState(() {
      _role = normalizedRole;

      _isCustomer = customerMode;
    });

    // ==========================================================
    // CUSTOMER
    // ==========================================================
    //
    // Customer ko manually customer select nahi karna.
    //
    // Backend CustomerListAPIView CUSTOMER role ke liye
    // sirf logged-in user's phone wala customer return karta hai.
    //
    // Isliye getCustomers() se apna exact CustomerModel
    // mil jayega.
    // ==========================================================

    if (customerMode) {
      await _loadMyCustomer();

      if (!mounted) return;

      setState(() {
        _loadingCustomers = false;
        _loadingEngineers = false;
      });

      return;
    }

    // ==========================================================
    // STAFF
    // ==========================================================

    await Future.wait([_loadCustomers(), _loadEngineers()]);
  }

  // ============================================================
  // LOAD CUSTOMER
  // ============================================================

  Future<void> _loadMyCustomer() async {
    try {
      final customers = await _customerService.getCustomers();

      if (!mounted) return;

      if (customers.isEmpty) {
        _showError("Customer profile not found.");

        return;
      }

      setState(() {
        _customers = customers;

        _selectedCustomer = customers.first;
      });
    } catch (e) {
      if (!mounted) return;

      _showError("Unable to load your customer profile.\n$e");
    }
  }

  // ============================================================
  // LOAD ALL / ASSIGNED CUSTOMERS
  // ============================================================

  Future<void> _loadCustomers() async {
    try {
      final customers = await _customerService.getCustomers();

      if (!mounted) return;

      setState(() {
        _customers = customers;

        _loadingCustomers = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loadingCustomers = false;
      });

      _showError("Unable to load customers.\n$e");
    }
  }

  // ============================================================
  // LOAD ENGINEERS
  // ============================================================

  Future<void> _loadEngineers() async {
    try {
      final engineers = await _engineerService.getEngineers();

      if (!mounted) return;

      setState(() {
        _engineers = engineers;

        _loadingEngineers = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loadingEngineers = false;
      });

      _showError("Unable to load engineers.\n$e");
    }
  }

  // ============================================================
  // DATE PICKER
  // ============================================================

  Future<void> _pickScheduledDate() async {
    if (_isCustomer) {
      return;
    }

    final now = DateTime.now();

    final selected = await showDatePicker(
      context: context,

      initialDate: _scheduledDate ?? now,

      firstDate: now,

      lastDate: DateTime(now.year + 2),
    );

    if (selected == null) {
      return;
    }

    if (!mounted) return;

    setState(() {
      _scheduledDate = selected;

      _scheduledDateController.text = _formatDate(selected);
    });
  }

  // ============================================================
  // DATE FORMAT
  // ============================================================

  String _formatDate(DateTime date) {
    final day = date.day.toString().padLeft(2, "0");

    final month = date.month.toString().padLeft(2, "0");

    return "${date.year}-$month-$day";
  }

  // ============================================================
  // COMPLAINT TYPE LABEL
  // ============================================================

  String _complaintTypeLabel(String value) {
    final item = _complaintTypes.firstWhere(
      (item) => item["value"] == value,
      orElse: () => {"value": value, "label": value},
    );

    return item["label"] ?? value;
  }

  // ============================================================
  // PRIORITY LABEL
  // ============================================================

  String _priorityLabel(String value) {
    final item = _priorities.firstWhere(
      (item) => item["value"] == value,
      orElse: () => {"value": value, "label": value},
    );

    return item["label"] ?? value;
  }

  // ============================================================
  // SUBMIT
  // ============================================================

  Future<void> _submitComplaint() async {
    if (_submitting) {
      return;
    }

    final form = _formKey.currentState;

    if (form == null || !form.validate()) {
      return;
    }

    // ==========================================================
    // CUSTOMER VALIDATION
    // ==========================================================

    if (_selectedCustomer == null) {
      _showError(
        _isCustomer
            ? "Your customer profile could not be loaded."
            : "Please select a customer.",
      );

      return;
    }

    // ==========================================================
    // CUSTOMER RULE
    // ==========================================================
    //
    // Customer:
    // - own customer ID
    // - NORMAL priority
    // - no engineer
    // - no scheduled date
    //
    // Staff:
    // - selected customer
    // - selected priority
    // - optional engineer
    // - optional schedule
    // ==========================================================

    final int customerId = _selectedCustomer!.id;

    final String priority = _isCustomer ? "NORMAL" : _priority;

    final int? engineerId = _isCustomer ? null : _selectedEngineer?.id;

    final String? scheduledDate = _isCustomer || _scheduledDate == null
        ? null
        : _formatDate(_scheduledDate!);

    setState(() {
      _submitting = true;
    });

    try {
      final ComplaintModel complaint = await _complaintService.createComplaint(
        customer: customerId,

        complaintType: _complaintType,

        description: _descriptionController.text.trim(),

        priority: priority,

        engineer: engineerId,

        scheduledDate: scheduledDate,
      );

      if (!mounted) return;

      setState(() {
        _submitting = false;
      });

      await _showSuccess(complaint);

      if (!mounted) return;

      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _submitting = false;
      });

      _showError("Failed to create complaint.\n$e");
    }
  }

  // ============================================================
  // SUCCESS
  // ============================================================

  Future<void> _showSuccess(ComplaintModel complaint) async {
    await showDialog<void>(
      context: context,

      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(Icons.check_circle, color: Colors.green, size: 52),

          title: const Text("Complaint Created"),

          content: Text(
            "Complaint ID:\n"
            "${complaint.complaintId}",

            textAlign: TextAlign.center,
          ),

          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
              },

              child: const Text("OK"),
            ),
          ],
        );
      },
    );
  }

  // ============================================================
  // ERROR
  // ============================================================

  void _showError(String message) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }

  // ============================================================
  // CUSTOMER SEARCH TEXT
  // ============================================================

  String _customerSearchText(CustomerModel customer) {
    return [
      customer.customerName,
      customer.customerId,
      customer.phone,
      customer.cardNumber,
      customer.oldCardNumber,
    ].join(" ");
  }

  // ============================================================
  // CUSTOMER SEARCH MATCH
  // ============================================================

  bool _matchesCustomer(CustomerModel customer, String query) {
    final searchText = _customerSearchText(customer).toLowerCase();

    final cleanQuery = query.trim().toLowerCase();

    if (cleanQuery.isEmpty) {
      return true;
    }

    return searchText.contains(cleanQuery);
  }

  // ============================================================
  // OPEN CUSTOMER SEARCH
  // ============================================================

  Future<void> _openCustomerSearch() async {
    if (_isCustomer || _submitting || _loadingCustomers) {
      return;
    }

    final selected = await showModalBottomSheet<CustomerModel>(
      context: context,

      isScrollControlled: true,

      backgroundColor: Colors.transparent,

      builder: (sheetContext) {
        return _CustomerSearchSheet(
          customers: _customers,

          selectedCustomer: _selectedCustomer,

          matchesCustomer: _matchesCustomer,
        );
      },
    );

    if (selected == null || !mounted) {
      return;
    }

    setState(() {
      _selectedCustomer = selected;
    });
  }

  // ============================================================
  // CUSTOMER SELECTOR
  // ============================================================

  Widget _buildCustomerSelector() {
    if (_isCustomer) {
      return _buildMyCustomerCard();
    }

    if (_loadingCustomers) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 20),

        child: Center(child: CircularProgressIndicator()),
      );
    }

    return InkWell(
      onTap: _submitting ? null : _openCustomerSearch,

      borderRadius: BorderRadius.circular(4),

      child: InputDecorator(
        decoration: const InputDecoration(
          labelText: "Customer",

          prefixIcon: Icon(Icons.person),

          suffixIcon: Icon(Icons.search),

          border: OutlineInputBorder(),
        ),

        child: _selectedCustomer == null
            ? const Text(
                "Search and select customer",

                style: TextStyle(color: Colors.grey),
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,

                children: [
                  Text(
                    _selectedCustomer!.customerName,

                    style: const TextStyle(
                      fontWeight: FontWeight.w600,

                      fontSize: 15,
                    ),

                    overflow: TextOverflow.ellipsis,
                  ),

                  const SizedBox(height: 3),

                  Text(
                    "${_selectedCustomer!.phone} • "
                    "${_selectedCustomer!.customerId}",

                    style: TextStyle(color: Colors.grey.shade700, fontSize: 12),

                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
      ),
    );
  }

  // ============================================================
  // CUSTOMER SELF CARD
  // ============================================================

  Widget _buildMyCustomerCard() {
    final customer = _selectedCustomer;

    if (customer == null) {
      return Container(
        width: double.infinity,

        padding: const EdgeInsets.all(14),

        decoration: BoxDecoration(
          color: Colors.orange.shade50,

          borderRadius: BorderRadius.circular(12),
        ),

        child: const Text("Loading customer profile..."),
      );
    }

    return Container(
      width: double.infinity,

      padding: const EdgeInsets.all(14),

      decoration: BoxDecoration(
        color: Colors.green.shade50,

        borderRadius: BorderRadius.circular(12),

        border: Border.all(color: Colors.green.shade200),
      ),

      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          Row(
            children: [
              Icon(Icons.verified_user, color: Colors.green.shade700),

              const SizedBox(width: 8),

              const Expanded(
                child: Text(
                  "Your Customer Account",

                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Text(
            customer.customerName,

            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 5),

          Text(
            "Customer ID: "
            "${customer.customerId}",
          ),

          Text(
            "Phone: "
            "${customer.phone}",
          ),

          if (customer.cardNumber.isNotEmpty)
            Text(
              "Card: "
              "${customer.cardNumber}",
            ),

          if (customer.area.isNotEmpty)
            Text(
              "Area: "
              "${customer.area}",
            ),
        ],
      ),
    );
  }

  // ============================================================
  // SELECTED CUSTOMER INFO
  // ============================================================

  Widget _buildSelectedCustomerInfo() {
    if (_isCustomer) {
      return const SizedBox.shrink();
    }

    final customer = _selectedCustomer;

    if (customer == null) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,

      margin: const EdgeInsets.only(top: 10),

      padding: const EdgeInsets.all(14),

      decoration: BoxDecoration(
        color: Colors.blue.shade50,

        borderRadius: BorderRadius.circular(12),

        border: Border.all(color: Colors.blue.shade100),
      ),

      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          Text(
            customer.customerName,

            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 6),

          Text(
            "Customer ID: "
            "${customer.customerId}",
          ),

          Text(
            "Phone: "
            "${customer.phone}",
          ),

          if (customer.cardNumber.isNotEmpty)
            Text(
              "Card: "
              "${customer.cardNumber}",
            ),

          if (customer.oldCardNumber.isNotEmpty)
            Text(
              "Old Card: "
              "${customer.oldCardNumber}",
            ),

          if (customer.area.isNotEmpty)
            Text(
              "Area: "
              "${customer.area}",
            ),
        ],
      ),
    );
  }

  // ============================================================
  // ENGINEER SELECTOR
  // ============================================================

  Widget _buildEngineerSelector() {
    if (_isCustomer) {
      return const SizedBox.shrink();
    }

    if (_loadingEngineers) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 10),

        child: Center(child: CircularProgressIndicator()),
      );
    }

    return DropdownButtonFormField<EngineerModel>(
      initialValue: _selectedEngineer,

      isExpanded: true,

      decoration: const InputDecoration(
        labelText: "Assign Engineer",

        prefixIcon: Icon(Icons.engineering),

        border: OutlineInputBorder(),
      ),

      hint: const Text("Select engineer (optional)"),

      items: _engineers.map((engineer) {
        return DropdownMenuItem<EngineerModel>(
          value: engineer,

          child: Text(engineer.name, overflow: TextOverflow.ellipsis),
        );
      }).toList(),

      onChanged: _submitting
          ? null
          : (value) {
              setState(() {
                _selectedEngineer = value;
              });
            },
    );
  }

  // ============================================================
  // SECTION TITLE
  // ============================================================

  Widget _sectionTitle(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 21, color: Colors.blue),

        const SizedBox(width: 8),

        Text(
          title,

          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("New Complaint"), centerTitle: true),

      body: SafeArea(
        child: Form(
          key: _formKey,

          child: ListView(
            padding: const EdgeInsets.all(16),

            children: [
              // ==================================================
              // CUSTOMER
              // ==================================================
              _sectionTitle("Customer", Icons.person),

              const SizedBox(height: 10),

              _buildCustomerSelector(),

              _buildSelectedCustomerInfo(),

              const SizedBox(height: 24),

              // ==================================================
              // COMPLAINT DETAILS
              // ==================================================
              _sectionTitle("Complaint Details", Icons.report_problem),

              const SizedBox(height: 10),

              DropdownButtonFormField<String>(
                initialValue: _complaintType,

                decoration: const InputDecoration(
                  labelText: "Complaint Type",

                  prefixIcon: Icon(Icons.build),

                  border: OutlineInputBorder(),
                ),

                items: _complaintTypes.map((item) {
                  return DropdownMenuItem<String>(
                    value: item["value"],

                    child: Text(item["label"] ?? ""),
                  );
                }).toList(),

                onChanged: _submitting
                    ? null
                    : (value) {
                        if (value == null) {
                          return;
                        }

                        setState(() {
                          _complaintType = value;
                        });
                      },
              ),

              const SizedBox(height: 14),

              // ==================================================
              // DESCRIPTION
              // ==================================================
              TextFormField(
                controller: _descriptionController,

                enabled: !_submitting,

                minLines: 4,

                maxLines: 7,

                textInputAction: TextInputAction.newline,

                decoration: const InputDecoration(
                  labelText: "Complaint Description",

                  hintText: "Describe your complaint...",

                  alignLabelWithHint: true,

                  prefixIcon: Padding(
                    padding: EdgeInsets.only(bottom: 70),

                    child: Icon(Icons.description),
                  ),

                  border: OutlineInputBorder(),
                ),

                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return "Please enter complaint description";
                  }

                  if (value.trim().length < 5) {
                    return "Description is too short";
                  }

                  return null;
                },
              ),

              const SizedBox(height: 14),

              // ==================================================
              // CUSTOMER
              // PRIORITY
              // ==================================================
              if (_isCustomer) ...[
                Container(
                  width: double.infinity,

                  padding: const EdgeInsets.all(13),

                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,

                    borderRadius: BorderRadius.circular(10),
                  ),

                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,

                    children: [
                      Icon(Icons.info_outline, color: Colors.blue.shade700),

                      const SizedBox(width: 9),

                      const Expanded(
                        child: Text(
                          "Priority: Normal\n"
                          "Our team will review your complaint "
                          "and assign an engineer.",
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 28),
              ],

              // ==================================================
              // STAFF ONLY
              // ==================================================
              if (!_isCustomer) ...[
                // ------------------------------------------------
                // PRIORITY
                // ------------------------------------------------
                DropdownButtonFormField<String>(
                  initialValue: _priority,

                  decoration: const InputDecoration(
                    labelText: "Priority",

                    prefixIcon: Icon(Icons.priority_high),

                    border: OutlineInputBorder(),
                  ),

                  items: _priorities.map((item) {
                    return DropdownMenuItem<String>(
                      value: item["value"],

                      child: Text(item["label"] ?? ""),
                    );
                  }).toList(),

                  onChanged: _submitting
                      ? null
                      : (value) {
                          if (value == null) {
                            return;
                          }

                          setState(() {
                            _priority = value;
                          });
                        },
                ),

                const SizedBox(height: 24),

                // ------------------------------------------------
                // ASSIGNMENT
                // ------------------------------------------------
                _sectionTitle("Assignment", Icons.assignment_ind),

                const SizedBox(height: 10),

                _buildEngineerSelector(),

                const SizedBox(height: 14),

                // ------------------------------------------------
                // SCHEDULED DATE
                // ------------------------------------------------
                TextFormField(
                  controller: _scheduledDateController,

                  readOnly: true,

                  enabled: !_submitting,

                  onTap: _pickScheduledDate,

                  decoration: InputDecoration(
                    labelText: "Scheduled Date",

                    hintText: "Optional",

                    prefixIcon: const Icon(Icons.calendar_today),

                    suffixIcon: IconButton(
                      icon: const Icon(Icons.date_range),

                      onPressed: _submitting ? null : _pickScheduledDate,
                    ),

                    border: const OutlineInputBorder(),
                  ),
                ),

                const SizedBox(height: 28),
              ],

              // ==================================================
              // CREATE BUTTON
              // ==================================================
              SizedBox(
                height: 52,

                child: ElevatedButton.icon(
                  onPressed: _submitting ? null : _submitComplaint,

                  icon: _submitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,

                          child: CircularProgressIndicator(
                            strokeWidth: 2,

                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.send),

                  label: Text(
                    _submitting ? "Creating Complaint..." : "Create Complaint",

                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 12),

              // ==================================================
              // SUMMARY
              // ==================================================
              Container(
                padding: const EdgeInsets.all(12),

                decoration: BoxDecoration(
                  color: Colors.grey.shade100,

                  borderRadius: BorderRadius.circular(10),
                ),

                child: Text(
                  "Complaint Type: "
                  "${_complaintTypeLabel(_complaintType)}\n"
                  "Priority: "
                  "${_isCustomer ? "Normal" : _priorityLabel(_priority)}",

                  style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                ),
              ),

              const SizedBox(height: 30),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // DISPOSE
  // ============================================================

  @override
  void dispose() {
    _descriptionController.dispose();

    _scheduledDateController.dispose();

    super.dispose();
  }
}

// ==================================================================
// CUSTOMER SEARCH SHEET
// ==================================================================

class _CustomerSearchSheet extends StatefulWidget {
  final List<CustomerModel> customers;

  final CustomerModel? selectedCustomer;

  final bool Function(CustomerModel, String) matchesCustomer;

  const _CustomerSearchSheet({
    required this.customers,
    required this.selectedCustomer,
    required this.matchesCustomer,
  });

  @override
  State<_CustomerSearchSheet> createState() => _CustomerSearchSheetState();
}

class _CustomerSearchSheetState extends State<_CustomerSearchSheet> {
  // ============================================================
  // SEARCH
  // ============================================================

  final TextEditingController _searchController = TextEditingController();

  String _query = "";

  // ============================================================
  // DISPOSE
  // ============================================================

  @override
  void dispose() {
    _searchController.dispose();

    super.dispose();
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final filtered = widget.customers
        .where((customer) => widget.matchesCustomer(customer, _query))
        .toList();

    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(bottom: bottomInset),

        child: Container(
          height: MediaQuery.of(context).size.height * 0.82,

          decoration: const BoxDecoration(
            color: Colors.white,

            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),

          child: Column(
            children: [
              // ==================================================
              // HEADER
              // ==================================================
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 8, 10),

                child: Row(
                  children: [
                    const Expanded(
                      child: Text(
                        "Search Customer",

                        style: TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),

                    IconButton(
                      onPressed: () {
                        Navigator.of(context).pop();
                      },

                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),

              // ==================================================
              // SEARCH FIELD
              // ==================================================
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),

                child: TextField(
                  controller: _searchController,

                  autofocus: true,

                  onChanged: (value) {
                    setState(() {
                      _query = value;
                    });
                  },

                  decoration: InputDecoration(
                    hintText: "Name, phone, customer ID, card...",

                    prefixIcon: const Icon(Icons.search),

                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            onPressed: () {
                              _searchController.clear();

                              setState(() {
                                _query = "";
                              });
                            },

                            icon: const Icon(Icons.clear),
                          ),

                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 10),

              // ==================================================
              // COUNT
              // ==================================================
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),

                child: Align(
                  alignment: Alignment.centerLeft,

                  child: Text(
                    "${filtered.length} customer(s)",

                    style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                  ),
                ),
              ),

              const SizedBox(height: 4),

              // ==================================================
              // LIST
              // ==================================================
              Expanded(
                child: filtered.isEmpty
                    ? const Center(child: Text("No customer found"))
                    : ListView.separated(
                        padding: const EdgeInsets.symmetric(vertical: 8),

                        itemCount: filtered.length,

                        separatorBuilder: (_, _) => const Divider(height: 1),

                        itemBuilder: (context, index) {
                          final customer = filtered[index];

                          final selected =
                              widget.selectedCustomer?.id == customer.id;

                          return ListTile(
                            leading: CircleAvatar(
                              child: const Icon(Icons.person),
                            ),

                            title: Text(
                              customer.customerName,

                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),

                            subtitle: Text(
                              "${customer.phone} • "
                              "${customer.customerId}\n"
                              "${customer.cardNumber}",

                              maxLines: 2,

                              overflow: TextOverflow.ellipsis,
                            ),

                            trailing: selected
                                ? const Icon(
                                    Icons.check_circle,

                                    color: Colors.green,
                                  )
                                : null,

                            onTap: () {
                              Navigator.of(context).pop(customer);
                            },
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
}
