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
  final String partsDecision;
  final bool beforePhotoUploaded;
  final bool afterPhotoUploaded;
  final bool otpVerified;
  final bool signatureUploaded;

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
    required this.partsDecision,
    required this.beforePhotoUploaded,
    required this.afterPhotoUploaded,
    required this.otpVerified,
    required this.signatureUploaded,
  });

  factory JobModel.fromJson(Map<String, dynamic> json) {
    return JobModel(
      id: (json["id"] as num).toInt(),
      jobId: json["job_id"] ?? "",
      customerName: json["customer_name"] ?? "",
      customerPhone: json["customer_phone"] ?? json["phone"] ?? "",
      customerAddress: json["customer_address"] ?? json["address"] ?? "",
      phone: json["phone"] ?? json["customer_phone"] ?? "",
      address: json["address"] ?? json["customer_address"] ?? "",
      area: json["area"] ?? "",
      city: json["city"] ?? "",
      assetId: json["asset_id"] ?? "",
      engineerName: json["engineer_name"] ?? "",
      latitude: double.tryParse(json["latitude"].toString()) ?? 0,
      longitude: double.tryParse(json["longitude"].toString()) ?? 0,
      jobType: json["job_type"] ?? "",
      priority: json["priority"] ?? "",
      status: json["status"] ?? "",
      scheduledDate: json["scheduled_date"] ?? "",
      remarks: json["remarks"] ?? "",
      partsDecision: json["parts_decision"] ?? "PENDING",
      beforePhotoUploaded: json["before_photo_uploaded"] == true,
      afterPhotoUploaded: json["after_photo_uploaded"] == true,
      otpVerified: json["otp_verified"] == true,
      signatureUploaded: json["signature_uploaded"] == true,
    );
  }

  Map<String, dynamic> toJson() => <String, dynamic>{
        "id": id,
        "job_id": jobId,
        "customer_name": customerName,
        "customer_phone": customerPhone,
        "customer_address": customerAddress,
        "phone": phone,
        "address": address,
        "area": area,
        "city": city,
        "asset_id": assetId,
        "engineer_name": engineerName,
        "latitude": latitude,
        "longitude": longitude,
        "job_type": jobType,
        "priority": priority,
        "status": status,
        "scheduled_date": scheduledDate,
        "remarks": remarks,
        "parts_decision": partsDecision,
        "before_photo_uploaded": beforePhotoUploaded,
        "after_photo_uploaded": afterPhotoUploaded,
        "otp_verified": otpVerified,
        "signature_uploaded": signatureUploaded,
      };
}
