from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import EmployeeProfile


class EmployeeProfileForm(forms.ModelForm):

    emergency_contact = forms.CharField(
        required=False,
        validators=[
            RegexValidator(
                regex=r'^[6-9]\d{9}$',
                message="Enter a valid 10-digit mobile number."
            )
        ]
    )

    class Meta:
        model = EmployeeProfile

        exclude = (
            "user",
            "employee_id",
            "last_latitude",
            "last_longitude",
            "last_location_updated",
            "is_online",
        )

        widgets = {

            "date_of_birth": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),

            "joining_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control"
                }
            ),

            "salary": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01"
                }
            ),
        }

    # -------------------------
    # Aadhaar Validation
    # -------------------------

    def clean_aadhaar_number(self):

        aadhaar = self.cleaned_data.get("aadhaar_number", "").strip()

        if aadhaar:

            if not aadhaar.isdigit():
                raise ValidationError("Aadhaar must contain digits only.")

            if len(aadhaar) != 12:
                raise ValidationError("Aadhaar must be 12 digits.")

        return aadhaar

    # -------------------------
    # PAN Validation
    # -------------------------

    def clean_pan_number(self):

        pan = self.cleaned_data.get("pan_number", "").upper()

        import re

        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"

        if pan:

            if not re.match(pattern, pan):
                raise ValidationError("Invalid PAN Number.")

        return pan

    # -------------------------
    # Salary Validation
    # -------------------------

    def clean_salary(self):

        salary = self.cleaned_data.get("salary")

        if salary < 0:
            raise ValidationError("Salary cannot be negative.")

        return salary

    # -------------------------
    # Date Validation
    # -------------------------

    def clean(self):

        cleaned_data = super().clean()

        dob = cleaned_data.get("date_of_birth")
        joining = cleaned_data.get("joining_date")

        if dob and joining:

            if joining < dob:
                raise ValidationError(
                    "Joining date cannot be earlier than Date of Birth."
                )

        return cleaned_data