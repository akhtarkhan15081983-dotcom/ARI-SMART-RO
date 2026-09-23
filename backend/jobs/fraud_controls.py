from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Job, JobActivityLog
from .services import FIELD_WORK_TYPES, NO_PARTS_ACTIVITY


class JobNoPartsDeclarationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        job = (
            Job.objects.select_for_update()
            .filter(pk=pk, engineer__user=request.user)
            .first()
        )
        if job is None:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        if job.job_type not in FIELD_WORK_TYPES:
            return Response(
                {"detail": "No-parts declaration is only valid for service or complaint jobs."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job.status != "IN_PROGRESS":
            return Response(
                {"detail": "No-parts declaration can only be made while work is in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job.parts_used.exists():
            return Response(
                {"detail": "Parts are already recorded for this job."},
                status=status.HTTP_409_CONFLICT,
            )

        confirmation = request.data.get("confirm_no_parts") is True
        if not confirmation:
            return Response(
                {"detail": "Explicit confirmation that no part was used is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        remarks = str(request.data.get("remarks", "")).strip()
        JobActivityLog.objects.update_or_create(
            job=job,
            engineer=job.engineer,
            activity=NO_PARTS_ACTIVITY,
            defaults={"remarks": remarks or "Engineer confirmed no replacement part was used."},
        )
        return Response(
            {
                "success": True,
                "job_id": job.job_id,
                "parts_decision": "NO_PARTS",
                "message": "No-parts declaration recorded in the audit trail.",
            },
            status=status.HTTP_200_OK,
        )
