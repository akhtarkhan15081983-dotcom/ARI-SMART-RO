class LoginResponse {
  final bool success;
  final String access;
  final String refresh;
  final LoginUser user;

  LoginResponse({
    required this.success,
    required this.access,
    required this.refresh,
    required this.user,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      success: json["success"],
      access: json["access"],
      refresh: json["refresh"],
      user: LoginUser.fromJson(json["user"]),
    );
  }
}

class LoginUser {
  final int id;
  final String phone;
  final String fullName;
  final String role;

  LoginUser({
    required this.id,
    required this.phone,
    required this.fullName,
    required this.role,
  });

  factory LoginUser.fromJson(Map<String, dynamic> json) {
    return LoginUser(
      id: json["id"],
      phone: json["phone"] ?? "",
      fullName: json["full_name"] ?? "",
      role: json["role"] ?? "",
    );
  }
}