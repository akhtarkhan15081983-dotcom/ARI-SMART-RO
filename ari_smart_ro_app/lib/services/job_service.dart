import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../models/job_model.dart';
import 'api_service.dart';
import 'offline_job_store.dart';

class JobService {
  static final OfflineJobStore _offline = OfflineJobStore();

  Future<Map<String, String>> _headers({String? actionId}) async {
    final token = await ApiService.getAccessToken();
    return {
      "Authorization": "Bearer $token",
      "Content-Type": "application/json",
      if (actionId != null) "X-ARI-Action-ID": actionId,
    };
  }

  Future<List<JobModel>> getMyJobs() async {
    unawaited(syncPendingActions());
    try {
      final response = await http
          .get(
            Uri.parse("${ApiService.baseUrl}/jobs/my-jobs/"),
            headers: await _headers(),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final List data = jsonDecode(response.body);
        final jobs = data
            .map((e) => JobModel.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
        await _offline.cacheJobs(jobs);
        return jobs;
      }
      throw Exception("Failed to load jobs");
    } on TimeoutException catch (_) {
      return _cachedJobsOrThrow();
    } on SocketException catch (_) {
      return _cachedJobsOrThrow();
    } on http.ClientException catch (_) {
      return _cachedJobsOrThrow();
    }
  }

  Future<List<JobModel>> _cachedJobsOrThrow() async {
    final cached = await _offline.getCachedJobs();
    if (cached.isNotEmpty) return cached;
    throw Exception("No internet and no downloaded jobs are available yet.");
  }

  Future<bool> acceptJob(int jobId) async {
    return changeJobStatus(jobId, "ACCEPTED");
  }

  Future<JobModel> getJobDetail(int jobId) async {
    try {
      final response = await http
          .get(
            Uri.parse("${ApiService.baseUrl}/jobs/$jobId/"),
            headers: await _headers(),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final job = JobModel.fromJson(
          Map<String, dynamic>.from(jsonDecode(response.body) as Map),
        );
        await _offline.cacheJob(job);
        return job;
      }
      throw Exception("Unable to load Job");
    } on TimeoutException catch (_) {
      return _cachedJobOrThrow(jobId);
    } on SocketException catch (_) {
      return _cachedJobOrThrow(jobId);
    } on http.ClientException catch (_) {
      return _cachedJobOrThrow(jobId);
    }
  }

  Future<JobModel> _cachedJobOrThrow(int jobId) async {
    final cached = await _offline.getCachedJob(jobId);
    if (cached != null) return cached;
    throw Exception("This job has not been downloaded for offline use.");
  }

  Future<bool> changeJobStatus(int jobId, String status) async {
    final actionId = _offline.newActionId("STATUS", jobId);
    try {
      final success = await _sendStatus(
        jobId,
        status,
        actionId: actionId,
      );
      if (success) {
        await _offline.updateCachedStatus(jobId, status);
      }
      return success;
    } on TimeoutException catch (_) {
      await _queueStatus(jobId, status, actionId);
      return true;
    } on SocketException catch (_) {
      await _queueStatus(jobId, status, actionId);
      return true;
    } on http.ClientException catch (_) {
      await _queueStatus(jobId, status, actionId);
      return true;
    }
  }

  Future<void> _queueStatus(int jobId, String status, String actionId) async {
    await _offline.queueAction(
      type: "STATUS",
      jobId: jobId,
      payload: {"status": status},
      actionId: actionId,
    );
    await _offline.updateCachedStatus(jobId, status);
  }

  Future<bool> _sendStatus(
    int jobId,
    String status, {
    required String actionId,
  }) async {
    final response = await http
        .post(
          Uri.parse("${ApiService.baseUrl}/jobs/$jobId/change-status/"),
          headers: await _headers(actionId: actionId),
          body: jsonEncode({"status": status}),
        )
        .timeout(const Duration(seconds: 15));

    if (response.statusCode == 200 || response.statusCode == 201) return true;

    if (response.statusCode == 400) {
      final current = await _fetchRemoteJob(jobId);
      if (current?.status.trim().toUpperCase() == status.trim().toUpperCase()) {
        return true;
      }
    }
    return false;
  }

  Future<JobModel?> _fetchRemoteJob(int jobId) async {
    try {
      final response = await http
          .get(
            Uri.parse("${ApiService.baseUrl}/jobs/$jobId/"),
            headers: await _headers(),
          )
          .timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) return null;
      return JobModel.fromJson(
        Map<String, dynamic>.from(jsonDecode(response.body) as Map),
      );
    } catch (_) {
      return null;
    }
  }

  Future<bool> uploadGPS(int jobId, double latitude, double longitude) async {
    final actionId = _offline.newActionId("GPS", jobId);
    final payload = <String, dynamic>{
      "latitude": latitude,
      "longitude": longitude,
      "captured_at": DateTime.now().toUtc().toIso8601String(),
    };
    try {
      return await _sendGps(jobId, payload, actionId: actionId);
    } on TimeoutException catch (_) {
      await _offline.queueAction(
        type: "GPS",
        jobId: jobId,
        payload: payload,
        actionId: actionId,
      );
      return true;
    } on SocketException catch (_) {
      await _offline.queueAction(
        type: "GPS",
        jobId: jobId,
        payload: payload,
        actionId: actionId,
      );
      return true;
    } on http.ClientException catch (_) {
      await _offline.queueAction(
        type: "GPS",
        jobId: jobId,
        payload: payload,
        actionId: actionId,
      );
      return true;
    }
  }

  Future<bool> _sendGps(
    int jobId,
    Map<String, dynamic> payload, {
    required String actionId,
  }) async {
    final response = await http
        .post(
          Uri.parse("${ApiService.baseUrl}/jobs/$jobId/gps/"),
          headers: await _headers(actionId: actionId),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 15));
    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<bool> uploadPhoto(
    int jobId,
    String imagePath,
    String description,
  ) async {
    final actionId = _offline.newActionId("PHOTO", jobId);
    try {
      return await _sendPhoto(
        jobId,
        imagePath,
        description,
        actionId: actionId,
      );
    } on TimeoutException catch (_) {
      await _offline.queuePhoto(
        jobId: jobId,
        sourcePath: imagePath,
        description: description,
        actionId: actionId,
      );
      return true;
    } on SocketException catch (_) {
      await _offline.queuePhoto(
        jobId: jobId,
        sourcePath: imagePath,
        description: description,
        actionId: actionId,
      );
      return true;
    } on http.ClientException catch (_) {
      await _offline.queuePhoto(
        jobId: jobId,
        sourcePath: imagePath,
        description: description,
        actionId: actionId,
      );
      return true;
    }
  }

  Future<bool> _sendPhoto(
    int jobId,
    String imagePath,
    String description, {
    required String actionId,
  }) async {
    final token = await ApiService.getAccessToken();
    final request = http.MultipartRequest(
      "POST",
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/media/"),
    );
    request.headers["Authorization"] = "Bearer $token";
    request.headers["X-ARI-Action-ID"] = actionId;
    request.fields["media_type"] = "PHOTO";
    request.fields["description"] = description;
    request.files.add(await http.MultipartFile.fromPath("file", imagePath));
    final response = await request.send().timeout(const Duration(seconds: 25));
    await response.stream.drain<void>();
    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<bool> addPartToJob(int jobId, int inventoryItemId) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/parts/"),
      headers: await _headers(),
      body: jsonEncode({"inventory_item": inventoryItemId, "quantity": 1}),
    );
    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<bool> uploadSignature(
    int jobId,
    Uint8List signatureBytes,
    String customerName,
  ) async {
    final actionId = _offline.newActionId("SIGNATURE", jobId);
    try {
      return await _sendSignatureBytes(
        jobId,
        signatureBytes,
        customerName,
        actionId: actionId,
      );
    } on TimeoutException catch (_) {
      await _offline.queueSignature(
        jobId: jobId,
        bytes: signatureBytes,
        customerName: customerName,
        actionId: actionId,
      );
      return true;
    } on SocketException catch (_) {
      await _offline.queueSignature(
        jobId: jobId,
        bytes: signatureBytes,
        customerName: customerName,
        actionId: actionId,
      );
      return true;
    } on http.ClientException catch (_) {
      await _offline.queueSignature(
        jobId: jobId,
        bytes: signatureBytes,
        customerName: customerName,
        actionId: actionId,
      );
      return true;
    }
  }

  Future<bool> _sendSignatureBytes(
    int jobId,
    Uint8List signatureBytes,
    String customerName, {
    required String actionId,
  }) async {
    final dir = await getTemporaryDirectory();
    final file = File("${dir.path}/signature-$actionId.png");
    await file.writeAsBytes(signatureBytes);
    try {
      return await _sendSignatureFile(
        jobId,
        file.path,
        customerName,
        actionId: actionId,
      );
    } finally {
      if (await file.exists()) {
        await file.delete();
      }
    }
  }

  Future<bool> _sendSignatureFile(
    int jobId,
    String filePath,
    String customerName, {
    required String actionId,
  }) async {
    final token = await ApiService.getAccessToken();
    final request = http.MultipartRequest(
      "POST",
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/signature/"),
    );
    request.headers["Authorization"] = "Bearer $token";
    request.headers["X-ARI-Action-ID"] = actionId;
    request.fields["customer_name"] = customerName;
    request.files.add(await http.MultipartFile.fromPath("signature", filePath));
    final response = await request.send().timeout(const Duration(seconds: 25));
    await response.stream.drain<void>();
    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<bool> completeInstallation({
    required int jobId,
    required int inputTds,
    required int outputTds,
    required String referral,
    required String remarks,
  }) async {
    final actionId = _offline.newActionId("INSTALLATION", jobId);
    final payload = <String, dynamic>{
      "job": jobId,
      "input_tds": inputTds,
      "output_tds": outputTds,
      "referral_name": referral,
      "remarks": remarks,
    };
    try {
      return await _sendInstallation(payload, actionId: actionId);
    } on TimeoutException catch (_) {
      await _offline.queueAction(
        type: "INSTALLATION",
        jobId: jobId,
        payload: payload,
        actionId: actionId,
      );
      return true;
    } on SocketException catch (_) {
      await _offline.queueAction(
        type: "INSTALLATION",
        jobId: jobId,
        payload: payload,
        actionId: actionId,
      );
      return true;
    } on http.ClientException catch (_) {
      await _offline.queueAction(
        type: "INSTALLATION",
        jobId: jobId,
        payload: payload,
        actionId: actionId,
      );
      return true;
    }
  }

  Future<bool> _sendInstallation(
    Map<String, dynamic> payload, {
    required String actionId,
  }) async {
    final response = await http
        .post(
          Uri.parse("${ApiService.baseUrl}/installations/complete/"),
          headers: await _headers(actionId: actionId),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 15));
    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<bool> generateOTP(int jobId) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/generate-otp/"),
      headers: await _headers(),
    );
    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<Map<String, dynamic>> getCustomerAssignedEngineer() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/jobs/customer/assigned-engineer/"),
      headers: await _headers(),
    );
    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    }
    throw Exception("Unable to load assigned engineer");
  }

  Future<Map<String, dynamic>> getCustomerActiveOTP() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/jobs/otp/customer-active/"),
      headers: await _headers(),
    );
    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    }
    throw Exception("Unable to load active OTP");
  }

  Future<Map<String, dynamic>> getAdminJobOTP(int jobId) async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/admin-otp/"),
      headers: await _headers(),
    );
    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    }
    throw Exception("Unable to reveal emergency OTP");
  }

  Future<bool> verifyOTP(int jobId, String otp) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/verify-otp/"),
      headers: await _headers(),
      body: jsonEncode({"otp": otp}),
    );
    return response.statusCode == 200;
  }

  Future<int> pendingOfflineCount({int? jobId}) {
    return _offline.pendingCount(jobId: jobId);
  }

  Future<void> markGpsUnavailable(int jobId, bool unavailable) {
    return _offline.setGpsUnavailable(jobId, unavailable);
  }

  Future<bool> isGpsUnavailable(int jobId) {
    return _offline.isGpsUnavailable(jobId);
  }

  Future<int> syncPendingActions() async {
    final pending = await _offline.pendingActions();
    var synced = 0;
    for (final action in pending) {
      final id = action['id']?.toString() ?? '';
      final type = action['type']?.toString() ?? '';
      final jobId = (action['job_id'] as num?)?.toInt();
      final payload = Map<String, dynamic>.from(
        action['payload'] as Map? ?? const <String, dynamic>{},
      );
      if (id.isEmpty || jobId == null) continue;

      try {
        bool success = false;
        switch (type) {
          case "STATUS":
            success = await _sendStatus(
              jobId,
              payload['status']?.toString() ?? '',
              actionId: id,
            );
            break;
          case "GPS":
            success = await _sendGps(jobId, payload, actionId: id);
            break;
          case "PHOTO":
            final filePath = action['file_path']?.toString() ?? '';
            if (filePath.isNotEmpty && await File(filePath).exists()) {
              success = await _sendPhoto(
                jobId,
                filePath,
                payload['description']?.toString() ?? '',
                actionId: id,
              );
            }
            break;
          case "SIGNATURE":
            final filePath = action['file_path']?.toString() ?? '';
            if (filePath.isNotEmpty && await File(filePath).exists()) {
              success = await _sendSignatureFile(
                jobId,
                filePath,
                payload['customer_name']?.toString() ?? '',
                actionId: id,
              );
            }
            break;
          case "INSTALLATION":
            success = await _sendInstallation(payload, actionId: id);
            break;
        }

        if (!success) {
          break;
        }
        await _offline.removeAction(id);
        synced += 1;
      } on TimeoutException {
        break;
      } on SocketException {
        break;
      } on http.ClientException {
        break;
      }
    }
    return synced;
  }
}
