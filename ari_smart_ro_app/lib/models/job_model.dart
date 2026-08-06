class JobModel {
  final int id;
  final String jobId;

  final String customerName;
  final String customerPhone;
  final String customerAddress;

  final String phone;
  final String address;
  final String area;
  final String city;

  final String assetId;
  final String engineerName;

  final double latitude;
  final double longitude;

  final String jobType;
  final String priority;
  final String status;
  final String scheduledDate;
  final String remarks;

  JobModel({
    required this.id,
    required this.jobId,
    required this.customerName,
    required this.customerPhone,
    required this.customerAddress,
    required this.phone,
    required this.address,
    required this.area,
    required this.city,
    required this.assetId,
    required this.engineerName,
    required this.latitude,
    required this.longitude,
    required this.jobType,
    required this.priority,
    required this.status,
    required this.scheduledDate,
    required this.remarks,
  });

  factory JobModel.fromJson(Map<String, dynamic> json) {
    return JobModel(
      id: json["id"],

      jobId: json["job_id"] ?? "",

      customerName: json["customer_name"] ?? "",

      customerPhone:
          json["customer_phone"] ??
          json["phone"] ??
          "",

      customerAddress:
          json["customer_address"] ??
          json["address"] ??
          "",

      phone: json["phone"] ?? "",
      address: json["address"] ?? "",
      area: json["area"] ?? "",
      city: json["city"] ?? "",

      assetId: json["asset_id"] ?? "",
      engineerName: json["engineer_name"] ?? "",

      latitude: double.tryParse(
              json["latitude"].toString()) ??
          0,

      longitude: double.tryParse(
              json["longitude"].toString()) ??
          0,

      jobType: json["job_type"] ?? "",

      priority: json["priority"] ?? "",

      status: json["status"] ?? "",

      scheduledDate:
          json["scheduled_date"] ?? "",

      remarks: json["remarks"] ?? "",
    );
  }
}