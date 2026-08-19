class ProfileModel {
  final String employeeId;
  final String firstName;
  final String lastName;
  final String pincode;
  final String emergencyName;
  final String emergencyContact;
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
    required this.firstName,
    required this.lastName,
    required this.pincode,
    required this.emergencyName,
    required this.emergencyContact,
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
      firstName: json["first_name"] ?? "",
      lastName: json["last_name"] ?? "",
      pincode: json["pincode"] ?? "",
      emergencyName: json["emergency_name"] ?? "",
      emergencyContact: json["emergency_contact"] ?? "",
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