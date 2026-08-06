class AttendanceModel {
  final int id;
  final String employeeName;
  final String date;
  final String? checkIn;
  final String? checkOut;
  final double workingHours;
  final String status;
  final double? latitude;
  final double? longitude;
  final String? selfie;
  final String? remarks;

  AttendanceModel({
    required this.id,
    required this.employeeName,
    required this.date,
    this.checkIn,
    this.checkOut,
    required this.workingHours,
    required this.status,
    this.latitude,
    this.longitude,
    this.selfie,
    this.remarks,
  });

  factory AttendanceModel.fromJson(
    Map<String, dynamic> json,
  ) {
    return AttendanceModel(
      id: json["id"] ?? 0,

      employeeName: json["employee_name"] ?? "",

      date: json["date"] ?? "",

      checkIn: json["check_in"],

      checkOut: json["check_out"],

      workingHours: double.tryParse(
            json["working_hours"].toString(),
          ) ??
          0.0,

      status: json["status"] ?? "",

      latitude: json["latitude"] == null
          ? null
          : double.tryParse(
              json["latitude"].toString(),
            ),

      longitude: json["longitude"] == null
          ? null
          : double.tryParse(
              json["longitude"].toString(),
            ),

      selfie: json["selfie"],

      remarks: json["remarks"],
    );
  }
}