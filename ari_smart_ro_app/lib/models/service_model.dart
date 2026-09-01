class ServiceModel {
  final int id;
  final String serviceId;
  final int? customer;
  final int? engineer;
  final int? roAsset;
  final String serviceType;
  final String status;
  final String scheduledDate;
  final String? completedDate;
  final String? nextServiceDate;
  final int? inputTds;
  final int? outputTds;
  final String remarks;
  final double? latitude;
  final double? longitude;

  ServiceModel({
    required this.id,
    required this.serviceId,
    this.customer,
    this.engineer,
    this.roAsset,
    required this.serviceType,
    required this.status,
    required this.scheduledDate,
    this.completedDate,
    this.nextServiceDate,
    this.inputTds,
    this.outputTds,
    required this.remarks,
    this.latitude,
    this.longitude,
  });

  factory ServiceModel.fromJson(Map<String, dynamic> json) {
    return ServiceModel(
      id: json["id"] ?? 0,
      serviceId: json["service_id"] ?? "",
      customer: json["customer"] is int
          ? json["customer"]
          : int.tryParse(json["customer"]?.toString() ?? ""),
      engineer: json["engineer"] is int
          ? json["engineer"]
          : int.tryParse(json["engineer"]?.toString() ?? ""),
      roAsset: json["ro_asset"] is int
          ? json["ro_asset"]
          : int.tryParse(json["ro_asset"]?.toString() ?? ""),
      serviceType: json["service_type"] ?? "",
      status: json["status"] ?? "",
      scheduledDate: json["scheduled_date"] ?? "",
      completedDate: json["completed_date"],
      nextServiceDate: json["next_service_date"],
      inputTds: json["input_tds"] is int
          ? json["input_tds"]
          : int.tryParse(json["input_tds"]?.toString() ?? ""),
      outputTds: json["output_tds"] is int
          ? json["output_tds"]
          : int.tryParse(json["output_tds"]?.toString() ?? ""),
      remarks: json["remarks"] ?? "",
      latitude: json["latitude"] != null
          ? double.tryParse(json["latitude"].toString())
          : null,
      longitude: json["longitude"] != null
          ? double.tryParse(json["longitude"].toString())
          : null,
    );
  }
}
