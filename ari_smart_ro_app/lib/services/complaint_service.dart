import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/complaint_model.dart';
import 'api_service.dart';

class ComplaintService {
  // ============================================================
  // GET ALL COMPLAINTS
  // ============================================================

  Future<List<ComplaintModel>> getComplaints() async {
    final response = await http.get(
      Uri.parse(
        '${ApiService.baseUrl}/complaints/',
      ),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(
        response.body,
      );

      // --------------------------------------------------------
      // API RETURNS LIST
      // --------------------------------------------------------

      if (decoded is List) {
        return decoded
            .map(
              (item) => ComplaintModel.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList();
      }

      // --------------------------------------------------------
      // API RETURNS {"results": [...]}
      // --------------------------------------------------------

      if (decoded is Map<String, dynamic> &&
          decoded["results"] is List) {
        return (decoded["results"] as List)
            .map(
              (item) => ComplaintModel.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList();
      }

      return [];
    }

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    throw Exception(
      "Failed to load complaints. "
      "Status: ${response.statusCode}",
    );
  }

  // ============================================================
  // GET COMPLAINT DETAIL
  // ============================================================

  Future<ComplaintModel> getComplaintDetail(
    int id,
  ) async {
    final response = await http.get(
      Uri.parse(
        '${ApiService.baseUrl}/complaints/$id/',
      ),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(
        response.body,
      );

      return ComplaintModel.fromJson(
        decoded as Map<String, dynamic>,
      );
    }

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    if (response.statusCode == 404) {
      throw Exception(
        "Complaint not found.",
      );
    }

    throw Exception(
      "Failed to load complaint detail. "
      "Status: ${response.statusCode}",
    );
  }

  // ============================================================
  // SEARCH COMPLAINTS
  // ============================================================

  Future<List<ComplaintModel>> searchComplaints(
    String query,
  ) async {
    final cleanQuery = query.trim();

    if (cleanQuery.isEmpty) {
      return getComplaints();
    }

    final uri = Uri.parse(
      '${ApiService.baseUrl}/complaints/search/',
    ).replace(
      queryParameters: {
        "q": cleanQuery,
      },
    );

    final response = await http.get(
      uri,
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(
        response.body,
      );

      // --------------------------------------------------------
      // API RETURNS LIST
      // --------------------------------------------------------

      if (decoded is List) {
        return decoded
            .map(
              (item) => ComplaintModel.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList();
      }

      // --------------------------------------------------------
      // API RETURNS {"results": [...]}
      // --------------------------------------------------------

      if (decoded is Map<String, dynamic> &&
          decoded["results"] is List) {
        return (decoded["results"] as List)
            .map(
              (item) => ComplaintModel.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList();
      }

      return [];
    }

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    throw Exception(
      "Failed to search complaints. "
      "Status: ${response.statusCode}",
    );
  }

  // ============================================================
  // CREATE COMPLAINT
  // ============================================================

  Future<ComplaintModel> createComplaint({
    required int customer,
    required String complaintType,
    required String description,
    String priority = "NORMAL",
    int? engineer,
    String? scheduledDate,
    double? latitude,
    double? longitude,
  }) async {
    final Map<String, dynamic> body = {
      "customer": customer,
      "complaint_type": complaintType,
      "description": description,
      "priority": priority,
    };

    if (engineer != null) {
      body["engineer"] = engineer;
    }

    if (scheduledDate != null &&
        scheduledDate.isNotEmpty) {
      body["scheduled_date"] = scheduledDate;
    }

    if (latitude != null) {
      body["latitude"] = latitude;
    }

    if (longitude != null) {
      body["longitude"] = longitude;
    }

    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/complaints/create/',
      ),
      headers: {
        ...await ApiService.authHeaders(),
        "Content-Type": "application/json",
      },
      body: jsonEncode(body),
    );

    if (response.statusCode == 200 ||
        response.statusCode == 201) {
      final decoded = jsonDecode(
        response.body,
      );

      return ComplaintModel.fromJson(
        decoded as Map<String, dynamic>,
      );
    }

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    throw Exception(
      "Failed to create complaint. "
      "Status: ${response.statusCode} "
      "${response.body}",
    );
  }

  // ============================================================
  // UPDATE COMPLAINT
  // ============================================================

  Future<ComplaintModel> updateComplaint(
    int id, {
    String? complaintType,
    String? description,
    String? priority,
    String? status,
    int? engineer,
    String? scheduledDate,
    String? engineerRemarks,
    String? resolution,
    double? latitude,
    double? longitude,
  }) async {
    final Map<String, dynamic> body = {};

    if (complaintType != null) {
      body["complaint_type"] =
          complaintType;
    }

    if (description != null) {
      body["description"] =
          description;
    }

    if (priority != null) {
      body["priority"] =
          priority;
    }

    if (status != null) {
      body["status"] =
          status;
    }

    if (engineer != null) {
      body["engineer"] =
          engineer;
    }

    if (scheduledDate != null) {
      body["scheduled_date"] =
          scheduledDate;
    }

    if (engineerRemarks != null) {
      body["engineer_remarks"] =
          engineerRemarks;
    }

    if (resolution != null) {
      body["resolution"] =
          resolution;
    }

    if (latitude != null) {
      body["latitude"] =
          latitude;
    }

    if (longitude != null) {
      body["longitude"] =
          longitude;
    }

    final response = await http.patch(
      Uri.parse(
        '${ApiService.baseUrl}/complaints/$id/update/',
      ),
      headers: {
        ...await ApiService.authHeaders(),
        "Content-Type": "application/json",
      },
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(
        response.body,
      );

      return ComplaintModel.fromJson(
        decoded as Map<String, dynamic>,
      );
    }

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    throw Exception(
      "Failed to update complaint. "
      "Status: ${response.statusCode} "
      "${response.body}",
    );
  }

  // ============================================================
  // ASSIGN ENGINEER
  // ============================================================

  Future<ComplaintModel> assignEngineer(
    int complaintId,
    int engineerId,
  ) async {
    return updateComplaint(
      complaintId,
      engineer: engineerId,
      status: "ASSIGNED",
    );
  }

  // ============================================================
  // MARK IN PROGRESS
  // ============================================================

  Future<ComplaintModel> startComplaint(
    int complaintId,
  ) async {
    final response = await http.patch(
      Uri.parse(
        '${ApiService.baseUrl}/complaints/$complaintId/start/',
      ),
      headers: {
        ...await ApiService.authHeaders(),
        "Content-Type": "application/json",
      },
    );

    // ----------------------------------------------------------
    // SUCCESS
    // ----------------------------------------------------------

    if (response.statusCode == 200) {
      final decoded = jsonDecode(
        response.body,
      );

      // Backend returns:
      //
      // {
      //   "success": true,
      //   "message": "...",
      //   "complaint": {...}
      // }
      //
      if (decoded is Map<String, dynamic> &&
          decoded["complaint"] is Map<String, dynamic>) {
        return ComplaintModel.fromJson(
          decoded["complaint"]
              as Map<String, dynamic>,
        );
      }

      // --------------------------------------------------------
      // FALLBACK
      // --------------------------------------------------------
      // In case backend directly returns complaint object.
      // --------------------------------------------------------

      if (decoded is Map<String, dynamic>) {
        return ComplaintModel.fromJson(
          decoded,
        );
      }

      throw Exception(
        "Invalid response received while starting complaint.",
      );
    }

    // ----------------------------------------------------------
    // AUTHENTICATION
    // ----------------------------------------------------------

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    // ----------------------------------------------------------
    // PERMISSION
    // ----------------------------------------------------------

    if (response.statusCode == 403) {
      throw Exception(
        "You are not allowed to start this complaint.",
      );
    }

    // ----------------------------------------------------------
    // NOT FOUND
    // ----------------------------------------------------------

    if (response.statusCode == 404) {
      throw Exception(
        "Complaint not found.",
      );
    }

    // ----------------------------------------------------------
    // BAD REQUEST
    // ----------------------------------------------------------

    if (response.statusCode == 400) {
      try {
        final decoded = jsonDecode(
          response.body,
        );

        if (decoded is Map<String, dynamic> &&
            decoded["message"] != null) {
          throw Exception(
            decoded["message"].toString(),
          );
        }
      } catch (_) {
        // Ignore JSON parsing error.
      }

      throw Exception(
        "Complaint cannot be started.",
      );
    }

    // ----------------------------------------------------------
    // OTHER ERROR
    // ----------------------------------------------------------

    throw Exception(
      "Failed to start complaint. "
      "Status: ${response.statusCode} "
      "${response.body}",
    );
  }

  // ============================================================
  // MARK IN PROGRESS
  // ============================================================
  // Alias method.
  //
  // This keeps compatibility if another screen/controller
  // already uses markInProgress().
  // ============================================================

  Future<ComplaintModel> markInProgress(
    int complaintId,
  ) async {
    return startComplaint(
      complaintId,
    );
  }

  // ============================================================
  // RESOLVE COMPLAINT
  // ============================================================

  Future<ComplaintModel> resolveComplaint(
    int complaintId, {
    required String resolution,
    String? engineerRemarks,
  }) async {
    return updateComplaint(
      complaintId,
      status: "RESOLVED",
      resolution: resolution,
      engineerRemarks:
          engineerRemarks,
    );
  }

  // ============================================================
  // CLOSE COMPLAINT
  // ============================================================

  Future<ComplaintModel> closeComplaint(
    int complaintId,
  ) async {
    final response = await http.patch(
      Uri.parse(
        '${ApiService.baseUrl}/complaints/$complaintId/close/',
      ),
      headers: {
        ...await ApiService.authHeaders(),
        "Content-Type": "application/json",
      },
    );

    // ----------------------------------------------------------
    // SUCCESS
    // ----------------------------------------------------------

    if (response.statusCode == 200) {
      final decoded = jsonDecode(
        response.body,
      );

      if (decoded is Map<String, dynamic> &&
          decoded["complaint"] is Map<String, dynamic>) {
        return ComplaintModel.fromJson(
          decoded["complaint"]
              as Map<String, dynamic>,
        );
      }

      if (decoded is Map<String, dynamic>) {
        return ComplaintModel.fromJson(
          decoded,
        );
      }

      throw Exception(
        "Invalid response received while closing complaint.",
      );
    }

    // ----------------------------------------------------------
    // AUTHENTICATION
    // ----------------------------------------------------------

    if (response.statusCode == 401) {
      throw Exception(
        "Authentication expired. Please login again.",
      );
    }

    // ----------------------------------------------------------
    // PERMISSION
    // ----------------------------------------------------------

    if (response.statusCode == 403) {
      throw Exception(
        "You are not allowed to close this complaint.",
      );
    }

    // ----------------------------------------------------------
    // NOT FOUND
    // ----------------------------------------------------------

    if (response.statusCode == 404) {
      throw Exception(
        "Complaint not found.",
      );
    }

    // ----------------------------------------------------------
    // BAD REQUEST
    // ----------------------------------------------------------

    if (response.statusCode == 400) {
      try {
        final decoded = jsonDecode(
          response.body,
        );

        if (decoded is Map<String, dynamic> &&
            decoded["message"] != null) {
          throw Exception(
            decoded["message"].toString(),
          );
        }
      } catch (_) {
        // Ignore JSON parsing error.
      }

      throw Exception(
        "Complaint cannot be closed.",
      );
    }

    throw Exception(
      "Failed to close complaint. "
      "Status: ${response.statusCode} "
      "${response.body}",
    );
  }
}