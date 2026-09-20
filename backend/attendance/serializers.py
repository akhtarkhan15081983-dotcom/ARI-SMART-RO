from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from employees.models import HRPolicy
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.user.get_full_name",
        read_only=True,
    )
    server_time = serializers.SerializerMethodField()
    checkout_reminder_at = serializers.SerializerMethodField()

    def get_server_time(self, obj):
        return timezone.localtime(timezone.now()).isoformat()

    def get_checkout_reminder_at(self, obj):
        if not obj.check_in or obj.check_out:
            return None
        hours = float(HRPolicy.current().daily_work_hours)
        return timezone.localtime(obj.check_in + timedelta(hours=hours)).isoformat()

    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = (
            "working_hours",
            "created_at",
        )
