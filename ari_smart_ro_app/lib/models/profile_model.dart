class ProfileModel {
  final String employeeId;
  final String fullName;
  final String phone;
  final String email;
  final String role;
  final String designation;
  final String joiningDate;
  final String gender;
  final String city;
  final String state;
  final String address;
  final String? photo;

  ProfileModel({
    required this.employeeId,
    required this.fullName,
    required this.phone,
    required this.email,
    required this.role,
    required this.designation,
    required this.joiningDate,
    required this.gender,
    required this.city,
    required this.state,
    required this.address,
    this.photo,
  });

  factory ProfileModel.fromJson(Map<String, dynamic> json) {
    return ProfileModel(
      employeeId: json["employee_id"] ?? "",
      fullName: json["full_name"] ?? "",
      phone: json["phone"] ?? "",
      email: json["email"] ?? "",
      role: json["role"] ?? "",
      designation: json["designation"] ?? "",
      joiningDate: json["joining_date"] ?? "",
      gender: json["gender"] ?? "",
      city: json["city"] ?? "",
      state: json["state"] ?? "",
      address: json["address"] ?? "",
      photo: json["photo"],
    );
  }
}