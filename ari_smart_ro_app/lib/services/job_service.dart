import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../models/job_model.dart';
import 'api_service.dart';
import 'dart:io';
import 'dart:typed_data';
import 'package:path_provider/path_provider.dart';

class JobService {
  final storage = const FlutterSecureStorage();

  Future<Map<String, String>> _headers() async {
    final token = await storage.read(key: "access");

    return {
      "Authorization": "Bearer $token",
      "Content-Type": "application/json",
    };
  }

  // =======================
  // MY JOBS
  // =======================

  Future<List<JobModel>> getMyJobs() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/jobs/my-jobs/"),
      headers: await _headers(),
    );

    print("========== MY JOBS ==========");
    print("STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);
      return data.map((e) => JobModel.fromJson(e)).toList();
    }

    throw Exception("Failed to load jobs");
  }

  // =======================
  // ACCEPT JOB
  // =======================

  Future<bool> acceptJob(int jobId) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/accept/"),
      headers: await _headers(),
    );

    print("ACCEPT STATUS : ${response.statusCode}");
    print(response.body);

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  // =======================
  // JOB DETAIL
  // =======================

  Future<JobModel> getJobDetail(int jobId) async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/"),
      headers: await _headers(),
    );

    print("DETAIL STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      return JobModel.fromJson(jsonDecode(response.body));
    }

    throw Exception("Unable to load Job");
  }

  // =======================
  // CHANGE STATUS
  // =======================

  Future<bool> changeJobStatus(
    int jobId,
    String status,
  ) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/change-status/"),
      headers: await _headers(),
      body: jsonEncode({
        "status": status,
      }),
    );

    print("CHANGE STATUS : ${response.statusCode}");
    print("BODY : ${response.body}");

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  // =======================
  // GPS
  // =======================

  Future<bool> uploadGPS(
    int jobId,
    double latitude,
    double longitude,
  ) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/gps/"),
      headers: await _headers(),
      body: jsonEncode({
        "latitude": latitude,
        "longitude": longitude,
      }),
    );

    print("GPS STATUS : ${response.statusCode}");
    print("GPS BODY : ${response.body}");

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  // =======================
  // PHOTO
  // =======================

  Future<bool> uploadPhoto(
    int jobId,
    String imagePath,
    String description,
  ) async {
    final token = await storage.read(key: "access");

    var request = http.MultipartRequest(
      "POST",
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/media/"),
    );

    request.headers["Authorization"] = "Bearer $token";

    request.fields["media_type"] = "PHOTO";
    request.fields["description"] = description;

    request.files.add(
      await http.MultipartFile.fromPath(
        "file",
        imagePath,
      ),
    );

    final response = await request.send();

    final body = await response.stream.bytesToString();

    print("PHOTO STATUS : ${response.statusCode}");
    print("PHOTO BODY : $body");

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  // =======================
  // ADD PART TO JOB
  // =======================

  Future<bool> addPartToJob(
    int jobId,
    int inventoryItemId,
  ) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/jobs/$jobId/parts/"),
      headers: await _headers(),
      body: jsonEncode({
        "inventory_item": inventoryItemId,
        "quantity": 1,
      }),
    );

    print("PART STATUS : ${response.statusCode}");
    print("PART BODY : ${response.body}");

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  Future<bool> uploadSignature(
    int jobId,
    Uint8List signatureBytes,
    String customerName,
  ) async {

    final token = await storage.read(key: "access");

    final dir = await getTemporaryDirectory();

    final file = File(
      "${dir.path}/signature.png",
    );

    await file.writeAsBytes(signatureBytes);

    var request = http.MultipartRequest(
      "POST",
      Uri.parse(
        "${ApiService.baseUrl}/jobs/$jobId/signature/",
      ),
    );

    request.headers["Authorization"] =
        "Bearer $token";

    request.fields["customer_name"] =
        customerName;

    request.files.add(
      await http.MultipartFile.fromPath(
        "signature",
        file.path,
      ),
    );

    final response = await request.send();

    final body =
        await response.stream.bytesToString();

    print("SIGNATURE STATUS : ${response.statusCode}");
    print(body);

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }
  Future<bool> completeInstallation({
    required int jobId,
    required int inputTds,
    required int outputTds,
    required String referral,
    required String remarks,
  }) async {

    final response = await http.post(

      Uri.parse(
        "${ApiService.baseUrl}/installations/complete/",
      ),

      headers: await _headers(),

      body: jsonEncode({

        "job": jobId,

        "input_tds": inputTds,

        "output_tds": outputTds,

        "referral_name": referral,

        "remarks": remarks,

      }),

    );

    print("INSTALLATION STATUS : ${response.statusCode}");
    print(response.body);

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  Future<String?> generateOTP(int jobId) async {

    final response = await http.post(
    
      Uri.parse(
        "${ApiService.baseUrl}/jobs/$jobId/generate-otp/",
      ),

      headers: await _headers(),

    );

    print("GENERATE OTP STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {

      final data = jsonDecode(response.body);

      return data["otp"];

    }

    return null;
  }

  Future<bool> verifyOTP(
    int jobId,
    String otp,
  ) async {

    final response = await http.post(
    

      Uri.parse(
        "${ApiService.baseUrl}/jobs/$jobId/verify-otp/",
      ),

      headers: await _headers(),

      body: jsonEncode({

        "otp": otp,

      }),

    );

    print("VERIFY OTP STATUS : ${response.statusCode}");
    print(response.body);

    return response.statusCode == 200;
  }

}