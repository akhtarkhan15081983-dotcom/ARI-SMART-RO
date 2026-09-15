import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import '../../services/engineer_service.dart';
import '../../services/api_service.dart';
import '../../models/engineer_model.dart';

import 'customer_details_screen.dart';
import 'customer_bulk_import_screen.dart';
import '../walkin/walkin_customer_screen.dart';

class CustomerListScreen extends StatefulWidget {
  const CustomerListScreen({super.key});

  @override
  State<CustomerListScreen> createState() => _CustomerListScreenState();
}

class _CustomerListScreenState extends State<CustomerListScreen> {
  // ============================================================
  // SERVICES
  // ============================================================

  final CustomerService service = CustomerService();

  final EngineerService engineerService = EngineerService();

  // ============================================================
  // SEARCH
  // ============================================================

  final TextEditingController _searchController = TextEditingController();

  String _searchQuery = "";

  _AssignmentFilter _assignmentFilter = _AssignmentFilter.all;

  // ============================================================
  // ROLE
  // ============================================================

  String _role = "";

  // ============================================================
  // CUSTOMERS
  // ============================================================

  List<CustomerModel> _customers = [];

  bool _isLoading = true;

  // ============================================================
  // FILTERED CUSTOMERS
  // ============================================================

  List<CustomerModel> get _filteredCustomers {
    final query = _searchQuery.trim().toLowerCase();

    return _customers.where((customer) {
      final matchesAssignment = switch (_assignmentFilter) {
        _AssignmentFilter.all => true,
        _AssignmentFilter.unassigned => customer.assignedEngineer == null,
        _AssignmentFilter.assigned => customer.assignedEngineer != null,
      };

      final matchesSearch = query.isEmpty ||
          customer.customerName.toLowerCase().contains(query) ||
          customer.customerId.toLowerCase().contains(query) ||
          customer.phone.toLowerCase().contains(query) ||
          customer.cardNumber.toLowerCase().contains(query) ||
          customer.oldCardNumber.toLowerCase().contains(query) ||
          customer.area.toLowerCase().contains(query) ||
          customer.address.toLowerCase().contains(query) ||
          customer.roModel.toLowerCase().contains(query) ||
          customer.engineerName.toLowerCase().contains(query);

      return matchesAssignment && matchesSearch;
    }).toList();
  }

  // ============================================================
  // INIT
  // ============================================================

  @override
  void initState() {
    super.initState();

    _loadRole();

    _loadCustomers();
  }

  // ============================================================
  // DISPOSE
  // ============================================================

  @override
  void dispose() {
    _searchController.dispose();

    super.dispose();
  }

  // ============================================================
  // LOAD ROLE
  // ============================================================

  Future<void> _loadRole() async {
    try {
      final role = await ApiService.getRole();

      if (!mounted) {
        return;
      }

      setState(() {
        _role = role?.trim().toUpperCase() ?? "";
      });
    } catch (e) {
      debugPrint("CUSTOMER LIST ROLE ERROR: $e");
    }
  }

  // ============================================================
  // LOAD CUSTOMERS
  // ============================================================

  Future<void> _loadCustomers() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
      });
    }

    try {
      final customers = await service.getCustomers();

      if (!mounted) {
        return;
      }

      setState(() {
        _customers = customers;

        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _customers = [];

        _isLoading = false;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Failed to load customers: $e")));
    }
  }

  // ============================================================
  // OPEN CUSTOMER DETAILS
  // ============================================================

  void _openCustomerDetails(CustomerModel customer) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CustomerDetailsScreen(customer: customer),
      ),
    );
  }


  void _showCustomerQr(CustomerModel customer) {
    final payload = "ARI-SMART-RO:CUSTOMER:${customer.customerId}";
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(customer.customerName),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            QrImageView(data: payload, size: 220),
            const SizedBox(height: 12),
            Text(customer.customerId, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Scan this QR to identify the customer.'),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  }

  Future<void> _openBulkImport() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const CustomerBulkImportScreen()),
    );
    if (changed == true) await _loadCustomers();
  }

  Future<void> _openSingleCustomer() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const WalkInCustomerScreen()),
    );
    if (changed == true) await _loadCustomers();
  }

  // ============================================================
  // ASSIGN / REASSIGN CUSTOMER
  // ============================================================

  Future<void> showEngineerDialog(CustomerModel customer) async {
    try {
      final engineers = await engineerService.getEngineers();

      if (!mounted) {
        return;
      }

      final messenger = ScaffoldMessenger.of(context);

      showDialog<void>(
        context: context,
        builder: (dialogContext) => _EngineerPickerDialog(
          engineers: engineers,
          onSelected: (engineer) async {
            Navigator.pop(dialogContext);

            final bool success = await service.assignCustomer(
              customerId: customer.id,
              employeeId: engineer.id,
            );

            if (!mounted) return;

            if (success) {
              messenger.showSnackBar(
                SnackBar(content: Text("${engineer.name} Assigned Successfully")),
              );
              await _loadCustomers();
            } else {
              messenger.showSnackBar(
                const SnackBar(content: Text("Assignment Failed")),
              );
            }
          },
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  // ============================================================
  // SEARCH BOX
  // ============================================================

  Widget _buildSearchBox() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,

      children: [
        TextField(
          controller: _searchController,

          onChanged: (value) {
            setState(() {
              _searchQuery = value;
            });
          },

          textInputAction: TextInputAction.search,

          decoration: InputDecoration(
            hintText: "Search name, ID, phone, card or old card...",

            prefixIcon: const Icon(Icons.search),

            suffixIcon: _searchQuery.isEmpty
                ? null
                : IconButton(
                    tooltip: "Clear search",

                    icon: const Icon(Icons.clear),

                    onPressed: () {
                      _searchController.clear();

                      setState(() {
                        _searchQuery = "";
                      });
                    },
                  ),

            filled: true,

            fillColor: Theme.of(context).colorScheme.surface,

            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),

        const SizedBox(height: 8),

        Wrap(
          spacing: 8,
          children: _AssignmentFilter.values.map((filter) {
            return ChoiceChip(
              label: Text(filter.label),
              selected: _assignmentFilter == filter,
              onSelected: (_) => setState(() => _assignmentFilter = filter),
            );
          }).toList(),
        ),

        const SizedBox(height: 8),

        Row(
          children: [
            const Icon(Icons.people_alt_outlined, size: 18),

            const SizedBox(width: 6),

            Text(
              _searchQuery.trim().isEmpty &&
                      _assignmentFilter == _AssignmentFilter.all
                  ? "${_customers.length} customers"
                  : "${_filteredCustomers.length} customers found",

              style: TextStyle(
                color: Colors.grey.shade700,

                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ============================================================
  // CUSTOMER CARD
  // ============================================================

  Widget _buildCustomerCard(CustomerModel customer, int index) {
    return Card(
      elevation: 3,

      margin: const EdgeInsets.only(bottom: 12),

      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),

      child: InkWell(
        borderRadius: BorderRadius.circular(12),

        // ======================================================
        // CARD TAP
        // ======================================================
        onTap: _role == "OFFICE"
            ? null
            : () {
                _openCustomerDetails(customer);
              },

        child: Padding(
          padding: const EdgeInsets.all(12),

          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,

            children: [
              // ==================================================
              // CUSTOMER HEADER
              // ==================================================
              Row(
                children: [
                  CircleAvatar(child: Text("${index + 1}")),

                  const SizedBox(width: 12),

                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,

                      children: [
                        Text(
                          customer.customerName,

                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),

                        Text(
                          customer.phone,

                          style: const TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  ),

                  // =================================================
                  // DETAILS INDICATOR
                  // =================================================
                  if (_role != "OFFICE")
                    const Icon(
                      Icons.arrow_forward_ios,
                      size: 16,
                      color: Colors.grey,
                    ),
                ],
              ),

              const Divider(height: 20),

              // ==================================================
              // CUSTOMER ID
              // ==================================================
              Text(
                "Customer ID : "
                "${customer.customerId}",
              ),

              const SizedBox(height: 5),

              // ==================================================
              // CURRENT CARD
              // ==================================================
              Text(
                "Card No : "
                "${customer.cardNumber}",
              ),

              // ==================================================
              // OLD CARD
              // ==================================================
              if (customer.oldCardNumber.trim().isNotEmpty) ...[
                const SizedBox(height: 5),

                Text(
                  "Old Card No : "
                  "${customer.oldCardNumber}",
                ),
              ],

              const SizedBox(height: 5),

              // ==================================================
              // AREA
              // ==================================================
              Text(
                "Area : "
                "${customer.area}",
              ),

              const SizedBox(height: 5),

              // ==================================================
              // ADDRESS
              // ==================================================
              Text(
                "Address : "
                "${customer.address}",
              ),

              const SizedBox(height: 5),

              // ==================================================
              // RO MODEL
              // ==================================================
              Text(
                "RO Model : "
                "${customer.roModel}",
              ),

              const SizedBox(height: 5),

              // ==================================================
              // MONTHLY RENT
              // ==================================================
              Text(
                "Monthly Rent : "
                "₹${customer.monthlyRent}",
              ),

              const SizedBox(height: 5),

              // ==================================================
              // INSTALLATION
              // ==================================================
              Text(
                "Installation : "
                "₹${customer.installationCharge}",
              ),

              const SizedBox(height: 8),

              // ==================================================
              // ASSIGNED ENGINEER
              // ==================================================
              if (customer.assignedEngineer != null)
                Text(
                  "Assigned Employee : "
                  "${customer.engineerName}",

                  style: const TextStyle(
                    color: Colors.green,

                    fontWeight: FontWeight.bold,
                  ),
                )
              else
                const Text(
                  "Assigned Employee : "
                  "Not Assigned",

                  style: TextStyle(
                    color: Colors.red,

                    fontWeight: FontWeight.bold,
                  ),
                ),

              // ==================================================
              // ASSIGN / REASSIGN
              // ENGINEER MUST NOT SEE THIS
              // ==================================================
              const SizedBox(height: 15),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.end,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _showCustomerQr(customer),
                    icon: const Icon(Icons.qr_code_2),
                    label: const Text("QR"),
                  ),
                  if (_role != "ENGINEER")
                    ElevatedButton.icon(
                      onPressed: () {
                        showEngineerDialog(customer);
                      },
                      icon: const Icon(Icons.person_add),
                      label: Text(
                        customer.assignedEngineer == null ? "Assign" : "Reassign",
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredCustomers;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Customer List"),

        centerTitle: true,

        actions: [
          if (_role == "ADMIN" || _role == "MANAGER")
            PopupMenuButton<String>(
              tooltip: "Add customers",
              onSelected: (value) {
                if (value == "single") {
                  _openSingleCustomer();
                } else if (value == "bulk") {
                  _openBulkImport();
                }
              },
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: "single",
                  child: ListTile(
                    leading: Icon(Icons.person_add_alt_1),
                    title: Text("Add Single Customer"),
                  ),
                ),
                PopupMenuItem(
                  value: "bulk",
                  child: ListTile(
                    leading: Icon(Icons.upload_file),
                    title: Text("Bulk Import Excel/CSV"),
                  ),
                ),
              ],
              icon: const Icon(Icons.person_add),
            ),
          IconButton(
            tooltip: "Refresh",
            onPressed: _loadCustomers,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),

      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadCustomers,

              child: ListView(
                padding: const EdgeInsets.all(10),

                children: [
                  // ==========================================
                  // SEARCH
                  // ==========================================
                  _buildSearchBox(),

                  const SizedBox(height: 12),

                  // ==========================================
                  // NO CUSTOMERS
                  // ==========================================
                  if (_customers.isEmpty)
                    const Padding(
                      padding: EdgeInsets.only(top: 80),

                      child: Center(child: Text("No Customers Found")),
                    )
                  // ==========================================
                  // NO SEARCH RESULT
                  // ==========================================
                  else if (filtered.isEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 80),

                      child: Column(
                        children: [
                          Icon(
                            Icons.person_search,
                            size: 60,
                            color: Colors.grey.shade500,
                          ),

                          const SizedBox(height: 12),

                          const Text(
                            "No matching customer found",

                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w600,
                            ),
                          ),

                          const SizedBox(height: 6),

                          Text(
                            "Try name, Customer ID, phone, current card or old card number.",

                            textAlign: TextAlign.center,

                            style: TextStyle(color: Colors.grey.shade600),
                          ),
                        ],
                      ),
                    )
                  // ==========================================
                  // CUSTOMER CARDS
                  // ==========================================
                  else
                    ...List.generate(
                      filtered.length,
                      (index) => _buildCustomerCard(filtered[index], index),
                    ),
                ],
              ),
            ),
    );
  }
}

enum _AssignmentFilter {
  all("All"),
  unassigned("Unassigned"),
  assigned("Assigned");

  const _AssignmentFilter(this.label);
  final String label;
}

class _EngineerPickerDialog extends StatefulWidget {
  const _EngineerPickerDialog({
    required this.engineers,
    required this.onSelected,
  });

  final List<EngineerModel> engineers;
  final ValueChanged<EngineerModel> onSelected;

  @override
  State<_EngineerPickerDialog> createState() => _EngineerPickerDialogState();
}

class _EngineerPickerDialogState extends State<_EngineerPickerDialog> {
  final TextEditingController _controller = TextEditingController();
  String _query = "";

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final query = _query.trim().toLowerCase();
    final filtered = widget.engineers.where((engineer) {
      return query.isEmpty ||
          engineer.name.toLowerCase().contains(query) ||
          engineer.phone.toLowerCase().contains(query) ||
          engineer.employeeId.toLowerCase().contains(query);
    }).toList();

    return AlertDialog(
      title: const Text("Assign Engineer"),
      content: SizedBox(
        width: double.maxFinite,
        height: 430,
        child: Column(
          children: [
            TextField(
              controller: _controller,
              autofocus: true,
              onChanged: (value) => setState(() => _query = value),
              decoration: InputDecoration(
                hintText: "Search name, ID or phone...",
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _query.isEmpty
                    ? null
                    : IconButton(
                        tooltip: "Clear search",
                        onPressed: () {
                          _controller.clear();
                          setState(() => _query = "");
                        },
                        icon: const Icon(Icons.clear),
                      ),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: filtered.isEmpty
                  ? const Center(child: Text("No matching employee found"))
                  : ListView.builder(
                      itemCount: filtered.length,
                      itemBuilder: (context, index) {
                        final engineer = filtered[index];
                        return ListTile(
                          leading: const Icon(Icons.engineering),
                          title: Text(engineer.name),
                          subtitle: Text(
                            [engineer.employeeId, engineer.phone]
                                .where((value) => value.trim().isNotEmpty)
                                .join(" • "),
                          ),
                          onTap: () => widget.onSelected(engineer),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text("Cancel"),
        ),
      ],
    );
  }
}
