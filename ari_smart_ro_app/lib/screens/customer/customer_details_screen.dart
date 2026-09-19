import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../models/customer_model.dart';
import '../../services/api_service.dart';
import '../../services/customer_service.dart';

class CustomerDetailsScreen extends StatefulWidget {
  final CustomerModel customer;

  const CustomerDetailsScreen({super.key, required this.customer});

  @override
  State<CustomerDetailsScreen> createState() => _CustomerDetailsScreenState();
}

class _CustomerDetailsScreenState extends State<CustomerDetailsScreen> {
  final CustomerService _customerService = CustomerService();

  late CustomerModel _customer;
  String _role = "";
  bool _savingCustomer = false;
  bool _loadingHistory = true;
  String? _historyError;

  List<dynamic> _serviceHistory = [];

  @override
  void initState() {
    super.initState();
    _customer = widget.customer;
    _loadRole();
    _loadServiceHistory();
  }

  Future<void> _loadRole() async {
    final role = await ApiService.getRole();
    if (!mounted) return;
    setState(() => _role = role?.trim().toUpperCase() ?? "");
  }

  bool get _canManageCustomer => _role == "ADMIN" || _role == "MANAGER";

  Future<void> _refreshCustomer() async {
    try {
      final customer = await _customerService.getCustomer(_customer.id);
      if (!mounted) return;
      setState(() => _customer = customer);
    } catch (_) {}
  }

  // ============================================================
  // LOAD SERVICE HISTORY
  // ============================================================

  Future<void> _loadServiceHistory() async {
    try {
      setState(() {
        _loadingHistory = true;
        _historyError = null;
      });

      final token = await ApiService.getAccessToken();

      final response = await http.get(
        Uri.parse(
          "${ApiService.baseUrl}/customers/"
          "${widget.customer.id}/service-history/",
        ),
        headers: {
          "Authorization": "Bearer $token",
          "Content-Type": "application/json",
        },
      );

      print("========== CUSTOMER SERVICE HISTORY ==========");
      print("STATUS : ${response.statusCode}");
      print("BODY   : ${response.body}");

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);

        if (decoded is Map<String, dynamic>) {
          final history = decoded["history"];

          setState(() {
            _serviceHistory = history is List ? history : [];
            _loadingHistory = false;
          });
        } else if (decoded is List) {
          setState(() {
            _serviceHistory = decoded;
            _loadingHistory = false;
          });
        } else {
          setState(() {
            _serviceHistory = [];
            _loadingHistory = false;
          });
        }

        return;
      }

      setState(() {
        _loadingHistory = false;
        _historyError = "Unable to load service history.";
      });
    } catch (e) {
      print("SERVICE HISTORY ERROR : $e");

      setState(() {
        _loadingHistory = false;
        _historyError = "Unable to load service history.";
      });
    }
  }

  Future<void> _editCustomer() async {
    if (!_canManageCustomer || _savingCustomer) return;

    final name = TextEditingController(text: _customer.customerName);
    final phone = TextEditingController(text: _customer.phone);
    final alternatePhone = TextEditingController(text: _customer.alternatePhone);
    final email = TextEditingController(text: _customer.email);
    final address = TextEditingController(text: _customer.address);
    final area = TextEditingController(text: _customer.area);
    final city = TextEditingController(text: _customer.city);
    final state = TextEditingController(text: _customer.state);
    final pincode = TextEditingController(text: _customer.pincode);
    final oldCard = TextEditingController(text: _customer.oldCardNumber);
    final roModel = TextEditingController(text: _customer.roModel);
    final monthlyRent = TextEditingController(text: _customer.monthlyRent);
    final installationCharge = TextEditingController(
      text: _customer.installationCharge,
    );
    final securityDeposit = TextEditingController(
      text: _customer.securityDeposit,
    );
    final installationDate = TextEditingController(
      text: _customer.installationDate,
    );
    String gender = _customer.gender;

    final values = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocalState) => AlertDialog(
          title: const Text("Edit Customer Details"),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: name,
                    decoration: const InputDecoration(labelText: "Customer Name"),
                  ),
                  TextField(
                    controller: phone,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: "Phone"),
                  ),
                  TextField(
                    controller: alternatePhone,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: "Alternate Phone"),
                  ),
                  TextField(
                    controller: email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: "Email"),
                  ),
                  DropdownButtonFormField<String>(
                    value: {"MALE", "FEMALE", "OTHER"}.contains(gender)
                        ? gender
                        : null,
                    decoration: const InputDecoration(labelText: "Gender"),
                    items: const [
                      DropdownMenuItem(value: "MALE", child: Text("Male")),
                      DropdownMenuItem(value: "FEMALE", child: Text("Female")),
                      DropdownMenuItem(value: "OTHER", child: Text("Other")),
                    ],
                    onChanged: (value) {
                      setLocalState(() => gender = value ?? "");
                    },
                  ),
                  TextField(
                    controller: oldCard,
                    decoration: const InputDecoration(labelText: "Old Card Number"),
                  ),
                  TextField(
                    controller: address,
                    maxLines: 2,
                    decoration: const InputDecoration(labelText: "Address"),
                  ),
                  TextField(
                    controller: area,
                    decoration: const InputDecoration(labelText: "Area"),
                  ),
                  TextField(
                    controller: city,
                    decoration: const InputDecoration(labelText: "City"),
                  ),
                  TextField(
                    controller: state,
                    decoration: const InputDecoration(labelText: "State"),
                  ),
                  TextField(
                    controller: pincode,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: "Pincode"),
                  ),
                  TextField(
                    controller: roModel,
                    decoration: const InputDecoration(labelText: "RO Model"),
                  ),
                  TextField(
                    controller: monthlyRent,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: "Monthly Rent"),
                  ),
                  TextField(
                    controller: installationCharge,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: "Installation Charge"),
                  ),
                  TextField(
                    controller: securityDeposit,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: "Security Deposit"),
                  ),
                  TextField(
                    controller: installationDate,
                    decoration: const InputDecoration(
                      labelText: "Installation Date",
                      hintText: "YYYY-MM-DD",
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    "Customer ID and Current ARI Card Number are system-generated and cannot be edited here.",
                    style: TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text("CANCEL"),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext, {
                  "name": name.text.trim(),
                  "phone": phone.text.trim(),
                  "alternate_phone": alternatePhone.text.trim(),
                  "email": email.text.trim(),
                  "gender": gender,
                  "old_card_number": oldCard.text.trim(),
                  "address": address.text.trim(),
                  "area": area.text.trim(),
                  "city": city.text.trim(),
                  "state": state.text.trim(),
                  "pincode": pincode.text.trim(),
                  "ro_model": roModel.text.trim(),
                  "monthly_rent": monthlyRent.text.trim(),
                  "installation_charge": installationCharge.text.trim(),
                  "security_deposit": securityDeposit.text.trim(),
                  "installation_date": installationDate.text.trim().isEmpty
                      ? null
                      : installationDate.text.trim(),
                });
              },
              child: const Text("SAVE"),
            ),
          ],
        ),
      ),
    );

    name.dispose();
    phone.dispose();
    alternatePhone.dispose();
    email.dispose();
    address.dispose();
    area.dispose();
    city.dispose();
    state.dispose();
    pincode.dispose();
    oldCard.dispose();
    roModel.dispose();
    monthlyRent.dispose();
    installationCharge.dispose();
    securityDeposit.dispose();
    installationDate.dispose();

    if (values == null || !mounted) return;

    setState(() => _savingCustomer = true);
    try {
      final updated = await _customerService.updateCustomer(
        customerId: _customer.id,
        values: values,
      );
      if (!mounted) return;
      setState(() => _customer = updated);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Customer details updated.")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => _savingCustomer = false);
    }
  }

  Future<void> _changeCustomerStatus(bool active) async {
    if (!_canManageCustomer || _savingCustomer) return;

    final reason = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(active ? "Activate Customer?" : "Deactivate Customer?"),
        content: active
            ? Text("${_customer.customerName} will become active again.")
            : TextField(
                controller: reason,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: "Deactivation Reason",
                  hintText: "Optional",
                ),
              ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text("CANCEL"),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(active ? "ACTIVATE" : "DEACTIVATE"),
          ),
        ],
      ),
    ) ?? false;

    if (!confirmed) {
      reason.dispose();
      return;
    }

    setState(() => _savingCustomer = true);
    try {
      await _customerService.customerLifecycle(
        customerId: _customer.id,
        action: active ? "reactivate" : "deactivate",
        reason: reason.text.trim(),
      );
      await _refreshCustomer();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            active ? "Customer activated." : "Customer deactivated.",
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      reason.dispose();
      if (mounted) setState(() => _savingCustomer = false);
    }
  }

  // ============================================================
  // DETAIL ROW
  // ============================================================

  Widget _detailRow({
    required IconData icon,
    required String title,
    required String value,
  }) {
    final displayValue = value.trim().isEmpty ? "Not Available" : value;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.grey.shade100,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 22, color: Colors.blue),

          const SizedBox(width: 12),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade600,
                    fontWeight: FontWeight.w600,
                  ),
                ),

                const SizedBox(height: 3),

                Text(
                  displayValue,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // SECTION TITLE
  // ============================================================

  Widget _sectionTitle(String title, IconData icon) {
    return Padding(
      padding: const EdgeInsets.only(top: 8, bottom: 10),
      child: Row(
        children: [
          Icon(icon, color: Colors.blue),

          const SizedBox(width: 8),

          Text(
            title,
            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // SAFE STRING
  // ============================================================

  String _stringValue(dynamic value) {
    if (value == null) {
      return "";
    }

    return value.toString();
  }

  // ============================================================
  // SERVICE HISTORY CARD
  // ============================================================

  Widget _buildServiceHistoryCard(Map<String, dynamic> job) {
    final jobId = _stringValue(job["job_id"]);

    final jobType = _stringValue(job["job_type"]);

    final status = _stringValue(job["status"]);

    final engineerName = _stringValue(job["engineer_name"]);

    final scheduledDate = _stringValue(job["scheduled_date"]);

    final completedAt = _stringValue(job["completed_at"]);

    final parts = job["parts_used"] is List
        ? job["parts_used"] as List
        : <dynamic>[];

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ==================================================
            // JOB HEADER
            // ==================================================
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.build_circle_outlined,
                    color: Colors.blue,
                    size: 28,
                  ),
                ),

                const SizedBox(width: 12),

                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        jobId.isEmpty ? "Service Job" : jobId,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 4),

                      Text(
                        jobType.isEmpty ? "Service" : jobType,
                        style: TextStyle(color: Colors.grey.shade700),
                      ),
                    ],
                  ),
                ),

                _statusChip(status),
              ],
            ),

            const SizedBox(height: 14),

            // ==================================================
            // ENGINEER
            // ==================================================
            if (engineerName.isNotEmpty)
              _historyInfoRow(
                Icons.engineering_outlined,
                "Engineer",
                engineerName,
              ),

            if (scheduledDate.isNotEmpty)
              _historyInfoRow(
                Icons.event_outlined,
                "Scheduled",
                _formatDate(scheduledDate),
              ),

            if (completedAt.isNotEmpty)
              _historyInfoRow(
                Icons.check_circle_outline,
                "Completed",
                _formatDate(completedAt),
              ),

            // ==================================================
            // PARTS
            // ==================================================
            const SizedBox(height: 8),

            Row(
              children: [
                const Icon(
                  Icons.inventory_2_outlined,
                  size: 20,
                  color: Colors.blue,
                ),

                const SizedBox(width: 7),

                Text(
                  "Parts Used",
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            if (parts.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  "No parts recorded.",
                  style: TextStyle(color: Colors.grey.shade700),
                ),
              )
            else
              ...parts.map(
                (part) => _buildPartCard(
                  part is Map<String, dynamic>
                      ? part
                      : Map<String, dynamic>.from(part as Map),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // STATUS CHIP
  // ============================================================

  Widget _statusChip(String status) {
    String displayStatus;

    switch (status) {
      case "ASSIGNED":
        displayStatus = "Assigned";
        break;

      case "ACCEPTED":
        displayStatus = "Accepted";
        break;

      case "ON_THE_WAY":
        displayStatus = "On The Way";
        break;

      case "ARRIVED":
        displayStatus = "Arrived";
        break;

      case "IN_PROGRESS":
        displayStatus = "In Progress";
        break;

      case "COMPLETED":
        displayStatus = "Completed";
        break;

      case "CANCELLED":
        displayStatus = "Cancelled";
        break;

      default:
        displayStatus = status.isEmpty ? "Unknown" : status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _statusColor(status),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        displayStatus,
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: Colors.white,
        ),
      ),
    );
  }

  // ============================================================
  // STATUS COLOR
  // ============================================================

  Color _statusColor(String status) {
    switch (status) {
      case "COMPLETED":
        return Colors.green;

      case "IN_PROGRESS":
        return Colors.orange;

      case "CANCELLED":
        return Colors.red;

      case "ACCEPTED":
      case "ARRIVED":
        return Colors.blue;

      default:
        return Colors.grey;
    }
  }

  // ============================================================
  // HISTORY INFO ROW
  // ============================================================

  Widget _historyInfoRow(IconData icon, String title, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: Colors.grey.shade700),

          const SizedBox(width: 8),

          Text("$title: ", style: const TextStyle(fontWeight: FontWeight.w600)),

          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  // ============================================================
  // PART CARD
  // ============================================================

  Widget _buildPartCard(Map<String, dynamic> part) {
    final partName = _stringValue(part["part_name"]);

    final partCode = _stringValue(part["part_code"]);

    final serialNumber = _stringValue(part["serial_number"]);

    final barcode = _stringValue(part["barcode"]);

    final quantity = _stringValue(part["quantity"]);

    final usedAt = _stringValue(part["used_at"]);

    final remarks = _stringValue(part["remarks"]);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // PART NAME
          Text(
            partName.isEmpty ? "Unknown Part" : partName,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 8),

          if (partCode.isNotEmpty) _partInfo("Part Code", partCode),

          if (serialNumber.isNotEmpty) _partInfo("Serial Number", serialNumber),

          if (barcode.isNotEmpty) _partInfo("Barcode", barcode),

          _partInfo("Quantity", quantity.isEmpty ? "1" : quantity),

          if (usedAt.isNotEmpty) _partInfo("Used On", _formatDate(usedAt)),

          if (remarks.isNotEmpty) _partInfo("Remarks", remarks),
        ],
      ),
    );
  }

  // ============================================================
  // PART INFO
  // ============================================================

  Widget _partInfo(String title, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 105,
            child: Text(
              title,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),

          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // DATE FORMAT
  // ============================================================

  String _formatDate(String value) {
    try {
      final date = DateTime.parse(value).toLocal();

      final day = date.day.toString().padLeft(2, "0");

      final month = date.month.toString().padLeft(2, "0");

      final year = date.year.toString();

      final hour = date.hour.toString().padLeft(2, "0");

      final minute = date.minute.toString().padLeft(2, "0");

      return "$day-$month-$year $hour:$minute";
    } catch (_) {
      return value;
    }
  }

  // ============================================================
  // SERVICE HISTORY SECTION
  // ============================================================

  Widget _buildServiceHistorySection() {
    if (_loadingHistory) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionTitle("Service & Parts History", Icons.history),

          const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ),
          ),
        ],
      );
    }

    if (_historyError != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionTitle("Service & Parts History", Icons.history),

          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.red.shade50,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                const Icon(Icons.error_outline, color: Colors.red, size: 30),

                const SizedBox(height: 8),

                Text(
                  _historyError!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.red),
                ),

                const SizedBox(height: 10),

                OutlinedButton.icon(
                  onPressed: _loadServiceHistory,
                  icon: const Icon(Icons.refresh),
                  label: const Text("Retry"),
                ),
              ],
            ),
          ),
        ],
      );
    }

    if (_serviceHistory.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionTitle("Service & Parts History", Icons.history),

          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                Icon(Icons.history, size: 38, color: Colors.grey.shade500),

                const SizedBox(height: 8),

                Text(
                  "No service history found.",
                  style: TextStyle(
                    color: Colors.grey.shade700,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle("Service & Parts History", Icons.history),

        ..._serviceHistory.map((item) {
          if (item is Map<String, dynamic>) {
            return _buildServiceHistoryCard(item);
          }

          return const SizedBox.shrink();
        }),
      ],
    );
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final customer = _customer;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Customer Details"),
        centerTitle: true,

        actions: [
          IconButton(
            tooltip: "Refresh",
            onPressed: () async {
              await _refreshCustomer();
              await _loadServiceHistory();
            },
            icon: const Icon(Icons.refresh),
          ),
          if (_canManageCustomer)
            PopupMenuButton<String>(
              tooltip: "Customer actions",
              onSelected: (value) {
                if (value == "edit") {
                  _editCustomer();
                } else if (value == "activate") {
                  _changeCustomerStatus(true);
                } else if (value == "deactivate") {
                  _changeCustomerStatus(false);
                }
              },
              itemBuilder: (_) => [
                const PopupMenuItem(
                  value: "edit",
                  child: ListTile(
                    leading: Icon(Icons.edit_outlined),
                    title: Text("Edit Customer Details"),
                  ),
                ),
                if (customer.isActive)
                  const PopupMenuItem(
                    value: "deactivate",
                    child: ListTile(
                      leading: Icon(Icons.person_off_outlined),
                      title: Text("Deactivate Customer"),
                    ),
                  )
                else
                  const PopupMenuItem(
                    value: "activate",
                    child: ListTile(
                      leading: Icon(Icons.person_add_alt_1),
                      title: Text("Activate Customer"),
                    ),
                  ),
              ],
            ),
        ],
      ),

      body: SingleChildScrollView(
        padding: const EdgeInsets.all(14),

        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,

          children: [
            // ====================================================
            // CUSTOMER HEADER
            // ====================================================
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),

              child: Padding(
                padding: const EdgeInsets.all(18),

                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 32,

                      child: Text(
                        customer.customerName.trim().isNotEmpty
                            ? customer.customerName
                                  .trim()
                                  .substring(0, 1)
                                  .toUpperCase()
                            : "?",

                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),

                    const SizedBox(width: 14),

                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,

                        children: [
                          Text(
                            customer.customerName.trim().isEmpty
                                ? "Customer"
                                : customer.customerName,

                            style: const TextStyle(
                              fontSize: 21,
                              fontWeight: FontWeight.bold,
                            ),
                          ),

                          const SizedBox(height: 5),

                          Text(
                            customer.phone,
                            style: TextStyle(
                              fontSize: 15,
                              color: Colors.grey.shade700,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Chip(
                            visualDensity: VisualDensity.compact,
                            label: Text(
                              customer.isActive ? "ACTIVE" : "INACTIVE",
                            ),
                            avatar: Icon(
                              customer.isActive
                                  ? Icons.check_circle
                                  : Icons.person_off,
                              size: 18,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 12),

            // ====================================================
            // CUSTOMER INFORMATION
            // ====================================================
            _sectionTitle("Customer Information", Icons.person_outline),

            _detailRow(
              icon: Icons.badge_outlined,
              title: "Customer ID",
              value: customer.customerId,
            ),

            _detailRow(
              icon: Icons.phone_outlined,
              title: "Phone",
              value: customer.phone,
            ),

            _detailRow(
              icon: Icons.location_on_outlined,
              title: "Area",
              value: customer.area,
            ),

            _detailRow(
              icon: Icons.home_outlined,
              title: "Address",
              value: customer.address,
            ),

            // ====================================================
            // CARD INFORMATION
            // ====================================================
            _sectionTitle("Card Information", Icons.credit_card),

            _detailRow(
              icon: Icons.credit_card,
              title: "Current Card Number",
              value: customer.cardNumber,
            ),

            if (customer.oldCardNumber.trim().isNotEmpty)
              _detailRow(
                icon: Icons.history,
                title: "Old Card Number",
                value: customer.oldCardNumber,
              ),

            // ====================================================
            // RO INFORMATION
            // ====================================================
            _sectionTitle("RO Information", Icons.water_drop_outlined),

            _detailRow(
              icon: Icons.water_drop,
              title: "RO Model",
              value: customer.roModel,
            ),

            _detailRow(
              icon: Icons.payments_outlined,
              title: "Monthly Rent",
              value: customer.monthlyRent.isEmpty
                  ? ""
                  : "₹${customer.monthlyRent}",
            ),

            _detailRow(
              icon: Icons.receipt_long_outlined,
              title: "Installation Charge",
              value: customer.installationCharge.isEmpty
                  ? ""
                  : "₹${customer.installationCharge}",
            ),

            // ====================================================
            // ASSIGNMENT
            // ====================================================
            _sectionTitle("Assignment", Icons.engineering_outlined),

            _detailRow(
              icon: Icons.engineering,
              title: "Assigned Employee",
              value: customer.engineerName.isEmpty
                  ? "Not Assigned"
                  : customer.engineerName,
            ),

            // ====================================================
            // SERVICE & PARTS HISTORY
            // ====================================================
            _buildServiceHistorySection(),

            // ====================================================
            // LOCATION
            // ====================================================
            _sectionTitle("Location", Icons.location_on_outlined),

            _detailRow(
              icon: Icons.my_location,
              title: "Latitude",
              value: customer.latitude.toString(),
            ),

            _detailRow(
              icon: Icons.explore,
              title: "Longitude",
              value: customer.longitude.toString(),
            ),

            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
