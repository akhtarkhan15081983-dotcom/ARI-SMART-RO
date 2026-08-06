class BagItemModel {
  final int id;
  final String partName;
  final String? serialNumber;
  final String status;

  BagItemModel({
    required this.id,
    required this.partName,
    required this.serialNumber,
    required this.status,
  });

  factory BagItemModel.fromJson(Map<String, dynamic> json) {
    return BagItemModel(
      id: json["id"],
      partName: json["part_name"] ?? "",
      serialNumber: json["serial_number"],
      status: json["status"] ?? "",
    );
  }
}