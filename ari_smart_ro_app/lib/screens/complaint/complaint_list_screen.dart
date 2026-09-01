import 'package:flutter/material.dart';

import '../../models/complaint_model.dart';
import '../../services/api_service.dart';
import '../../services/complaint_service.dart';
import 'new_complaint_screen.dart';
import 'complaint_details_screen.dart';

class ComplaintListScreen extends StatefulWidget {
  const ComplaintListScreen({super.key});

  @override
  State<ComplaintListScreen> createState() => _ComplaintListScreenState();
}

class _ComplaintListScreenState extends State<ComplaintListScreen> {
  // ============================================================
  // SERVICE
  // ============================================================

  final ComplaintService _complaintService = ComplaintService();

  // ============================================================
  // SEARCH
  // ============================================================

  final TextEditingController _searchController = TextEditingController();

  // ============================================================
  // DATA
  // ============================================================

  List<ComplaintModel> _complaints = [];

  bool _isLoading = true;

  bool _actionLoading = false;

  String? _errorMessage;

  String _searchQuery = "";

  String? _role;

  // ============================================================
  // INIT
  // ============================================================

  @override
  void initState() {
    super.initState();

    _loadRole();

    _loadComplaints();
  }

  // ============================================================
  // LOAD ROLE
  // ============================================================

  Future<void> _loadRole() async {
    final role = await ApiService.getRole();

    if (!mounted) return;

    setState(() {
      _role = role?.toUpperCase();
    });
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
  // LOAD COMPLAINTS
  // ============================================================

  Future<void> _loadComplaints() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final complaints = await _complaintService.getComplaints();

      if (!mounted) return;

      setState(() {
        _complaints = complaints;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isLoading = false;

        _errorMessage = e.toString().replaceFirst("Exception: ", "");
      });
    }
  }

  // ============================================================
  // NEW COMPLAINT
  // ============================================================

  Future<void> _openNewComplaint() async {
    final created = await Navigator.push(
      context,

      MaterialPageRoute(builder: (_) => const NewComplaintScreen()),
    );

    if (!mounted) return;

    if (created == true) {
      await _loadComplaints();
    }
  }

  // ============================================================
  // SEARCH FILTER
  // ============================================================

  List<ComplaintModel> get _filteredComplaints {
    final query = _searchQuery.trim().toLowerCase();

    if (query.isEmpty) {
      return _complaints;
    }

    return _complaints.where((complaint) {
      return complaint.complaintId.toLowerCase().contains(query) ||
          complaint.customerName.toLowerCase().contains(query) ||
          complaint.customerIdDisplay.toLowerCase().contains(query) ||
          complaint.customerPhone.toLowerCase().contains(query) ||
          complaint.currentCardNumber.toLowerCase().contains(query) ||
          complaint.oldCardNumber.toLowerCase().contains(query) ||
          complaint.engineerName.toLowerCase().contains(query) ||
          complaint.engineerIdDisplay.toLowerCase().contains(query) ||
          complaint.displayComplaintType.toLowerCase().contains(query) ||
          complaint.displayStatus.toLowerCase().contains(query);
    }).toList();
  }

  // ============================================================
  // CAN PERFORM WORKFLOW ACTIONS
  // ============================================================

  bool get _canManageComplaint {
    if (_role == null) {
      return false;
    }

    return _role == "ENGINEER" ||
        _role == "ADMIN" ||
        _role == "MANAGER" ||
        _role == "OFFICE";
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final complaints = _filteredComplaints;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Complaints",
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        actions: [
          IconButton(
            tooltip: "Refresh",
            onPressed: _isLoading ? null : _loadComplaints,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),

      // ========================================================
      // NEW COMPLAINT
      // ========================================================
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _isLoading ? null : _openNewComplaint,
        icon: const Icon(Icons.add),
        label: const Text("New Complaint"),
      ),

      // ========================================================
      // BODY
      // ========================================================
      body: RefreshIndicator(
        onRefresh: _loadComplaints,

        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
            ? _buildErrorState()
            : complaints.isEmpty
            ? _buildEmptyState()
            : ListView(
                physics: const AlwaysScrollableScrollPhysics(),

                padding: const EdgeInsets.all(12),

                children: [
                  _buildSearchBox(),

                  const SizedBox(height: 12),

                  _buildSummary(complaints.length),

                  const SizedBox(height: 12),

                  ...complaints.map(_buildComplaintCard),

                  const SizedBox(height: 80),
                ],
              ),
      ),
    );
  }

  // ============================================================
  // SEARCH BOX
  // ============================================================

  Widget _buildSearchBox() {
    return TextField(
      controller: _searchController,

      onChanged: (value) {
        setState(() {
          _searchQuery = value;
        });
      },

      textInputAction: TextInputAction.search,

      decoration: InputDecoration(
        hintText: "Search complaint, customer, phone, card...",

        prefixIcon: const Icon(Icons.search),

        suffixIcon: _searchQuery.isEmpty
            ? null
            : IconButton(
                tooltip: "Clear",
                icon: const Icon(Icons.clear),
                onPressed: () {
                  _searchController.clear();

                  setState(() {
                    _searchQuery = "";
                  });
                },
              ),

        filled: true,

        fillColor: Colors.white,

        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),

        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),

        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Colors.blue),
        ),
      ),
    );
  }

  // ============================================================
  // SUMMARY
  // ============================================================

  Widget _buildSummary(int count) {
    final pending = _complaints
        .where(
          (item) =>
              item.status == "NEW" ||
              item.status == "ASSIGNED" ||
              item.status == "IN_PROGRESS",
        )
        .length;

    final resolved = _complaints
        .where((item) => item.status == "RESOLVED" || item.status == "CLOSED")
        .length;

    return Row(
      children: [
        Expanded(
          child: _summaryCard(
            icon: Icons.support_agent,
            title: "Complaints",
            value: count.toString(),
          ),
        ),

        const SizedBox(width: 8),

        Expanded(
          child: _summaryCard(
            icon: Icons.assignment_late_outlined,
            title: "Pending",
            value: pending.toString(),
          ),
        ),

        const SizedBox(width: 8),

        Expanded(
          child: _summaryCard(
            icon: Icons.check_circle_outline,
            title: "Resolved",
            value: resolved.toString(),
          ),
        ),
      ],
    );
  }

  // ============================================================
  // SUMMARY CARD
  // ============================================================

  Widget _summaryCard({
    required IconData icon,
    required String title,
    required String value,
  }) {
    return Card(
      elevation: 1,

      child: Padding(
        padding: const EdgeInsets.all(12),

        child: Row(
          children: [
            Icon(icon, size: 25, color: Colors.blue),

            const SizedBox(width: 8),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,

                children: [
                  Text(
                    title,
                    style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                  ),

                  const SizedBox(height: 2),

                  Text(
                    value,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // COMPLAINT CARD
  // ============================================================

  Widget _buildComplaintCard(ComplaintModel complaint) {
    return Card(
      elevation: 1,

      margin: const EdgeInsets.only(bottom: 12),

      child: InkWell(
        borderRadius: BorderRadius.circular(12),

        onTap: () async {
          final updated = await Navigator.push<bool>(
            context,
            MaterialPageRoute(
              builder: (_) => ComplaintDetailsScreen(complaintId: complaint.id),
            ),
          );

          if (!mounted) return;

          if (updated == true) {
            await _loadComplaints();
          }
        },

        child: Padding(
          padding: const EdgeInsets.all(14),

          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,

            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,

                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,

                      children: [
                        Text(
                          complaint.complaintId,

                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),

                        const SizedBox(height: 4),

                        Text(
                          complaint.displayComplaintType,

                          style: TextStyle(color: Colors.grey.shade700),
                        ),
                      ],
                    ),
                  ),

                  _priorityBadge(complaint.priority),

                  const SizedBox(width: 6),

                  _statusBadge(complaint.status),
                ],
              ),

              const Divider(height: 22),

              Row(
                crossAxisAlignment: CrossAxisAlignment.start,

                children: [
                  const Icon(Icons.person_outline, size: 20),

                  const SizedBox(width: 8),

                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,

                      children: [
                        Text(
                          complaint.displayCustomer,

                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),

                        const SizedBox(height: 3),

                        Text(
                          complaint.customerPhone,

                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 10),

              _infoRow("Customer ID", complaint.customerIdDisplay),

              _infoRow("Current Card", complaint.currentCardNumber),

              if (complaint.oldCardNumber.isNotEmpty)
                _infoRow("Old Card", complaint.oldCardNumber),

              const SizedBox(height: 8),

              Row(
                children: [
                  const Icon(Icons.engineering_outlined, size: 20),

                  const SizedBox(width: 8),

                  Expanded(
                    child: Text(
                      "Engineer: "
                      "${complaint.displayEngineer}",

                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),

              if (complaint.description.isNotEmpty) ...[
                const SizedBox(height: 10),

                Text(
                  complaint.description,

                  maxLines: 3,

                  overflow: TextOverflow.ellipsis,

                  style: TextStyle(color: Colors.grey.shade700),
                ),
              ],

              const SizedBox(height: 10),

              if (complaint.complaintDate != null)
                Text(
                  "Complaint: "
                  "${complaint.complaintDate}",

                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                ),

              if (complaint.scheduledDate?.isNotEmpty ?? false)
                Text(
                  "Scheduled: "
                  "${complaint.scheduledDate}",

                  style: TextStyle(fontSize: 12, color: Colors.orange.shade700),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // INFO ROW
  // ============================================================

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(top: 5),

      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          SizedBox(
            width: 105,

            child: Text(
              label,

              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ),

          Expanded(
            child: Text(
              value.isEmpty ? "-" : value,

              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // STATUS BADGE
  // ============================================================

  Widget _statusBadge(String status) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),

      decoration: BoxDecoration(
        color: _statusColor(status).withValues(alpha: 0.12),

        borderRadius: BorderRadius.circular(20),
      ),

      child: Text(
        _statusDisplayName(status),

        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: _statusColor(status),
        ),
      ),
    );
  }

  // ============================================================
  // STATUS COLOR
  // ============================================================

  Color _statusColor(String status) {
    switch (status) {
      case "NEW":
        return Colors.blue;

      case "ASSIGNED":
        return Colors.orange;

      case "IN_PROGRESS":
        return Colors.deepPurple;

      case "RESOLVED":
        return Colors.green;

      case "CLOSED":
        return Colors.teal;

      case "CANCELLED":
        return Colors.red;

      default:
        return Colors.grey;
    }
  }

  // ============================================================
  // STATUS DISPLAY
  // ============================================================

  String _statusDisplayName(String status) {
    switch (status) {
      case "NEW":
        return "New";

      case "ASSIGNED":
        return "Assigned";

      case "IN_PROGRESS":
        return "In Progress";

      case "RESOLVED":
        return "Resolved";

      case "CLOSED":
        return "Closed";

      case "CANCELLED":
        return "Cancelled";

      default:
        return status.isEmpty ? "-" : status.replaceAll("_", " ");
    }
  }

  // ============================================================
  // PRIORITY BADGE
  // ============================================================

  Widget _priorityBadge(String priority) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),

      decoration: BoxDecoration(
        color: _priorityColor(priority).withValues(alpha: 0.12),

        borderRadius: BorderRadius.circular(20),
      ),

      child: Text(
        _priorityDisplayName(priority),

        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: _priorityColor(priority),
        ),
      ),
    );
  }

  // ============================================================
  // PRIORITY COLOR
  // ============================================================

  Color _priorityColor(String priority) {
    switch (priority) {
      case "EMERGENCY":
        return Colors.red;

      case "URGENT":
        return Colors.deepOrange;

      case "NORMAL":
        return Colors.blue;

      case "LOW":
        return Colors.green;

      default:
        return Colors.grey;
    }
  }

  // ============================================================
  // PRIORITY DISPLAY
  // ============================================================

  String _priorityDisplayName(String priority) {
    switch (priority) {
      case "EMERGENCY":
        return "Emergency";

      case "URGENT":
        return "Urgent";

      case "NORMAL":
        return "Normal";

      case "LOW":
        return "Low";

      default:
        return priority.isEmpty ? "-" : priority;
    }
  }

  // ============================================================
  // EMPTY STATE
  // ============================================================

  Widget _buildEmptyState() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),

      padding: const EdgeInsets.all(24),

      children: [
        _buildSearchBox(),

        const SizedBox(height: 80),

        Icon(Icons.support_agent, size: 64, color: Colors.grey.shade400),

        const SizedBox(height: 14),

        const Center(
          child: Text(
            "No complaints found",
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          ),
        ),

        if (_searchQuery.trim().isNotEmpty) ...[
          const SizedBox(height: 8),

          Center(
            child: Text(
              "Try complaint ID, customer name, "
              "phone or card number.",

              textAlign: TextAlign.center,

              style: TextStyle(color: Colors.grey.shade600),
            ),
          ),
        ],
      ],
    );
  }

  // ============================================================
  // ERROR STATE
  // ============================================================

  Widget _buildErrorState() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),

      padding: const EdgeInsets.all(24),

      children: [
        const SizedBox(height: 100),

        Icon(Icons.error_outline, size: 60, color: Colors.red.shade400),

        const SizedBox(height: 12),

        const Center(
          child: Text(
            "Unable to load complaints",
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          ),
        ),

        const SizedBox(height: 8),

        Center(
          child: Text(
            _errorMessage ?? "",

            textAlign: TextAlign.center,

            style: TextStyle(color: Colors.grey.shade700),
          ),
        ),

        const SizedBox(height: 18),

        Center(
          child: ElevatedButton.icon(
            onPressed: _loadComplaints,

            icon: const Icon(Icons.refresh),

            label: const Text("Retry"),
          ),
        ),
      ],
    );
  }

  // ============================================================
  // COMPLAINT DETAILS
  // ============================================================

  void _showComplaintDetails(ComplaintModel complaint) {
    showModalBottomSheet(
      context: context,

      isScrollControlled: true,

      showDragHandle: true,

      builder: (sheetContext) {
        return SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),

            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,

              children: [
                // ==================================================
                // HEADER
                // ==================================================
                Text(
                  complaint.complaintId,

                  style: const TextStyle(
                    fontSize: 21,
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 8),

                Wrap(
                  spacing: 8,
                  runSpacing: 6,

                  children: [
                    _statusBadge(complaint.status),

                    _priorityBadge(complaint.priority),
                  ],
                ),

                const SizedBox(height: 20),

                // ==================================================
                // STATUS TIMELINE
                // ==================================================
                _buildStatusTimeline(complaint),

                const SizedBox(height: 20),

                // ==================================================
                // ACTIONS
                // ==================================================
                if (_canManageComplaint) _buildComplaintActions(complaint),

                if (_canManageComplaint) const SizedBox(height: 24),

                // ==================================================
                // CUSTOMER
                // ==================================================
                _detailSection("Customer", [
                  _detailItem("Name", complaint.customerName),

                  _detailItem("Customer ID", complaint.customerIdDisplay),

                  _detailItem("Phone", complaint.customerPhone),

                  _detailItem("Current Card", complaint.currentCardNumber),

                  if (complaint.oldCardNumber.isNotEmpty)
                    _detailItem("Old Card", complaint.oldCardNumber),
                ]),

                // ==================================================
                // COMPLAINT
                // ==================================================
                _detailSection("Complaint", [
                  _detailItem("Type", complaint.displayComplaintType),

                  _detailItem("Priority", complaint.displayPriority),

                  _detailItem("Status", complaint.displayStatus),

                  _detailItem("Description", complaint.description),

                  _detailItem("Complaint Date", complaint.complaintDate ?? "-"),

                  if (complaint.scheduledDate?.isNotEmpty ?? false)
                    _detailItem("Scheduled Date", complaint.scheduledDate!),
                ]),

                // ==================================================
                // ENGINEER
                // ==================================================
                _detailSection("Engineer", [
                  _detailItem("Name", complaint.displayEngineer),

                  _detailItem("Engineer ID", complaint.engineerIdDisplay),

                  _detailItem(
                    "Remarks",
                    complaint.engineerRemarks.isEmpty
                        ? "-"
                        : complaint.engineerRemarks,
                  ),
                ]),

                // ==================================================
                // RESOLUTION
                // ==================================================
                if (complaint.resolution.isNotEmpty)
                  _detailSection("Resolution", [
                    _detailItem("Resolution", complaint.resolution),

                    if (complaint.resolvedDate?.isNotEmpty ?? false)
                      _detailItem("Resolved Date", complaint.resolvedDate!),
                  ]),

                // ==================================================
                // LINKED SERVICE
                // ==================================================
                if (complaint.linkedServiceIdDisplay.isNotEmpty)
                  _detailSection("Linked Service", [
                    _detailItem("Service", complaint.linkedServiceIdDisplay),
                  ]),

                // ==================================================
                // LOCATION
                // ==================================================
                if (complaint.latitude != null || complaint.longitude != null)
                  _detailSection("Location", [
                    _detailItem(
                      "Latitude",
                      complaint.latitude?.toString() ?? "-",
                    ),

                    _detailItem(
                      "Longitude",
                      complaint.longitude?.toString() ?? "-",
                    ),
                  ]),

                // ==================================================
                // SYSTEM
                // ==================================================
                _detailSection("System", [
                  _detailItem("Created", complaint.createdAt ?? "-"),

                  _detailItem("Last Updated", complaint.updatedAt ?? "-"),
                ]),
              ],
            ),
          ),
        );
      },
    );
  }

  // ============================================================
  // COMPLAINT ACTIONS
  // ============================================================

  Widget _buildComplaintActions(ComplaintModel complaint) {
    // ----------------------------------------------------------
    // NEW
    // ----------------------------------------------------------
    // No action until engineer is assigned.
    // ----------------------------------------------------------

    if (complaint.status == "NEW") {
      return Container(
        width: double.infinity,

        padding: const EdgeInsets.all(14),

        decoration: BoxDecoration(
          color: Colors.blue.shade50,

          borderRadius: BorderRadius.circular(12),

          border: Border.all(color: Colors.blue.shade100),
        ),

        child: Row(
          children: [
            Icon(Icons.info_outline, color: Colors.blue.shade700),

            const SizedBox(width: 10),

            const Expanded(
              child: Text("Assign an engineer before starting this complaint."),
            ),
          ],
        ),
      );
    }

    // ----------------------------------------------------------
    // ASSIGNED
    // ----------------------------------------------------------

    if (complaint.status == "ASSIGNED") {
      return SizedBox(
        width: double.infinity,

        child: ElevatedButton.icon(
          onPressed: _actionLoading
              ? null
              : () {
                  _startComplaint(complaint);
                },

          icon: _actionLoading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.play_arrow),

          label: const Text("Start Work"),

          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
        ),
      );
    }

    // ----------------------------------------------------------
    // IN PROGRESS
    // ----------------------------------------------------------

    if (complaint.status == "IN_PROGRESS") {
      return SizedBox(
        width: double.infinity,

        child: ElevatedButton.icon(
          onPressed: _actionLoading
              ? null
              : () {
                  _showResolveDialog(complaint);
                },

          icon: const Icon(Icons.check_circle_outline),

          label: const Text("Resolve Complaint"),

          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.green,

            foregroundColor: Colors.white,

            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
        ),
      );
    }

    // ----------------------------------------------------------
    // RESOLVED
    // ----------------------------------------------------------

    if (complaint.status == "RESOLVED") {
      return SizedBox(
        width: double.infinity,

        child: ElevatedButton.icon(
          onPressed: _actionLoading
              ? null
              : () {
                  _confirmCloseComplaint(complaint);
                },

          icon: const Icon(Icons.lock_outline),

          label: const Text("Close Complaint"),

          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.teal,

            foregroundColor: Colors.white,

            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
        ),
      );
    }

    // ----------------------------------------------------------
    // CLOSED / CANCELLED
    // ----------------------------------------------------------

    return const SizedBox.shrink();
  }

  // ============================================================
  // START COMPLAINT
  // ============================================================

  Future<void> _startComplaint(ComplaintModel complaint) async {
    setState(() {
      _actionLoading = true;
    });

    try {
      await _complaintService.startComplaint(complaint.id);

      if (!mounted) return;

      Navigator.pop(context);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Complaint started successfully."),
          backgroundColor: Colors.green,
        ),
      );

      await _loadComplaints();
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _actionLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceFirst("Exception: ", "")),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  // ============================================================
  // RESOLVE DIALOG
  // ============================================================

  Future<void> _showResolveDialog(ComplaintModel complaint) async {
    final resolutionController = TextEditingController();

    final remarksController = TextEditingController();

    final result = await showDialog<bool>(
      context: context,

      barrierDismissible: false,

      builder: (dialogContext) {
        return AlertDialog(
          title: const Text("Resolve Complaint"),

          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,

              children: [
                TextField(
                  controller: resolutionController,

                  maxLines: 4,

                  decoration: const InputDecoration(
                    labelText: "Resolution *",

                    hintText: "Enter work completed / resolution",

                    border: OutlineInputBorder(),
                  ),
                ),

                const SizedBox(height: 14),

                TextField(
                  controller: remarksController,

                  maxLines: 3,

                  decoration: const InputDecoration(
                    labelText: "Engineer Remarks",

                    hintText: "Optional remarks",

                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),

          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },

              child: const Text("Cancel"),
            ),

            ElevatedButton.icon(
              onPressed: () {
                if (resolutionController.text.trim().isEmpty) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    const SnackBar(content: Text("Please enter resolution.")),
                  );

                  return;
                }

                Navigator.pop(dialogContext, true);
              },

              icon: const Icon(Icons.check),

              label: const Text("Resolve"),
            ),
          ],
        );
      },
    );

    if (result != true) {
      resolutionController.dispose();
      remarksController.dispose();
      return;
    }

    final resolution = resolutionController.text.trim();

    final remarks = remarksController.text.trim();

    resolutionController.dispose();
    remarksController.dispose();

    await _resolveComplaint(
      complaint,
      resolution,
      remarks.isEmpty ? null : remarks,
    );
  }

  // ============================================================
  // RESOLVE COMPLAINT
  // ============================================================

  Future<void> _resolveComplaint(
    ComplaintModel complaint,
    String resolution,
    String? remarks,
  ) async {
    setState(() {
      _actionLoading = true;
    });

    try {
      await _complaintService.resolveComplaint(
        complaint.id,

        resolution: resolution,

        engineerRemarks: remarks,
      );

      if (!mounted) return;

      Navigator.pop(context);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Complaint resolved successfully."),
          backgroundColor: Colors.green,
        ),
      );

      await _loadComplaints();
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _actionLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceFirst("Exception: ", "")),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  // ============================================================
  // CLOSE CONFIRMATION
  // ============================================================

  Future<void> _confirmCloseComplaint(ComplaintModel complaint) async {
    final confirmed = await showDialog<bool>(
      context: context,

      builder: (dialogContext) {
        return AlertDialog(
          title: const Text("Close Complaint?"),

          content: const Text(
            "Are you sure you want to close this resolved complaint?",
          ),

          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext, false);
              },

              child: const Text("Cancel"),
            ),

            ElevatedButton(
              onPressed: () {
                Navigator.pop(dialogContext, true);
              },

              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,

                foregroundColor: Colors.white,
              ),

              child: const Text("Close Complaint"),
            ),
          ],
        );
      },
    );

    if (confirmed == true) {
      await _closeComplaint(complaint);
    }
  }

  // ============================================================
  // CLOSE COMPLAINT
  // ============================================================

  Future<void> _closeComplaint(ComplaintModel complaint) async {
    setState(() {
      _actionLoading = true;
    });

    try {
      await _complaintService.closeComplaint(complaint.id);

      if (!mounted) return;

      Navigator.pop(context);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Complaint closed successfully."),
          backgroundColor: Colors.green,
        ),
      );

      await _loadComplaints();
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _actionLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceFirst("Exception: ", "")),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  // ============================================================
  // STATUS TIMELINE
  // ============================================================

  Widget _buildStatusTimeline(ComplaintModel complaint) {
    const statuses = ["NEW", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"];

    if (complaint.status == "CANCELLED") {
      return Container(
        width: double.infinity,

        padding: const EdgeInsets.all(16),

        decoration: BoxDecoration(
          color: Colors.red.shade50,

          borderRadius: BorderRadius.circular(14),

          border: Border.all(color: Colors.red.shade200),
        ),

        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,

          children: [
            Icon(Icons.cancel, color: Colors.red.shade700, size: 30),

            const SizedBox(width: 12),

            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,

                children: [
                  Text(
                    "Complaint Cancelled",

                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),

                  SizedBox(height: 4),

                  Text("This complaint has been cancelled."),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final currentIndex = statuses.indexOf(complaint.status);

    return Container(
      width: double.infinity,

      padding: const EdgeInsets.all(16),

      decoration: BoxDecoration(
        color: Colors.grey.shade50,

        borderRadius: BorderRadius.circular(14),

        border: Border.all(color: Colors.grey.shade200),
      ),

      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          const Text(
            "Complaint Status",

            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 16),

          ...List.generate(statuses.length, (index) {
            final status = statuses[index];

            final completed = currentIndex >= 0 && index <= currentIndex;

            final current = currentIndex == index;

            final isLast = index == statuses.length - 1;

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,

              children: [
                SizedBox(
                  width: 32,

                  child: Column(
                    children: [
                      Container(
                        width: 26,
                        height: 26,

                        decoration: BoxDecoration(
                          shape: BoxShape.circle,

                          color: completed
                              ? Colors.green
                              : Colors.grey.shade300,
                        ),

                        child: Icon(
                          completed ? Icons.check : Icons.circle,

                          size: completed ? 16 : 8,

                          color: completed
                              ? Colors.white
                              : Colors.grey.shade500,
                        ),
                      ),

                      if (!isLast)
                        Container(
                          width: 2,
                          height: 42,

                          color: completed
                              ? Colors.green
                              : Colors.grey.shade300,
                        ),
                    ],
                  ),
                ),

                const SizedBox(width: 10),

                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 3, bottom: 18),

                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,

                      children: [
                        Text(
                          _statusDisplayName(status),

                          style: TextStyle(
                            fontSize: 14,

                            fontWeight: current
                                ? FontWeight.bold
                                : FontWeight.w500,

                            color: completed
                                ? Colors.green.shade800
                                : Colors.grey.shade600,
                          ),
                        ),

                        if (current)
                          Padding(
                            padding: const EdgeInsets.only(top: 3),

                            child: Text(
                              "Current status",

                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.green.shade700,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          }),
        ],
      ),
    );
  }

  // ============================================================
  // DETAIL SECTION
  // ============================================================

  Widget _detailSection(String title, List<Widget> children) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),

      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          Text(
            title,

            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 8),

          ...children,
        ],
      ),
    );
  }

  // ============================================================
  // DETAIL ITEM
  // ============================================================

  Widget _detailItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),

      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          SizedBox(
            width: 105,

            child: Text(
              label,

              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
          ),

          Expanded(
            child: Text(
              value.isEmpty ? "-" : value,

              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
