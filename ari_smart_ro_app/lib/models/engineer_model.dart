class EngineerModel {
  final int id;
  final String employeeId;
  final String name;
  final String phone;
  final String role;
  final String designation;

  EngineerModel({
    required this.id,
    required this.employeeId,
    required this.name,
    required this.phone,
    this.role = "",
    this.designation = "",
  });

  factory EngineerModel.fromJson(Map<String, dynamic> json) {
    return EngineerModel(
      id: json["id"],
      employeeId: json["employee_id"] ?? "",
      name: json["name"] ?? "",
      phone: json["phone"] ?? "",
      role: json["role"]?.toString() ?? "",
      designation: json["designation"]?.toString() ?? "",
    );
  }
}
