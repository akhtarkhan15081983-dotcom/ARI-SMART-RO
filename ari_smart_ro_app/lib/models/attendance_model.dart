class AttendanceModel {
  final int id;
  final String employeeName;
  final String date;
  final String? checkIn;
  final String? checkOut;
  final double workingHours;
  final double regularWorkingHours;
  final double overtimeWorkingHours;
  final String? regularShiftEndAt;
  final bool autoCheckedOut;
  final String checkoutReason;
  final Map<String, dynamic>? overtime;
  final String status;
  final double? latitude;
  final double? longitude;
  final String? selfie;
  final String? remarks;
  final String identityReviewStatus;
  final String? identityReviewNote;
  final String? serverTime;
  final String? checkoutReminderAt;

  AttendanceModel({
    required this.id,
    required this.employeeName,
    required this.date,
    this.checkIn,
    this.checkOut,
    required this.workingHours,
    this.regularWorkingHours = 0,
    this.overtimeWorkingHours = 0,
    this.regularShiftEndAt,
    this.autoCheckedOut = false,
    this.checkoutReason = '',
    this.overtime,
    required this.status,
    this.latitude,
    this.longitude,
    this.selfie,
    this.remarks,
    this.identityReviewStatus = 'PENDING',
    this.identityReviewNote,
    this.serverTime,
    this.checkoutReminderAt,
  });

  bool get isReviewRejected => identityReviewStatus.toUpperCase() == 'REJECTED';
  bool get isReviewApproved => identityReviewStatus.toUpperCase() == 'APPROVED';
  bool get isReviewPending => identityReviewStatus.toUpperCase() == 'PENDING';

  factory AttendanceModel.fromJson(Map<String, dynamic> json) {
    return AttendanceModel(
      id: json['id'] ?? 0,
      employeeName: json['employee_name'] ?? '',
      date: json['date'] ?? '',
      checkIn: json['check_in'],
      checkOut: json['check_out'],
      workingHours: double.tryParse(json['working_hours'].toString()) ?? 0.0,
      regularWorkingHours:
          double.tryParse(json['regular_working_hours'].toString()) ?? 0.0,
      overtimeWorkingHours:
          double.tryParse(json['overtime_working_hours'].toString()) ?? 0.0,
      regularShiftEndAt: json['regular_shift_end_at']?.toString(),
      autoCheckedOut: json['auto_checked_out'] == true,
      checkoutReason: (json['checkout_reason'] ?? '').toString(),
      overtime: json['overtime'] is Map
          ? Map<String, dynamic>.from(json['overtime'] as Map)
          : null,
      status: json['status'] ?? '',
      latitude: json['latitude'] == null
          ? null
          : double.tryParse(json['latitude'].toString()),
      longitude: json['longitude'] == null
          ? null
          : double.tryParse(json['longitude'].toString()),
      selfie: json['selfie'],
      remarks: json['remarks'],
      identityReviewStatus: (json['identity_review_status'] ?? 'PENDING')
          .toString()
          .toUpperCase(),
      identityReviewNote: json['identity_review_note']?.toString(),
      serverTime: json['server_time']?.toString(),
      checkoutReminderAt: json['checkout_reminder_at']?.toString(),
    );
  }
}
