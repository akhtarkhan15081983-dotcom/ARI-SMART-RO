class ServiceModel {
  final int id;
  final String serviceId;
  final int? job;
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
    this.job,
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
    int? asInt(dynamic value) => value is int
        ? value
        : int.tryParse(value?.toString() ?? '');

    return ServiceModel(
      id: asInt(json['id']) ?? 0,
      serviceId: json['service_id']?.toString() ?? '',
      job: asInt(json['job']),
      customer: asInt(json['customer']),
      engineer: asInt(json['engineer']),
      roAsset: asInt(json['ro_asset']),
      serviceType: json['service_type']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      scheduledDate: json['scheduled_date']?.toString() ?? '',
      completedDate: json['completed_date']?.toString(),
      nextServiceDate: json['next_service_date']?.toString(),
      inputTds: asInt(json['input_tds']),
      outputTds: asInt(json['output_tds']),
      remarks: json['remarks']?.toString() ?? '',
      latitude: json['latitude'] != null
          ? double.tryParse(json['latitude'].toString())
          : null,
      longitude: json['longitude'] != null
          ? double.tryParse(json['longitude'].toString())
          : null,
    );
  }
}
