class AssetModel {
  final int id;
  final String assetId;
  final String serialNumber;
  final String status;
  final int roModelId;
  final String roModelName;

  AssetModel({
    required this.id,
    required this.assetId,
    required this.serialNumber,
    required this.status,
    required this.roModelId,
    required this.roModelName,
  });

  factory AssetModel.fromJson(Map<String, dynamic> json) {
    return AssetModel(
      id: json["id"],
      assetId: json["asset_id"] ?? "",
      serialNumber: json["serial_number"] ?? "",
      status: json["status"] ?? "",

      roModelId: json["ro_model"] ?? 0,

      roModelName: json["ro_model_name"] ?? "",
    );
  }
}