from django.db.models.signals import post_save
from django.dispatch import receiver

from .hr_phase2_letters_bgv_models import BackgroundVerificationCase
from .hr_phase2_recruitment_models import CandidateApplication


@receiver(post_save, sender=CandidateApplication)
def preserve_bgv_on_candidate_conversion(sender, instance, **kwargs):
    """Link the pre-join BGV case to the converted employee without duplicating checks."""
    if not instance.converted_employee_id:
        return
    row = (
        BackgroundVerificationCase.objects.filter(
            company_id=instance.company_id,
            application_id=instance.id,
        )
        .order_by("id")
        .first()
    )
    if row is None:
        return
    if row.employee_id and row.employee_id != instance.converted_employee_id:
        return
    if row.employee_id != instance.converted_employee_id:
        row.employee_id = instance.converted_employee_id
        row.save(update_fields=["employee", "updated_at"])
