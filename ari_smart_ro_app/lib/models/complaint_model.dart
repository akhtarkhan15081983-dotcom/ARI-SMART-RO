class ComplaintModel {
  final int id;
  final String complaintId;

  // Customer
  final int? customer;
  final String customerName;
  final String customerIdDisplay;
  final String customerPhone;
  final String currentCardNumber;
  final String oldCardNumber;

  // Engineer
  final int? engineer;
  final String engineerName;
  final String engineerIdDisplay;

  // Complaint
  final String complaintType;
  final String description;
  final String priority;
  final String status;

  // Dates
  final String? complaintDate;
  final String? scheduledDate;
  final String? resolvedDate;

  // Work
  final String engineerRemarks;
  final String resolution;

  // Location
  final double? latitude;
  final double? longitude;

  // Service
  final int? linkedService;
  final String linkedServiceIdDisplay;

  // System
  final String? createdAt;
  final String? updatedAt;

  ComplaintModel({
    required this.id,
    required this.complaintId,

    required this.customer,
    required this.customerName,
    required this.customerIdDisplay,
    required this.customerPhone,
    required this.currentCardNumber,
    required this.oldCardNumber,

    required this.engineer,
    required this.engineerName,
    required this.engineerIdDisplay,

    required this.complaintType,
    required this.description,
    required this.priority,
    required this.status,

    required this.complaintDate,
    required this.scheduledDate,
    required this.resolvedDate,

    required this.engineerRemarks,
    required this.resolution,

    required this.latitude,
    required this.longitude,

    required this.linkedService,
    required this.linkedServiceIdDisplay,

    required this.createdAt,
    required this.updatedAt,
  });

  factory ComplaintModel.fromJson(
    Map<String, dynamic> json,
  ) {
    return ComplaintModel(
      id: _toInt(json["id"]),

      complaintId:
          json["complaint_id"]?.toString() ?? "",

      // ========================================================
      // CUSTOMER
      // ========================================================

      customer: _toNullableInt(
        json["customer"],
      ),

      customerName:
          json["customer_name"]?.toString() ?? "",

      customerIdDisplay:
          json["customer_id_display"]
                  ?.toString() ??
              "",

      customerPhone:
          json["customer_phone"]?.toString() ?? "",

      currentCardNumber:
          json["current_card_number"]
                  ?.toString() ??
              "",

      oldCardNumber:
          json["old_card_number"]
                  ?.toString() ??
              "",

      // ========================================================
      // ENGINEER
      // ========================================================

      engineer: _toNullableInt(
        json["engineer"],
      ),

      engineerName:
          json["engineer_name"]?.toString() ?? "",

      engineerIdDisplay:
          json["engineer_id_display"]
                  ?.toString() ??
              "",

      // ========================================================
      // COMPLAINT
      // ========================================================

      complaintType:
          json["complaint_type"]?.toString() ?? "",

      description:
          json["description"]?.toString() ?? "",

      priority:
          json["priority"]?.toString() ?? "NORMAL",

      status:
          json["status"]?.toString() ?? "NEW",

      // ========================================================
      // DATES
      // ========================================================

      complaintDate:
          json["complaint_date"]?.toString(),

      scheduledDate:
          json["scheduled_date"]?.toString(),

      resolvedDate:
          json["resolved_date"]?.toString(),

      // ========================================================
      // WORK
      // ========================================================

      engineerRemarks:
          json["engineer_remarks"]?.toString() ?? "",

      resolution:
          json["resolution"]?.toString() ?? "",

      // ========================================================
      // LOCATION
      // ========================================================

      latitude:
          _toNullableDouble(
        json["latitude"],
      ),

      longitude:
          _toNullableDouble(
        json["longitude"],
      ),

      // ========================================================
      // SERVICE
      // ========================================================

      linkedService:
          _toNullableInt(
        json["linked_service"],
      ),

      linkedServiceIdDisplay:
          json["linked_service_id_display"]
                  ?.toString() ??
              "",

      // ========================================================
      // SYSTEM
      // ========================================================

      createdAt:
          json["created_at"]?.toString(),

      updatedAt:
          json["updated_at"]?.toString(),
    );
  }

  // ============================================================
  // HELPERS
  // ============================================================

  static int _toInt(
    dynamic value,
  ) {
    if (value is int) {
      return value;
    }

    return int.tryParse(
          value?.toString() ?? "",
        ) ??
        0;
  }

  static int? _toNullableInt(
    dynamic value,
  ) {
    if (value == null) {
      return null;
    }

    if (value is int) {
      return value;
    }

    return int.tryParse(
      value.toString(),
    );
  }

  static double? _toNullableDouble(
    dynamic value,
  ) {
    if (value == null) {
      return null;
    }

    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(
      value.toString(),
    );
  }

  // ============================================================
  // DISPLAY HELPERS
  // ============================================================

  String get displayCustomer {
    if (customerName.isNotEmpty) {
      return customerName;
    }

    return customerIdDisplay.isNotEmpty
        ? customerIdDisplay
        : "-";
  }

  String get displayEngineer {
    if (engineerName.isNotEmpty) {
      return engineerName;
    }

    if (engineerIdDisplay.isNotEmpty) {
      return engineerIdDisplay;
    }

    return "Not Assigned";
  }

  String get displayComplaintType {
    switch (complaintType) {
      case "RO_NOT_WORKING":
        return "RO Not Working";

      case "WATER_LEAKAGE":
        return "Water Leakage";

      case "LOW_TDS":
        return "Low TDS";

      case "BAD_TASTE":
        return "Bad Taste";

      case "LOW_WATER_FLOW":
        return "Low Water Flow";

      case "NO_WATER":
        return "No Water";

      case "PUMP_PROBLEM":
        return "Pump Problem";

      case "MEMBRANE_PROBLEM":
        return "Membrane Problem";

      case "FILTER_PROBLEM":
        return "Filter Problem";

      case "ELECTRICAL":
        return "Electrical Problem";

      case "NOISE":
        return "Unusual Noise";

      case "AMC_SERVICE":
        return "AMC Service";

      case "OTHER":
        return "Other";

      default:
        return complaintType.isEmpty
            ? "-"
            : complaintType;
    }
  }

  String get displayPriority {
    switch (priority) {
      case "EMERGENCY":
        return "Emergency";

      case "URGENT":
        return "Urgent";

      case "NORMAL":
        return "Normal";

      default:
        return priority.isEmpty
            ? "-"
            : priority;
    }
  }

  String get displayStatus {
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
        return status.isEmpty
            ? "-"
            : status;
    }
  }
}