class BagItemModel {
  final int id;
  final String partName;
  final String? serialNumber;
  final String status;
  final int? engineerId;
  final String engineerName;
  final String employeeId;

  BagItemModel({
    required this.id,
    required this.partName,
    required this.serialNumber,
    required this.status,
    this.engineerId,
    this.engineerName = "",
    this.employeeId = "",
  });

  factory BagItemModel.fromJson(Map<String, dynamic> json) {
    return BagItemModel(
      id: json["id"],
      partName: json["part_name"] ?? "",
      serialNumber: json["serial_number"],
      status: json["status"] ?? "",
      engineerId: json["engineer_id"],
      engineerName: json["engineer_name"] ?? "",
      employeeId: json["employee_id"] ?? "",
    );
  }
}
