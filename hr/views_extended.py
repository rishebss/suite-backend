from rest_framework import serializers, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from decimal import Decimal

from django.http import HttpResponse

from hr.models import (
    GoalLibrary, RatingScale, RatingScaleOption, AppraisalFormTemplate,
    AppraisalFormSection, AppraisalFormQuestion, AppraisalFormResponse,
    BellCurveConfig, PromotionMatrix, PromotionMatrixRow, GoalCascade,
    AppraisalCycleStage,
    JobRequisition, Candidate, JobApplication,
    AppraisalCycle, PerformanceGoal, PerformanceReview,
    TrainingProgram, TrainingNomination,
    Resignation, ExitClearance,
    EmployeeFamily, EmployeeEmergencyContact, EmployeeBankAccount,
    EmployeeDocumentVersion, ExitInterview, ExitInterviewResponse,
    FnFSettlement, FnFSettlementComponent, AlumniRecord,
    HRTicket, HRTicketConversation, AssetRequest,
    OKR, Feedback360, PIPlan, CalibrationSession,
    Skill, EmployeeSkill, TrainingNeed, TrainingAssessment, TrainingCost,
    InterviewSchedule, OfferLetter, BGVCheck, OnboardingTask,
    Employee, InternalJobPosting, InternalJobApplication, EmployeeReferral,
    OnboardingBuddy, PreJoiningDocument, OnboardingFeedback,
    POSHComplaint, POSHInquiryNote,
    DataConsentRecord,
    StayInterview,
    SalaryFreeze,
)
from hr.serializers_extended import (
    JobRequisitionSerializer, CandidateSerializer, JobApplicationSerializer,
    AppraisalCycleSerializer, PerformanceGoalSerializer, PerformanceReviewSerializer,
    TrainingProgramSerializer, TrainingNominationSerializer,
    ResignationSerializer, ExitClearanceSerializer,
    EmployeeFamilySerializer, EmployeeEmergencyContactSerializer,
    EmployeeBankAccountSerializer, EmployeeDocumentVersionSerializer,
    ExitInterviewSerializer, ExitInterviewResponseSerializer,
    FnFSettlementSerializer, FnFSettlementListSerializer, FnFSettlementComponentSerializer,
    AlumniRecordSerializer, HRTicketSerializer, HRTicketConversationSerializer,
    AssetRequestSerializer, OKRSerializer, Feedback360Serializer,
    PIPlanSerializer, CalibrationSessionSerializer, SkillSerializer,
    EmployeeSkillSerializer, TrainingNeedSerializer, TrainingAssessmentSerializer,
    TrainingCostSerializer, InterviewScheduleSerializer, OfferLetterSerializer,
    BGVCheckSerializer, OnboardingTaskSerializer,
    InternalJobPostingSerializer, InternalJobApplicationSerializer,
    EmployeeReferralSerializer, OnboardingBuddySerializer,
    PreJoiningDocumentSerializer, OnboardingFeedbackSerializer,
    GoalLibrarySerializer, RatingScaleSerializer, RatingScaleOptionSerializer,
    AppraisalFormTemplateSerializer, AppraisalFormSectionSerializer,
    AppraisalFormQuestionSerializer, AppraisalFormResponseSerializer,
    BellCurveConfigSerializer, PromotionMatrixSerializer, PromotionMatrixRowSerializer,
    GoalCascadeSerializer, AppraisalCycleStageSerializer,
    POSHComplaintSerializer, POSHInquiryNoteSerializer,
    DataConsentRecordSerializer,
    StayInterviewSerializer,
    SalaryFreezeSerializer,
)
from hr.permissions import IsHRAdmin, IsHRStaff, IsManagerOrHR, IsEmployeeOrHR
from hr.services.exit_service import ExitManagementEngine, AttritionAnalytics
from hr.services.reports_service import ReportDataAggregator


# ============================================================================
# CORE HR ENHANCEMENTS
# ============================================================================

class EmployeeFamilyViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Family Members (nominee, dependent info)."""
    serializer_class = EmployeeFamilySerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'relationship', 'is_dependent', 'is_nominee']
    search_fields = ['name', 'employee__employee_id']

    def get_queryset(self):
        return EmployeeFamily.objects.select_related('employee').all()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=['get'])
    def nominees(self, request):
        """Get all active nominees."""
        nominees = self.get_queryset().filter(is_nominee=True, is_active=True)
        serializer = self.get_serializer(nominees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dependents(self, request):
        """Get all dependents (for insurance)."""
        dependents = self.get_queryset().filter(is_dependent=True, is_active=True)
        serializer = self.get_serializer(dependents, many=True)
        return Response(serializer.data)


class EmployeeEmergencyContactViewSet(viewsets.ModelViewSet):
    """ViewSet for Emergency Contacts."""
    serializer_class = EmployeeEmergencyContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_primary']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeEmergencyContact.objects.select_related('employee').all()
        try:
            emp = user.employee
            return EmployeeEmergencyContact.objects.filter(employee=emp)
        except:
            return EmployeeEmergencyContact.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            # If marking as primary, unmark others
            if serializer.validated_data.get('is_primary'):
                EmployeeEmergencyContact.objects.filter(employee=emp, is_primary=True).update(is_primary=False)
            serializer.save(employee=emp)
        except:
            serializer.save()


class EmployeeBankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for Multi-Bank Accounts."""
    serializer_class = EmployeeBankAccountSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'account_type', 'is_verified']

    def get_queryset(self):
        return EmployeeBankAccount.objects.select_related('employee').all()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def verify(self, request, pk=None):
        """Verify a bank account."""
        account = self.get_object()
        account.is_verified = True
        account.verified_date = timezone.now()
        account.save()
        return Response({'status': 'Bank account verified'})


class EmployeeDocumentVersionViewSet(viewsets.ModelViewSet):
    """ViewSet for Document Versioning."""
    serializer_class = EmployeeDocumentVersionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['document', 'is_current']
    ordering_fields = ['-version_number']

    def get_queryset(self):
        return EmployeeDocumentVersion.objects.select_related('document', 'uploaded_by').all()

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


# ============================================================================
# RECRUITMENT ENHANCEMENTS
# ============================================================================

class JobRequisitionViewSet(viewsets.ModelViewSet):
    """ViewSet for Job Requisition management with approval."""
    serializer_class = JobRequisitionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'designation', 'priority', 'status']
    search_fields = ['justification', 'department__name', 'designation__name']

    def get_queryset(self):
        return JobRequisition.objects.select_related('department', 'designation', 'requested_by').all()

    def perform_create(self, serializer):
        try:
            employee = self.request.user.employee
        except Exception:
            raise serializers.ValidationError({"requested_by": "No employee profile found for your account"})
        serializer.save(requested_by=employee)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def approve(self, request, pk=None):
        """Approve requisition."""
        req = self.get_object()
        req.status = 'Approved'
        req.save()
        return Response({'status': 'Requisition approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject requisition."""
        req = self.get_object()
        req.status = 'Rejected'
        req.save()
        return Response({'status': 'Requisition rejected'})


class CandidateViewSet(viewsets.ModelViewSet):
    """ViewSet for Candidate database."""
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['source']
    search_fields = ['first_name', 'last_name', 'email', 'phone']

    def get_queryset(self):
        return Candidate.objects.all()

    @action(detail=False, methods=['get'])
    def search_by_skill(self, request):
        """Search candidates by skills."""
        skill = request.query_params.get('skill', '')
        if skill:
            candidates = self.get_queryset().filter(skills__icontains=skill)
            serializer = self.get_serializer(candidates, many=True)
            return Response(serializer.data)
        return Response({'error': 'skill parameter required'}, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Job Applications (ATS Pipeline)."""
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['requisition', 'candidate', 'stage']
    search_fields = ['candidate__first_name', 'candidate__email']

    def get_queryset(self):
        return JobApplication.objects.select_related('candidate', 'requisition').all()

    @action(detail=True, methods=['post'])
    def advance_stage(self, request, pk=None):
        """Advance candidate to next stage."""
        app = self.get_object()
        stages = ['Applied', 'Screening', 'L1_Interview', 'L2_Interview', 'HR_Round', 'Offered']
        if app.stage in stages:
            idx = stages.index(app.stage)
            if idx < len(stages) - 1:
                app.stage = stages[idx + 1]
                app.save()
                return Response({'status': f'Stage advanced to {app.stage}'})
        return Response({'error': 'Cannot advance further'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject application."""
        app = self.get_object()
        app.stage = 'Rejected'
        app.save()
        return Response({'status': 'Application rejected'})


class InterviewScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for Interview Scheduling."""
    serializer_class = InterviewScheduleSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['application', 'interview_type', 'status', 'interview_mode']
    search_fields = ['application__candidate__first_name', 'application__candidate__email']

    def get_queryset(self):
        return InterviewSchedule.objects.select_related('application__candidate').all()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        """Submit interview feedback."""
        interview = self.get_object()
        interview.feedback = request.data.get('feedback', '')
        interview.rating = request.data.get('rating')
        interview.feedback_submitted = True
        interview.status = 'COMPLETED'
        interview.save()
        return Response({'status': 'Feedback submitted'})

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule interview."""
        interview = self.get_object()
        new_date = request.data.get('scheduled_date')
        if new_date:
            interview.scheduled_date = new_date
            interview.status = 'RESCHEDULED'
            interview.save()
            return Response({'status': 'Interview rescheduled'})
        return Response({'error': 'scheduled_date required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's interviews."""
        from datetime import date
        today = date.today()
        interviews = self.get_queryset().filter(
            scheduled_date__date=today,
            status='SCHEDULED'
        )
        serializer = self.get_serializer(interviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_interviews(self, request):
        """Get current user's interviews as interviewer."""
        interviews = self.get_queryset().filter(interviewers=request.user)
        serializer = self.get_serializer(interviews, many=True)
        return Response(serializer.data)


class OfferLetterViewSet(viewsets.ModelViewSet):
    """ViewSet for Offer Letter management."""
    serializer_class = OfferLetterSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'candidate', 'requisition']
    search_fields = ['candidate__first_name', 'candidate__email']

    def get_queryset(self):
        return OfferLetter.objects.select_related('candidate', 'requisition').all()

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark offer as sent."""
        offer = self.get_object()
        offer.status = 'SENT'
        offer.sent_date = timezone.now()
        offer.save()
        return Response({'status': 'Offer marked as sent'})

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Mark offer as accepted."""
        offer = self.get_object()
        offer.status = 'ACCEPTED'
        offer.response_date = timezone.now()
        if request.FILES.get('acceptance_letter'):
            offer.acceptance_letter = request.FILES['acceptance_letter']
        offer.save()
        return Response({'status': 'Offer accepted'})

    @action(detail=True, methods=['post'])
    def reject_offer(self, request, pk=None):
        """Mark offer as rejected."""
        offer = self.get_object()
        offer.status = 'REJECTED'
        offer.response_date = timezone.now()
        offer.notes = request.data.get('reason', '')
        offer.save()
        return Response({'status': 'Offer rejected'})


class BGVCheckViewSet(viewsets.ModelViewSet):
    """ViewSet for Background Verification tracking."""
    serializer_class = BGVCheckSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['candidate', 'status']

    def get_queryset(self):
        return BGVCheck.objects.select_related('candidate').all()

    @action(detail=True, methods=['post'])
    def initiate(self, request, pk=None):
        """Initiate BGV check."""
        bgv = self.get_object()
        bgv.status = 'INITIATED'
        bgv.initiated_date = timezone.now().date()
        bgv.vendor_name = request.data.get('vendor_name', bgv.vendor_name)
        bgv.save()
        return Response({'status': 'BGV initiated'})

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update BGV status and verification details."""
        bgv = self.get_object()
        bgv.status = request.data.get('status', bgv.status)
        for field in ['identity_verified', 'address_verified', 'education_verified',
                      'employment_verified', 'criminal_verified']:
            if field in request.data:
                setattr(bgv, field, request.data[field])
        if bgv.status == 'CLEAR' or bgv.status == 'DISCREPANT':
            bgv.completed_date = timezone.now().date()
        bgv.remarks = request.data.get('remarks', bgv.remarks)
        bgv.save()
        return Response({'status': f'BGV updated to {bgv.status}'})


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Onboarding Checklist."""
    serializer_class = OnboardingTaskSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'task_type', 'is_completed']

    def get_queryset(self):
        return OnboardingTask.objects.select_related('employee', 'assigned_to', 'completed_by').all()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as completed."""
        task = self.get_object()
        task.is_completed = True
        task.completed_date = timezone.now()
        task.completed_by = request.user
        task.save()
        return Response({'status': 'Task completed'})

    @action(detail=False, methods=['get'])
    def employee_tasks(self, request):
        """Get tasks for a specific employee."""
        employee_id = request.query_params.get('employee_id')
        if employee_id:
            tasks = self.get_queryset().filter(employee_id=employee_id).order_by('task_type', 'order')
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        return Response({'error': 'employee_id required'}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# EXIT MANAGEMENT ENHANCEMENTS
# ============================================================================

class ResignationViewSet(viewsets.ModelViewSet):
    """ViewSet for Resignation management with exit workflow."""
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'status']
    search_fields = ['employee__first_name', 'employee__last_name']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return Resignation.objects.select_related('employee').all()
        try:
            emp = user.employee
            return Resignation.objects.filter(employee=emp)
        except:
            return Resignation.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(employee=emp)
        except:
            serializer.save()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve resignation with last working day."""
        resignation = self.get_object()
        last_day = request.data.get('approved_last_working_day')
        if not last_day:
            return Response({'error': 'approved_last_working_day required'}, status=status.HTTP_400_BAD_REQUEST)
        resignation.status = 'Approved'
        resignation.approved_last_working_day = last_day
        resignation.save()
        # Update employee status
        emp = resignation.employee
        emp.status = 'NOTICE_PERIOD'
        emp.save()
        return Response({'status': 'Resignation approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject resignation."""
        resignation = self.get_object()
        resignation.status = 'Rejected'
        resignation.save()
        return Response({'status': 'Resignation rejected'})

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw resignation."""
        resignation = self.get_object()
        resignation.status = 'Withdrawn'
        resignation.save()
        return Response({'status': 'Resignation withdrawn'})

    @action(detail=True, methods=['post'])
    def calculate_fn_f(self, request, pk=None):
        """Calculate Full & Final Settlement."""
        resignation = self.get_object()
        exit_date = request.data.get('exit_date', resignation.approved_last_working_day)
        if not exit_date:
            return Response({'error': 'exit_date required'}, status=status.HTTP_400_BAD_REQUEST)
        from datetime import date
        if isinstance(exit_date, str):
            from datetime import datetime
            exit_date = datetime.strptime(exit_date, '%Y-%m-%d').date()
        engine = ExitManagementEngine(resignation.employee)
        result = engine.calculate_fn_f(resignation, exit_date)
        return Response(result)

    @action(detail=True, methods=['get'])
    def clearance_status(self, request, pk=None):
        """Get exit clearance status."""
        resignation = self.get_object()
        engine = ExitManagementEngine(resignation.employee)
        status_data = engine.get_clearance_status(resignation)
        return Response(status_data)

    @action(detail=True, methods=['post'])
    def exit_interview(self, request, pk=None):
        """Create exit interview."""
        resignation = self.get_object()
        is_anonymous = request.data.get('is_anonymous', False)
        engine = ExitManagementEngine(resignation.employee)
        interview = engine.create_exit_interview(resignation, is_anonymous=is_anonymous)
        serializer = ExitInterviewSerializer(interview)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExitClearanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Exit Clearance management."""
    serializer_class = ExitClearanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resignation', 'department_code', 'is_cleared']

    def get_queryset(self):
        return ExitClearance.objects.select_related('resignation__employee', 'cleared_by').all()

    @action(detail=True, methods=['post'])
    def mark_cleared(self, request, pk=None):
        """Mark department clearance as completed."""
        clearance = self.get_object()
        clearance.is_cleared = True
        clearance.cleared_date = timezone.now()
        clearance.cleared_by = request.user
        clearance.comments = request.data.get('comments', '')
        clearance.checklist_items = request.data.get('checklist_items', [])
        clearance.save()
        return Response({'status': f'{clearance.department_name} clearance completed'})


class ExitInterviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Exit Interviews."""
    serializer_class = ExitInterviewSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resignation', 'employee', 'status']

    def get_queryset(self):
        return ExitInterview.objects.select_related('employee', 'interviewed_by', 'resignation').all()

    @action(detail=True, methods=['post'])
    def submit_response(self, request, pk=None):
        """Submit response to an exit interview question."""
        interview = self.get_object()
        response_id = request.data.get('response_id')
        choice_response = request.data.get('choice_response')
        text_response = request.data.get('text_response')
        rating_response = request.data.get('rating_response')

        try:
            response = ExitInterviewResponse.objects.get(id=response_id, interview=interview)
            if choice_response:
                response.choice_response = choice_response
            if text_response:
                response.text_response = text_response
            if rating_response is not None:
                response.rating_response = int(rating_response)
            response.save()
            return Response({'status': 'Response submitted'})
        except ExitInterviewResponse.DoesNotExist:
            return Response({'error': 'Invalid response ID'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark interview as completed."""
        interview = self.get_object()
        interview.status = 'COMPLETED'
        interview.interviewed_by = request.user
        interview.overall_satisfaction = request.data.get('overall_satisfaction')
        interview.rehire_recommendation = request.data.get('rehire_recommendation')
        interview.hr_notes = request.data.get('hr_notes', '')
        interview.save()
        return Response({'status': 'Exit interview completed'})


class FnFSettlementViewSet(viewsets.ModelViewSet):
    """ViewSet for F&F Settlement management."""
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']

    def get_queryset(self):
        return FnFSettlement.objects.select_related('employee', 'prepared_by').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return FnFSettlementListSerializer
        return FnFSettlementSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve F&F settlement."""
        settlement = self.get_object()
        if settlement.status != 'DRAFT':
            return Response({'error': 'Only draft settlements can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        settlement.status = 'PENDING_HR' if request.data.get('skip_hr') else 'PENDING_HR'
        settlement.save()
        return Response({'status': f'Settlement status: {settlement.status}'})

    @action(detail=True, methods=['post'])
    def approve_hr(self, request, pk=None):
        """HR approval for F&F."""
        settlement = self.get_object()
        settlement.status = 'PENDING_FINANCE'
        settlement.approved_by_hr = request.user
        settlement.save()
        return Response({'status': 'HR approved - pending finance'})

    @action(detail=True, methods=['post'])
    def approve_finance(self, request, pk=None):
        """Finance approval - mark as approved."""
        settlement = self.get_object()
        settlement.status = 'APPROVED'
        settlement.approved_by_finance = request.user
        settlement.approved_date = timezone.now()
        settlement.save()
        return Response({'status': 'Finance approved'})

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark settlement as paid."""
        settlement = self.get_object()
        settlement.status = 'PAID'
        settlement.payment_date = timezone.now().date()
        settlement.payment_reference = request.data.get('payment_reference', '')
        settlement.save()
        return Response({'status': 'Settlement marked as paid'})

    @action(detail=True, methods=['get'])
    def generate_experience_letter(self, request, pk=None):
        """Generate experience letter text."""
        settlement = self.get_object()
        engine = ExitManagementEngine(settlement.employee)
        letter = engine.generate_experience_letter(settlement)
        return Response({'letter': letter, 'employee_id': settlement.employee.employee_id})

    @action(detail=True, methods=['get'])
    def download_experience_letter(self, request, pk=None):
        """Download experience letter as PDF."""
        settlement = self.get_object()
        engine = ExitManagementEngine(settlement.employee)
        pdf_bytes = engine.generate_experience_letter_pdf(settlement)
        filename = f"experience_letter_{settlement.employee.employee_id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response

    @action(detail=True, methods=['get'])
    def generate_relieving_letter(self, request, pk=None):
        """Generate relieving letter text."""
        settlement = self.get_object()
        engine = ExitManagementEngine(settlement.employee)
        letter = engine.generate_relieving_letter(settlement)
        return Response({'letter': letter, 'employee_id': settlement.employee.employee_id})

    @action(detail=True, methods=['get'])
    def download_relieving_letter(self, request, pk=None):
        """Download relieving letter as PDF."""
        settlement = self.get_object()
        engine = ExitManagementEngine(settlement.employee)
        pdf_bytes = engine.generate_relieving_letter_pdf(settlement)
        filename = f"relieving_letter_{settlement.employee.employee_id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response


class AlumniRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for Alumni Portal management."""
    serializer_class = AlumniRecordSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_active', 'is_rehire_eligible']

    def get_queryset(self):
        return AlumniRecord.objects.select_related('employee').all()

    @action(detail=False, methods=['get'])
    def expiring_access(self, request):
        """Get alumni with expiring access (within 30 days)."""
        from datetime import date, timedelta
        cutoff = date.today() + timedelta(days=30)
        records = self.get_queryset().filter(
            access_expiry_date__lte=cutoff,
            access_expiry_date__gte=date.today(),
            is_active=True
        )
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)


# ============================================================================
# ESS / MSS PORTAL ENHANCEMENTS
# ============================================================================

class HRTicketViewSet(viewsets.ModelViewSet):
    """ViewSet for HR Helpdesk Tickets."""
    serializer_class = HRTicketSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'ticket_type', 'priority', 'status', 'assigned_to']
    search_fields = ['subject', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return HRTicket.objects.select_related('employee', 'assigned_to').all()
        try:
            emp = user.employee
            return HRTicket.objects.filter(employee=emp)
        except:
            return HRTicket.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(employee=emp)
        except:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def assign(self, request, pk=None):
        """Assign ticket to HR user."""
        ticket = self.get_object()
        assignee_id = request.data.get('assigned_to')
        if assignee_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                ticket.assigned_to = User.objects.get(id=assignee_id)
                ticket.status = 'IN_PROGRESS'
                ticket.save()
                return Response({'status': 'Ticket assigned'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'assigned_to required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_conversation(self, request, pk=None):
        """Add message to ticket."""
        ticket = self.get_object()
        message = request.data.get('message', '')
        is_internal = request.data.get('is_internal', False)
        if message:
            conv = HRTicketConversation.objects.create(
                ticket=ticket,
                user=request.user,
                message=message,
                is_internal=is_internal,
            )
            serializer = HRTicketConversationSerializer(conv)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'message required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def resolve(self, request, pk=None):
        """Mark ticket as resolved."""
        ticket = self.get_object()
        ticket.status = 'RESOLVED'
        ticket.resolved_date = timezone.now()
        ticket.resolution_notes = request.data.get('resolution_notes', '')
        ticket.save()
        return Response({'status': 'Ticket resolved'})

    @action(detail=True, methods=['post'])
    def close_ticket(self, request, pk=None):
        """Close ticket."""
        ticket = self.get_object()
        ticket.status = 'CLOSED'
        ticket.save()
        return Response({'status': 'Ticket closed'})

    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """Get current user's tickets."""
        try:
            emp = request.user.employee
            tickets = HRTicket.objects.filter(employee=emp)
            serializer = HRTicketSerializer(tickets, many=True)
            return Response(serializer.data)
        except:
            return Response([])

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsHRStaff])
    def unassigned(self, request):
        """Get unassigned tickets."""
        tickets = self.get_queryset().filter(assigned_to__isnull=True, status='OPEN')
        serializer = HRTicketSerializer(tickets, many=True)
        return Response(serializer.data)


class AssetRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Asset Requests."""
    serializer_class = AssetRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'asset_type', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return AssetRequest.objects.select_related('employee', 'approved_by').all()
        try:
            emp = user.employee
            return AssetRequest.objects.filter(employee=emp)
        except:
            return AssetRequest.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(employee=emp)
        except:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def approve(self, request, pk=None):
        """Approve asset request."""
        req = self.get_object()
        req.status = 'APPROVED'
        req.approved_by = request.user
        req.save()
        return Response({'status': 'Asset request approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def allocate(self, request, pk=None):
        """Allocate asset with serial number."""
        req = self.get_object()
        req.status = 'ALLOCATED'
        req.asset_serial = request.data.get('asset_serial', '')
        req.allocated_date = timezone.now().date()
        req.save()
        return Response({'status': 'Asset allocated'})

    @action(detail=True, methods=['post'])
    def return_asset(self, request, pk=None):
        """Mark asset as returned."""
        req = self.get_object()
        req.status = 'RETURNED'
        req.returned_date = timezone.now().date()
        req.save()
        return Response({'status': 'Asset returned'})


# ============================================================================
# PERFORMANCE ENHANCEMENTS
# ============================================================================

class AppraisalCycleViewSet(viewsets.ModelViewSet):
    """ViewSet for Appraisal Cycle management."""
    serializer_class = AppraisalCycleSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status']
    search_fields = ['name']

    def get_queryset(self):
        return AppraisalCycle.objects.all()

    @action(detail=True, methods=['post'])
    def close_cycle(self, request, pk=None):
        """Close an active appraisal cycle."""
        cycle = self.get_object()
        cycle.status = 'Closed'
        cycle.end_date = timezone.now().date()
        cycle.save()
        return Response({'status': 'Cycle closed'})


class PerformanceGoalViewSet(viewsets.ModelViewSet):
    """ViewSet for Performance Goals."""
    serializer_class = PerformanceGoalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'cycle', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return PerformanceGoal.objects.select_related('employee', 'cycle').all()
        try:
            emp = user.employee
            return PerformanceGoal.objects.filter(employee=emp)
        except:
            return PerformanceGoal.objects.none()


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Performance Reviews."""
    serializer_class = PerformanceReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'cycle']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return PerformanceReview.objects.select_related('employee', 'cycle').all()
        try:
            emp = user.employee
            return PerformanceReview.objects.filter(employee=emp)
        except:
            return PerformanceReview.objects.none()


class OKRViewSet(viewsets.ModelViewSet):
    """ViewSet for OKR management."""
    serializer_class = OKRSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'cycle', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return OKR.objects.select_related('employee', 'cycle').all()
        try:
            emp = user.employee
            return OKR.objects.filter(employee=emp)
        except:
            return OKR.objects.none()

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update OKR progress percentage."""
        okr = self.get_object()
        progress = request.data.get('progress_pct')
        current_value = request.data.get('current_value')
        if progress is not None:
            okr.progress_pct = Decimal(str(progress))
        if current_value is not None:
            okr.current_value = Decimal(str(current_value))
        if okr.progress_pct >= 100:
            okr.status = 'COMPLETED'
        elif okr.progress_pct >= 75:
            okr.status = 'ON_TRACK'
        elif okr.progress_pct >= 50:
            okr.status = 'AT_RISK'
        else:
            okr.status = 'BEHIND'
        okr.save()
        return Response({'status': f'OKR progress: {okr.progress_pct}%'})

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get OKR dashboard summary."""
        cycle_id = request.query_params.get('cycle_id')
        if not cycle_id:
            return Response({'error': 'cycle_id required'}, status=status.HTTP_400_BAD_REQUEST)
        okrs = self.get_queryset().filter(cycle_id=cycle_id)
        summary = {
            'total': okrs.count(),
            'on_track': okrs.filter(status='ON_TRACK').count(),
            'at_risk': okrs.filter(status='AT_RISK').count(),
            'behind': okrs.filter(status='BEHIND').count(),
            'completed': okrs.filter(status='COMPLETED').count(),
            'avg_progress': okrs.aggregate(avg=Avg('progress_pct'))['avg'] or 0,
        }
        return Response(summary)


class Feedback360ViewSet(viewsets.ModelViewSet):
    """ViewSet for 360° Feedback management."""
    serializer_class = Feedback360Serializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'reviewer', 'cycle', 'relationship', 'is_submitted']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return Feedback360.objects.select_related('employee', 'reviewer', 'cycle').all()
        try:
            emp = user.employee
            return Feedback360.objects.filter(
                Q(employee=emp) | Q(reviewer=emp)
            )
        except:
            return Feedback360.objects.none()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit 360° feedback."""
        feedback = self.get_object()
        feedback.is_submitted = True
        feedback.submitted_date = timezone.now()
        feedback.overall_rating = request.data.get('overall_rating')
        feedback.strengths = request.data.get('strengths', '')
        feedback.areas_for_improvement = request.data.get('areas_for_improvement', '')
        feedback.additional_comments = request.data.get('additional_comments', '')
        feedback.save()
        return Response({'status': 'Feedback submitted'})


class PIPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for Performance Improvement Plans."""
    serializer_class = PIPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return PIPlan.objects.select_related('employee', 'created_by').all()
        try:
            emp = user.employee
            return PIPlan.objects.filter(employee=emp)
        except:
            return PIPlan.objects.none()

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update PIP status."""
        pip = self.get_object()
        new_status = request.data.get('status')
        pip.status = new_status
        pip.outcome_notes = request.data.get('outcome_notes', '')
        pip.manager_checkin_log = request.data.get('checkin_log', '')
        pip.save()
        return Response({'status': f'PIP status: {pip.status}'})


class CalibrationSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for Calibration Sessions."""
    serializer_class = CalibrationSessionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cycle', 'department', 'status']

    def get_queryset(self):
        return CalibrationSession.objects.select_related('cycle', 'department').prefetch_related('participants').all()


# ============================================================================
# TRAINING ENHANCEMENTS
# ============================================================================

class TrainingProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for Training Programs."""
    serializer_class = TrainingProgramSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['training_type']
    search_fields = ['name', 'trainer_name']

    def get_queryset(self):
        return TrainingProgram.objects.all()

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming training programs."""
        from datetime import date
        programs = self.get_queryset().filter(start_date__gte=date.today()).order_by('start_date')
        serializer = self.get_serializer(programs, many=True)
        return Response(serializer.data)


class TrainingNominationViewSet(viewsets.ModelViewSet):
    """ViewSet for Training Nominations."""
    serializer_class = TrainingNominationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['program', 'employee', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return TrainingNomination.objects.select_related('program', 'employee').all()
        try:
            emp = user.employee
            return TrainingNomination.objects.filter(employee=emp)
        except:
            return TrainingNomination.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(employee=emp)
        except:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def approve(self, request, pk=None):
        """Approve nomination."""
        nom = self.get_object()
        nom.status = 'Approved'
        nom.save()
        return Response({'status': 'Nomination approved'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark nomination as completed with score."""
        nom = self.get_object()
        nom.status = 'Completed'
        nom.completion_score = request.data.get('completion_score')
        nom.save()
        return Response({'status': 'Training completed'})


class SkillViewSet(viewsets.ModelViewSet):
    """ViewSet for Skill Master."""
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name']

    def get_queryset(self):
        return Skill.objects.filter(is_active=True)


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Skill Matrix."""
    serializer_class = EmployeeSkillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'skill', 'proficiency', 'is_verified']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeSkill.objects.select_related('employee', 'skill', 'verified_by').all()
        try:
            emp = user.employee
            return EmployeeSkill.objects.filter(employee=emp)
        except:
            return EmployeeSkill.objects.none()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def verify(self, request, pk=None):
        """Verify a skill assessment."""
        skill = self.get_object()
        skill.is_verified = True
        skill.verified_by = request.user
        skill.save()
        return Response({'status': 'Skill verified'})

    @action(detail=False, methods=['get'])
    def skill_gap(self, request):
        """Identify skill gaps across organization."""
        from django.db.models import Q
        dept = request.query_params.get('department')
        skills = EmployeeSkill.objects.all()
        if dept:
            skills = skills.filter(employee__department_id=dept)
        gaps = skills.filter(proficiency__lte=2, is_verified=True)
        serializer = self.get_serializer(gaps, many=True)
        return Response({
            'total_skills': skills.count(),
            'gaps_found': gaps.count(),
            'gaps': serializer.data,
        })


class TrainingNeedViewSet(viewsets.ModelViewSet):
    """ViewSet for Training Need Identification (TNI)."""
    serializer_class = TrainingNeedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'skill', 'need_type', 'priority', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return TrainingNeed.objects.select_related('employee', 'skill').all()
        try:
            emp = user.employee
            return TrainingNeed.objects.filter(employee=emp)
        except:
            return TrainingNeed.objects.none()

    @action(detail=False, methods=['get'])
    def high_priority(self, request):
        """Get high priority training needs."""
        needs = self.get_queryset().filter(priority__in=['HIGH', 'CRITICAL'], status='IDENTIFIED')
        serializer = self.get_serializer(needs, many=True)
        return Response(serializer.data)


class TrainingAssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Training Assessments (Pre/Post)."""
    serializer_class = TrainingAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['nomination', 'assessment_type']

    def get_queryset(self):
        return TrainingAssessment.objects.select_related('nomination__employee', 'nomination__program').all()


class TrainingCostViewSet(viewsets.ModelViewSet):
    """ViewSet for Training Cost tracking."""
    serializer_class = TrainingCostSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['program', 'cost_type', 'paid_by_department']

    def get_queryset(self):
        return TrainingCost.objects.select_related('program', 'paid_by_department').all()


# ============================================================================
# ATTRITION & REPORTS
# ============================================================================

class ReportsViewSet(viewsets.ViewSet):
    """
    Comprehensive Reports & Analytics ViewSet.
    Provides endpoints for CEO dashboard, attrition, headcount, recruitment analytics,
    attendance reports, payroll reports, compliance calendar, and training reports.
    """

    permission_classes = [IsAuthenticated, IsHRStaff]

    # ==========================================================================
    # CEO / CHRO DASHBOARD
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='ceo-dashboard')
    def ceo_dashboard(self, request):
        """CEO/CHRO Dashboard with organizational overview."""
        year = request.query_params.get('year')
        if year:
            year = int(year)
        data = ReportDataAggregator.get_ceo_dashboard(year)
        return Response(data)

    # ==========================================================================
    # ATTRITION ANALYSIS
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def attrition(self, request):
        """Comprehensive attrition analysis."""
        year = request.query_params.get('year')
        if year:
            year = int(year)
        data = ReportDataAggregator.get_attrition_analysis(year)
        return Response(data)

    # ==========================================================================
    # HEADCOUNT REPORTS
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def headcount(self, request):
        """Headcount analysis by department, location, grade, etc."""
        data = ReportDataAggregator.get_headcount_report()
        return Response(data)

    # ==========================================================================
    # RECRUITMENT ANALYTICS
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='recruitment-analytics')
    def recruitment_analytics(self, request):
        """Recruitment funnel analytics and KPIs."""
        year = request.query_params.get('year')
        if year:
            year = int(year)
        data = ReportDataAggregator.get_recruitment_analytics(year)
        return Response(data)

    # ==========================================================================
    # ATTENDANCE REPORTS
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='attendance-report')
    def attendance_report(self, request):
        """Attendance analysis for a given month/year."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if month:
            month = int(month)
        if year:
            year = int(year)
        data = ReportDataAggregator.get_attendance_report(month, year)
        return Response(data)

    # ==========================================================================
    # LEAVE REPORTS
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='leave-report')
    def leave_report(self, request):
        """Leave utilization analysis."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if month:
            month = int(month)
        if year:
            year = int(year)
        data = ReportDataAggregator.get_leave_report(month, year)
        return Response(data)

    # ==========================================================================
    # PAYROLL REPORTS
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='payroll-report')
    def payroll_report(self, request):
        """Payroll cost analysis."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if month:
            month = int(month)
        if year:
            year = int(year)
        data = ReportDataAggregator.get_payroll_report(month, year)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='payroll-variance')
    def payroll_variance(self, request):
        """Month-over-month payroll variance."""
        month = int(request.query_params.get('month', date.today().month))
        year = int(request.query_params.get('year', date.today().year))
        prev_month = request.query_params.get('prev_month')
        prev_year = request.query_params.get('prev_year')
        if prev_month:
            prev_month = int(prev_month)
        if prev_year:
            prev_year = int(prev_year)
        data = ReportDataAggregator.get_payroll_variance_report(month, year, prev_month, prev_year)
        return Response(data)

    # ==========================================================================
    # COMPLIANCE CALENDAR REPORT
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='compliance-report')
    def compliance_report(self, request):
        """Compliance calendar status and risk assessment."""
        year = request.query_params.get('year')
        if year:
            year = int(year)
        data = ReportDataAggregator.get_compliance_calendar_report(year)
        return Response(data)

    # ==========================================================================
    # TRAINING REPORT
    # ==========================================================================

    @action(detail=False, methods=['get'], url_path='training-report')
    def training_report(self, request):
        """Training & development analytics."""
        year = request.query_params.get('year')
        if year:
            year = int(year)
        data = ReportDataAggregator.get_training_report(year)
        return Response(data)

    # ==========================================================================
    # EXPORT
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export report data as CSV."""
        report_type = request.query_params.get('type', 'payroll')
        year = int(request.query_params.get('year', date.today().year))
        month = int(request.query_params.get('month', date.today().month))
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if report_type == 'payroll':
            data = ReportDataAggregator.get_payroll_report(month, year)
            writer.writerow(['Report', 'Value'])
            writer.writerow(['Period', f'{month}/{year}'])
            writer.writerow(['Total Gross', data['total_gross']])
            writer.writerow(['Total Net', data['total_net']])
            writer.writerow(['Total Deductions', data['total_deductions']])
            writer.writerow(['Employee Count', data['employee_count']])
            writer.writerow([])
            writer.writerow(['Department', 'Gross', 'Net', 'Deductions', 'Employees'])
            for d in data['department_cost']:
                writer.writerow([d['employee__department__name'], d['gross'], d['net'], d['deductions'], d['count']])
        elif report_type == 'attrition':
            data = ReportDataAggregator.get_attrition_analysis(year)
            writer.writerow(['Attrition Analysis', 'Value'])
            writer.writerow(['Total Separations', data['total_separations']])
            writer.writerow(['Voluntary', data['voluntary']])
            writer.writerow(['Involuntary', data['involuntary']])
            writer.writerow([])
            writer.writerow(['Department', 'Count'])
            for d in data['by_department']:
                writer.writerow([d['department__name'], d['count']])
        elif report_type == 'headcount':
            data = ReportDataAggregator.get_headcount_report()
            writer.writerow(['Department', 'Headcount'])
            for d in data['by_department']:
                writer.writerow([d['department__name'], d['count']])
        elif report_type == 'recruitment':
            data = ReportDataAggregator.get_recruitment_analytics(year)
            writer.writerow(['Recruitment Analytics', 'Value'])
            writer.writerow(['Total Applications', data['total_applications']])
            writer.writerow(['Total Offers', data['total_offers']])
            writer.writerow(['Offer Acceptance Rate', f"{data['offer_acceptance_rate']}%"])
            writer.writerow(['Avg Days to Fill', data['avg_days_to_fill']])
        else:
            writer.writerow(['Unsupported report type'])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{year}.csv"'
        return response


# ============================================================================
# RECRUITMENT & ONBOARDING ENHANCED VIEWSETS
# ============================================================================

class InternalJobPostingViewSet(viewsets.ModelViewSet):
    """ViewSet for Internal Job Portal (IJP) postings."""
    serializer_class = InternalJobPostingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'designation', 'status', 'employment_type']
    search_fields = ['title', 'description', 'requirements']

    def get_queryset(self):
        return InternalJobPosting.objects.select_related(
            'department', 'designation', 'work_location', 'posted_by'
        ).all()

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """Publish an IJP posting (DRAFT → OPEN)."""
        posting = self.get_object()
        posting.status = 'OPEN'
        posting.save()
        return Response({'status': 'IJP published', 'title': posting.title})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an IJP posting."""
        posting = self.get_object()
        posting.status = 'CLOSED'
        posting.save()
        return Response({'status': 'IJP closed'})

    @action(detail=False, methods=['get'])
    def open_positions(self, request):
        """Get all currently open IJP positions (for employee browsing)."""
        positions = self.get_queryset().filter(status='OPEN', is_active=True)
        serializer = self.get_serializer(positions, many=True)
        return Response(serializer.data)


class InternalJobApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for IJP Applications from existing employees."""
    serializer_class = InternalJobApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['posting', 'applicant', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return InternalJobApplication.objects.select_related('posting', 'applicant').all()
        try:
            emp = user.employee
            return InternalJobApplication.objects.filter(applicant=emp).select_related('posting', 'applicant')
        except Exception:
            return InternalJobApplication.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(applicant=emp)
            # Update posting stats
            posting = emp.posting
            posting.total_applications = InternalJobApplication.objects.filter(posting=posting).count()
            posting.save()
        except Exception:
            serializer.save()

    @action(detail=True, methods=['post'])
    def shortlist(self, request, pk=None):
        """Shortlist an internal applicant."""
        app = self.get_object()
        app.status = 'SHORTLISTED'
        app.save()
        # Update posting stats
        posting = app.posting
        posting.shortlisted_count = InternalJobApplication.objects.filter(posting=posting, status='SHORTLISTED').count()
        posting.save()
        return Response({'status': 'Applicant shortlisted'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an internal applicant."""
        app = self.get_object()
        app.status = 'REJECTED'
        app.save()
        return Response({'status': 'Applicant rejected'})

    @action(detail=True, methods=['post'])
    def manager_endorse(self, request, pk=None):
        """Current manager endorses the internal move."""
        app = self.get_object()
        app.manager_endorsed = request.data.get('endorsed', True)
        app.manager_comment = request.data.get('comment', '')
        app.save()
        return Response({'status': f"Manager endorsement: {app.manager_endorsed}"})


class EmployeeReferralViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Referral Programme."""
    serializer_class = EmployeeReferralSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['referring_employee', 'status', 'bonus_paid', 'requisition']
    search_fields = ['referred_name', 'referred_email']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeReferral.objects.select_related('referring_employee', 'referred_candidate').all()
        try:
            emp = user.employee
            return EmployeeReferral.objects.filter(referring_employee=emp)
        except Exception:
            return EmployeeReferral.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(referring_employee=emp)
        except Exception:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def update_status(self, request, pk=None):
        """Update referral pipeline status."""
        ref = self.get_object()
        ref.status = request.data.get('status', ref.status)
        if request.data.get('bonus_amount'):
            ref.bonus_amount = request.data['bonus_amount']
        if request.data.get('bonus_paid'):
            ref.bonus_paid = True
            ref.bonus_paid_date = timezone.now().date()
        ref.save()
        return Response({'status': f'Referral status: {ref.status}'})

    @action(detail=False, methods=['get'])
    def my_referrals(self, request):
        """Get current user's referrals."""
        try:
            emp = request.user.employee
            refs = EmployeeReferral.objects.filter(referring_employee=emp)
            serializer = self.get_serializer(refs, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get referral programme dashboard stats."""
        from django.db.models import Sum
        total = self.get_queryset().count()
        hired = self.get_queryset().filter(status__in=['HIRED', 'JOINED']).count()
        bonus_total = self.get_queryset().aggregate(total=Sum('bonus_amount'))['total'] or 0
        bonus_paid = self.get_queryset().filter(bonus_paid=True).aggregate(total=Sum('bonus_amount'))['total'] or 0
        return Response({
            'total_referrals': total,
            'hired_count': hired,
            'total_bonus': float(bonus_total),
            'bonus_paid': float(bonus_paid),
            'conversion_rate': round((hired / total * 100) if total > 0 else 0, 1),
        })


class OnboardingBuddyViewSet(viewsets.ModelViewSet):
    """ViewSet for Buddy/Mentor assignments during onboarding."""
    serializer_class = OnboardingBuddySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['new_employee', 'buddy', 'role', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return OnboardingBuddy.objects.select_related('new_employee', 'buddy').all()
        try:
            emp = user.employee
            return OnboardingBuddy.objects.filter(
                Q(new_employee=emp) | Q(buddy=emp)
            ).select_related('new_employee', 'buddy')
        except Exception:
            return OnboardingBuddy.objects.none()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark buddy assignment as completed."""
        buddy = self.get_object()
        buddy.status = 'COMPLETED'
        buddy.end_date = timezone.now().date()
        buddy.buddy_rating = request.data.get('buddy_rating')
        buddy.new_employee_feedback = request.data.get('new_employee_feedback', '')
        buddy.buddy_feedback = request.data.get('buddy_feedback', '')
        buddy.save()
        return Response({'status': 'Buddy assignment completed'})

    @action(detail=False, methods=['get'])
    def active_buddies(self, request):
        """Get active buddy assignments."""
        buddies = self.get_queryset().filter(status='ACTIVE')
        serializer = self.get_serializer(buddies, many=True)
        return Response(serializer.data)


class PreJoiningDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Pre-Joining Document Portal."""
    serializer_class = PreJoiningDocumentSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['candidate', 'offer', 'status', 'welcome_email_sent']
    search_fields = ['candidate__email', 'candidate__first_name']

    def get_queryset(self):
        return PreJoiningDocument.objects.select_related('candidate', 'offer').all()

    @action(detail=True, methods=['post'])
    def send_welcome(self, request, pk=None):
        """Send welcome email with portal access link."""
        portal = self.get_object()
        portal.welcome_email_sent = True
        portal.welcome_email_date = timezone.now()
        portal.save()
        # Trigger welcome email notification
        try:
            from hr.services.notification_service import OnboardingNotification
            OnboardingNotification.send_welcome_email(portal)
        except Exception:
            pass
        return Response({'status': 'Welcome email sent', 'portal_url': f"/candidate-portal/{portal.portal_token}"})

    @action(detail=False, methods=['get'])
    def pending_portals(self, request):
        """Get portals where documents are pending."""
        pending = self.get_queryset().filter(status='PENDING')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def onboarding_completion(self, request):
        """Get overall onboarding document completion stats."""
        all_portals = self.get_queryset()
        total = all_portals.count()
        completed = all_portals.filter(status='VERIFIED').count()
        pending = all_portals.filter(status='PENDING').count()
        return Response({
            'total_candidates': total,
            'documents_completed': completed,
            'documents_pending': pending,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1),
        })


class OnboardingFeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet for Onboarding Feedback surveys (Day 30, 60, 90)."""
    serializer_class = OnboardingFeedbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'feedback_type']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return OnboardingFeedback.objects.select_related('employee').all()
        try:
            emp = user.employee
            return OnboardingFeedback.objects.filter(employee=emp)
        except Exception:
            return OnboardingFeedback.objects.none()

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get onboarding feedback summary."""
        from django.db.models import Avg
        summary = OnboardingFeedback.objects.filter(is_active=True).aggregate(
            avg_satisfaction=Avg('overall_satisfaction'),
            avg_onboarding=Avg('onboarding_process'),
            avg_buddy=Avg('buddy_support'),
            avg_role_clarity=Avg('role_clarity'),
            total_responses=Count('id'),
        )
        return Response(summary)


# ============================================================================
# PMS ENHANCEMENT VIEWSETS: GOAL LIBRARY, RATING SCALES, FORM DESIGNER, BELL CURVE, PROMOTION MATRIX
# ============================================================================

class GoalLibraryViewSet(viewsets.ModelViewSet):
    """ViewSet for pre-built goal library templates."""
    serializer_class = GoalLibrarySerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'designation', 'category', 'goal_type']
    search_fields = ['title', 'description']

    def get_queryset(self):
        return GoalLibrary.objects.select_related('department', 'designation', 'created_by').all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_department(self, request):
        """Get goal templates filtered by department."""
        dept_id = request.query_params.get('department_id')
        goals = self.get_queryset()
        if dept_id:
            goals = goals.filter(Q(department_id=dept_id) | Q(department__isnull=True))
        goals = goals.order_by('category', 'title')
        serializer = self.get_serializer(goals, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all available goal categories with counts."""
        from django.db.models import Count
        cats = GoalLibrary.objects.filter(is_active=True).values('category').annotate(
            count=Count('id')
        ).order_by('category')
        return Response(list(cats))


class RatingScaleViewSet(viewsets.ModelViewSet):
    """ViewSet for configurable rating scales."""
    serializer_class = RatingScaleSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scale_type', 'is_active']

    def get_queryset(self):
        return RatingScale.objects.prefetch_related('options').all()

    def perform_create(self, serializer):
        scale = serializer.save()
        # Auto-create default options if none exist yet
        if scale.scale_type == 'STANDARD_5':
            defaults = [
                (5.0, 'Outstanding', 'Exceptional performance, far exceeds expectations', '#22C55E'),
                (4.0, 'Exceeds Expectations', 'Consistently exceeds role expectations', '#3B82F6'),
                (3.0, 'Meets Expectations', 'Fully meets role expectations', '#F59E0B'),
                (2.0, 'Needs Improvement', 'Partially meets expectations, gaps exist', '#F97316'),
                (1.0, 'Unsatisfactory', 'Does not meet minimum expectations', '#EF4444'),
            ]
            for val, label, desc, color in defaults:
                RatingScaleOption.objects.get_or_create(
                    scale=scale, rating_value=val,
                    defaults={'label': label, 'description': desc, 'color_code': color, 'order': int(6-val)}
                )
        elif scale.scale_type == 'STANDARD_9':
            defaults = [
                (9.0, 'Exceptional', 'Role model performance', '#22C55E'),
                (8.0, 'Excellent', 'Significantly exceeds expectations', '#16A34A'),
                (7.0, 'Strong', 'Exceeds expectations in most areas', '#3B82F6'),
                (6.0, 'Proficient', 'Exceeds expectations in some areas', '#6366F1'),
                (5.0, 'Fully Meets', 'Fully meets all expectations', '#F59E0B'),
                (4.0, 'Meets Most', 'Meets most expectations, minor gaps', '#F97316'),
                (3.0, 'Needs Development', 'Below expectations in several areas', '#DC2626'),
                (2.0, 'Significant Gaps', 'Well below expectations', '#B91C1C'),
                (1.0, 'Unsatisfactory', 'Far below minimum standards', '#991B1B'),
            ]
            for val, label, desc, color in defaults:
                RatingScaleOption.objects.get_or_create(
                    scale=scale, rating_value=val,
                    defaults={'label': label, 'description': desc, 'color_code': color, 'order': int(10-val)}
                )

    @action(detail=True, methods=['post'])
    def add_option(self, request, pk=None):
        """Add a rating option to the scale."""
        scale = self.get_object()
        serializer = RatingScaleOptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(scale=scale)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppraisalFormTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for appraisal form template designer."""
    serializer_class = AppraisalFormTemplateSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['form_type', 'is_published', 'rating_scale']
    search_fields = ['name', 'description']

    def get_queryset(self):
        return AppraisalFormTemplate.objects.select_related('rating_scale', 'created_by').prefetch_related(
            'sections', 'sections__questions'
        ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def add_section(self, request, pk=None):
        """Add a section to the form template."""
        template = self.get_object()
        serializer = AppraisalFormSectionSerializer(data={
            **request.data, 'form_template': template.id
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish form template."""
        template = self.get_object()
        template.is_published = True
        template.save()
        return Response({'status': 'Form template published'})

    @action(detail=True, methods=['get'])
    def structure(self, request, pk=None):
        """Get full structure of the form (sections + questions)."""
        template = self.get_object()
        sections = template.sections.filter(is_active=True).order_by('order')
        data = []
        for sec in sections:
            questions = sec.questions.filter(is_active=True).order_by('order')
            data.append({
                'section': AppraisalFormSectionSerializer(sec).data,
                'questions': AppraisalFormQuestionSerializer(questions, many=True).data,
            })
        return Response({'template_id': template.id, 'name': template.name, 'structure': data})


class AppraisalFormSectionViewSet(viewsets.ModelViewSet):
    """ViewSet for appraisal form sections."""
    serializer_class = AppraisalFormSectionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['form_template']

    def get_queryset(self):
        return AppraisalFormSection.objects.prefetch_related('questions').all()

    @action(detail=True, methods=['post'])
    def add_question(self, request, pk=None):
        """Add a question to this section."""
        section = self.get_object()
        serializer = AppraisalFormQuestionSerializer(data={
            **request.data, 'section': section.id
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppraisalFormQuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for appraisal form questions."""
    serializer_class = AppraisalFormQuestionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['section', 'question_type', 'is_required']

    def get_queryset(self):
        return AppraisalFormQuestion.objects.select_related('section', 'rating_scale').all()


class AppraisalFormResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for appraisal form responses."""
    serializer_class = AppraisalFormResponseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['review', 'question', 'respondent_type', 'is_draft']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return AppraisalFormResponse.objects.select_related('review', 'question', 'respondent').all()
        return AppraisalFormResponse.objects.filter(respondent=user)

    def perform_create(self, serializer):
        serializer.save(respondent=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_submit(self, request):
        """Submit multiple responses at once (for forms)."""
        responses = request.data.get('responses', [])
        review_id = request.data.get('review_id')
        respondent_type = request.data.get('respondent_type', 'SELF')
        created = []
        for item in responses:
            data = {
                'review': review_id,
                'question': item.get('question_id'),
                'respondent': request.user.id,
                'respondent_type': respondent_type,
                'is_draft': False,
            }
            if 'rating_value' in item:
                data['rating_value'] = item['rating_value']
            if 'text_response' in item:
                data['text_response'] = item['text_response']
            if 'choice_response' in item:
                data['choice_response'] = item['choice_response']
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                created.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'submitted': len(created), 'responses': created})


class BellCurveConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for Bell Curve / Forced Ranking configuration."""
    serializer_class = BellCurveConfigSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cycle', 'curve_type', 'is_forced_ranking']

    def get_queryset(self):
        return BellCurveConfig.objects.select_related('cycle').all()

    @action(detail=False, methods=['get'])
    def standard_curves(self, request):
        """Get standard bell curve templates."""
        curves = [
            {
                'name': 'Standard Bell Curve (10-20-40-20-10)',
                'curve_type': 'STANDARD_BELL',
                'distribution': {'5': 10, '4': 20, '3': 40, '2': 20, '1': 10},
                'description': 'Classic bell curve with 10% top performers, 10% bottom performers',
            },
            {
                'name': 'Soft Curve (15-25-30-20-10)',
                'curve_type': 'SKEWED_RIGHT',
                'distribution': {'5': 15, '4': 25, '3': 30, '2': 20, '1': 10},
                'description': 'Slightly skewed towards high performers',
            },
            {
                'name': 'High Performance (20-30-30-15-5)',
                'curve_type': 'SKEWED_RIGHT',
                'distribution': {'5': 20, '4': 30, '3': 30, '2': 15, '1': 5},
                'description': 'Heavy skew towards high performance organization',
            },
            {
                'name': 'Aggressive (5-15-40-25-15)',
                'curve_type': 'SKEWED_LEFT',
                'distribution': {'5': 5, '4': 15, '3': 40, '2': 25, '1': 15},
                'description': 'Strict curve with heavy bottom weighting',
            },
            {
                'name': 'Flat Distribution (20-20-20-20-20)',
                'curve_type': 'FLAT',
                'distribution': {'5': 20, '4': 20, '3': 20, '2': 20, '1': 20},
                'description': 'Equal distribution across all rating levels',
            },
        ]
        return Response(curves)

    @action(detail=True, methods=['get'])
    def simulate(self, request, pk=None):
        """Simulate bell curve distribution for a department."""
        config = self.get_object()
        dept_id = request.query_params.get('department_id')
        from django.db.models import Count
        # Get current ratings for this cycle
        ratings = PerformanceReview.objects.filter(cycle=config.cycle)
        if dept_id:
            ratings = ratings.filter(employee__department_id=dept_id)
        total = ratings.count()
        if total == 0:
            return Response({'error': 'No ratings found for this cycle'}, status=status.HTTP_400_BAD_REQUEST)
        # Current distribution
        current_dist = {}
        for r in ratings:
            rating_key = str(int(r.final_rating)) if r.final_rating else 'UNRATED'
            current_dist[rating_key] = current_dist.get(rating_key, 0) + 1
        # Expected distribution
        expected = {}
        for k, v in config.distribution.items():
            expected[k] = round(total * v / 100)
        return Response({
            'total_employees': total,
            'current_distribution': current_dist,
            'expected_distribution': expected,
            'config': BellCurveConfigSerializer(config).data,
        })


class PromotionMatrixViewSet(viewsets.ModelViewSet):
    """ViewSet for Promotion Matrix (Rating → Increment mapping)."""
    serializer_class = PromotionMatrixSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cycle', 'rating_scale', 'is_active']

    def get_queryset(self):
        return PromotionMatrix.objects.select_related('rating_scale', 'cycle').prefetch_related('rows').all()

    @action(detail=True, methods=['post'])
    def add_row(self, request, pk=None):
        """Add a rating bracket row to the matrix."""
        matrix = self.get_object()
        serializer = PromotionMatrixRowSerializer(data={
            **request.data, 'matrix': matrix.id
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def calculate(self, request, pk=None):
        """Calculate recommended increment for a given rating."""
        matrix = self.get_object()
        rating = request.query_params.get('rating')
        if not rating:
            return Response({'error': 'rating query parameter required'})
        try:
            rating = Decimal(str(rating))
        except:
            return Response({'error': 'Invalid rating value'})
        row = matrix.rows.filter(
            rating_from__lte=rating, rating_to__gte=rating, is_active=True
        ).first()
        if row:
            return Response({
                'rating': float(rating),
                'min_increment_pct': float(row.min_increment_pct),
                'max_increment_pct': float(row.max_increment_pct),
                'promotion_recommended': row.promotion_recommended,
                'promotion_notes': row.promotion_notes,
                'bonus_recommended_pct': float(row.bonus_recommended),
            })
        return Response({'error': 'No matching bracket found for this rating'})


class GoalCascadeViewSet(viewsets.ModelViewSet):
    """ViewSet for Goal Cascade (Company → Dept → Individual)."""
    serializer_class = GoalCascadeSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source_type', 'target_department', 'target_employee', 'cycle']

    def get_queryset(self):
        return GoalCascade.objects.select_related(
            'target_department', 'target_employee', 'aligned_goal', 'cycle', 'created_by'
        ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def alignment_tree(self, request):
        """Get goal alignment visualization data."""
        cycle_id = request.query_params.get('cycle_id')
        cascades = self.get_queryset()
        if cycle_id:
            cascades = cascades.filter(cycle_id=cycle_id)
        # Organize: Company → Department → Employee
        tree = {
            'company_goals': [],
            'department_goals': [],
            'employee_goals': [],
        }
        for c in cascades:
            item = GoalCascadeSerializer(c).data
            if c.source_type == 'COMPANY':
                tree['company_goals'].append(item)
            elif c.source_type == 'DEPARTMENT':
                tree['department_goals'].append(item)
            else:
                tree['employee_goals'].append(item)
        return Response(tree)


class AppraisalCycleStageViewSet(viewsets.ModelViewSet):
    """ViewSet for Appraisal Cycle workflow stages."""
    serializer_class = AppraisalCycleStageSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cycle', 'stage_type', 'status']

    def get_queryset(self):
        return AppraisalCycleStage.objects.select_related('cycle', 'form_template').all()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate this stage."""
        stage = self.get_object()
        stage.status = 'ACTIVE'
        stage.save()
        return Response({'status': f'Stage {stage.get_stage_type_display()} activated'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark this stage as completed."""
        stage = self.get_object()
        stage.status = 'COMPLETED'
        stage.save()
        # Auto-activate next stage if exists
        next_stage = AppraisalCycleStage.objects.filter(
            cycle=stage.cycle, order__gt=stage.order
        ).order_by('order').first()
        if next_stage:
            next_stage.status = 'ACTIVE'
            next_stage.save()
        return Response({'status': f'Stage {stage.get_stage_type_display()} completed'})

    @action(detail=False, methods=['get'])
    def cycle_workflow(self, request):
        """Get the full workflow for a given cycle."""
        cycle_id = request.query_params.get('cycle_id')
        if not cycle_id:
            return Response({'error': 'cycle_id required'})
        stages = self.get_queryset().filter(cycle_id=cycle_id).order_by('order')
        serializer = self.get_serializer(stages, many=True)
        return Response(serializer.data)


# ============================================================================
# POSH (SEXUAL HARASSMENT) MODULE VIEWSETS
# ============================================================================

class POSHInquiryNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for POSH Inquiry Notes (confidential)."""
    serializer_class = POSHInquiryNoteSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['complaint', 'author', 'is_confidential']

    def get_queryset(self):
        return POSHInquiryNote.objects.select_related('complaint', 'author').all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class POSHComplaintViewSet(viewsets.ModelViewSet):
    """ViewSet for POSH Complaint management (confidential)."""
    serializer_class = POSHComplaintSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['complainant', 'respondent', 'complaint_type', 'status']
    search_fields = ['description', 'complainant__first_name', 'respondent__first_name']

    def get_queryset(self):
        user = self.request.user
        # ICC members and HR admins can view all cases
        if user.role in ['Superadmin', 'Admin']:
            return POSHComplaint.objects.select_related('complainant', 'respondent', 'presiding_officer').all()
        # Employees see only complaints they filed or are against them
        try:
            emp = user.employee
            return POSHComplaint.objects.filter(
                Q(complainant=emp) | Q(respondent=emp)
            ).select_related('complainant', 'respondent')
        except Exception:
            return POSHComplaint.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(complainant=emp)
        except Exception:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def submit(self, request, pk=None):
        """Submit a draft complaint for formal processing."""
        complaint = self.get_object()
        complaint.status = 'SUBMITTED'
        complaint.submitted_date = timezone.now()
        complaint.save()
        return Response({'status': 'Complaint submitted to ICC'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def start_inquiry(self, request, pk=None):
        """Start formal ICC inquiry."""
        complaint = self.get_object()
        complaint.status = 'UNDER_INVESTIGATION'
        complaint.inquiry_start_date = timezone.now().date()
        # Assign ICC members
        if request.data.get('icc_members'):
            complaint.icc_members.set(request.data['icc_members'])
        if request.data.get('presiding_officer'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                complaint.presiding_officer = User.objects.get(id=request.data['presiding_officer'])
            except User.DoesNotExist:
                pass
        complaint.save()
        return Response({'status': 'Inquiry started'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def complete_inquiry(self, request, pk=None):
        """Complete ICC inquiry with findings."""
        complaint = self.get_object()
        complaint.status = 'INQUIRY_COMPLETED'
        complaint.inquiry_completed_date = timezone.now().date()
        complaint.inquiry_findings = request.data.get('findings', '')
        complaint.action_taken = request.data.get('action_taken', '')
        complaint.save()
        return Response({'status': 'Inquiry completed. Pending resolution.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def resolve(self, request, pk=None):
        """Resolve a POSH complaint."""
        complaint = self.get_object()
        complaint.status = 'RESOLVED'
        complaint.resolution_date = timezone.now().date()
        complaint.closure_notes = request.data.get('closure_notes', '')
        complaint.save()
        return Response({'status': 'Complaint resolved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def add_inquiry_note(self, request, pk=None):
        """Add confidential inquiry note."""
        complaint = self.get_object()
        note = POSHInquiryNote.objects.create(
            complaint=complaint,
            author=request.user,
            note=request.data.get('note', ''),
            is_confidential=request.data.get('is_confidential', True),
        )
        serializer = POSHInquiryNoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsHRStaff])
    def dashboard(self, request):
        """Get POSH dashboard statistics."""
        total = self.get_queryset().count()
        active = self.get_queryset().filter(status__in=['SUBMITTED', 'UNDER_INVESTIGATION']).count()
        resolved = self.get_queryset().filter(status__in=['RESOLVED', 'CLOSED']).count()
        return Response({
            'total_cases': total,
            'active_cases': active,
            'resolved_cases': resolved,
            'by_type': self.get_queryset().values('complaint_type').annotate(count=Count('id')),
        })


# ============================================================================
# DATA PRIVACY CONSENT (DPDP ACT) VIEWSETS
# ============================================================================

class DataConsentRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for Data Privacy Consent management (DPDP Act/GDPR)."""
    serializer_class = DataConsentRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'consent_type', 'status', 'consent_version']
    search_fields = ['employee__first_name', 'employee__employee_id']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return DataConsentRecord.objects.select_related('employee').all()
        try:
            emp = user.employee
            return DataConsentRecord.objects.filter(employee=emp)
        except Exception:
            return DataConsentRecord.objects.none()

    @action(detail=True, methods=['post'])
    def grant(self, request, pk=None):
        """Grant consent."""
        consent = self.get_object()
        consent.status = 'GRANTED'
        consent.granted_date = timezone.now()
        consent.ip_address = request.META.get('REMOTE_ADDR', '')
        consent.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        consent.save()
        return Response({'status': 'Consent granted'})

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw consent."""
        consent = self.get_object()
        consent.status = 'WITHDRAWN'
        consent.withdrawn_date = timezone.now()
        consent.ip_address = request.META.get('REMOTE_ADDR', '')
        consent.save()
        return Response({'status': 'Consent withdrawn'})

    @action(detail=False, methods=['get'])
    def my_consents(self, request):
        """Get current user's consent records."""
        try:
            emp = request.user.employee
            consents = DataConsentRecord.objects.filter(employee=emp)
            serializer = self.get_serializer(consents, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsHRStaff])
    def compliance_report(self, request):
        """Get consent compliance report."""
        total_employees = Employee.objects.filter(is_active=True).count()
        consented = DataConsentRecord.objects.filter(status='GRANTED').values('employee').distinct().count()
        return Response({
            'total_employees': total_employees,
            'consent_given': consented,
            'consent_pending': total_employees - consented,
            'compliance_pct': round(consented / max(total_employees, 1) * 100, 1),
        })


# ============================================================================
# STAY INTERVIEW VIEWSETS
# ============================================================================

class StayInterviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Stay Interview management (proactive retention)."""
    serializer_class = StayInterviewSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'status', 'retention_risk', 'conducted_by']
    search_fields = ['employee__first_name', 'employee__employee_id']

    def get_queryset(self):
        return StayInterview.objects.select_related('employee', 'conducted_by').all()

    @action(detail=False, methods=['get'])
    def high_risk(self, request):
        """Get high-risk employees from stay interviews."""
        interviews = self.get_queryset().filter(
            retention_risk__in=['HIGH', 'CRITICAL'],
            is_active=True
        ).order_by('-interview_date')
        serializer = self.get_serializer(interviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def retention_summary(self, request):
        """Get retention risk summary."""
        from django.db.models import Count
        summary = self.get_queryset().values('retention_risk').annotate(
            count=Count('id')
        ).order_by('retention_risk')
        return Response(list(summary))


# ============================================================================
# SALARY FREEZE VIEWSETS
# ============================================================================

class SalaryFreezeViewSet(viewsets.ModelViewSet):
    """ViewSet for Salary Freeze management."""
    serializer_class = SalaryFreezeSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'freeze_reason', 'is_active']
    search_fields = ['employee__first_name', 'employee__employee_id', 'description']

    def get_queryset(self):
        return SalaryFreeze.objects.select_related('employee', 'frozen_by', 'unfrozen_by').all()

    def perform_create(self, serializer):
        serializer.save(frozen_by=self.request.user)

    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        """Release a salary freeze."""
        freeze = self.get_object()
        freeze.is_active = False
        freeze.unfrozen_date = timezone.now()
        freeze.unfrozen_by = request.user
        freeze.unfrozen_reason = request.data.get('reason', '')
        freeze.save()
        return Response({'status': 'Salary unfrozen'})

    @action(detail=False, methods=['get'])
    def active_freezes(self, request):
        """Get all currently active salary freezes."""
        freezes = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(freezes, many=True)
        return Response(serializer.data)


# ============================================================================
# BULK SALARY REVISION UPLOAD
# ============================================================================

class BulkSalaryRevisionUploadViewSet(viewsets.ViewSet):
    """
    Bulk upload salary revisions via CSV/Excel.
    """
    permission_classes = [IsAuthenticated, IsHRStaff]

    @action(detail=False, methods=['post'])
    def upload_excel(self, request):
        """
        Bulk upload salary revisions from CSV file.
        Expected columns: employee_id, revised_ctc, revised_gross, revised_basic,
                         effective_month, effective_year, revision_type, reason
        """
        import csv
        import io

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'CSV file is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded_file))
        except Exception as e:
            return Response({'error': f'Invalid file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if not reader.fieldnames:
            return Response({'error': 'File has no headers'}, status=status.HTTP_400_BAD_REQUEST)

        required = ['employee_id', 'revised_ctc']
        missing = [f for f in required if f not in reader.fieldnames]
        if missing:
            return Response({'error': f'Missing required columns: {missing}'}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        errors = []
        for row_num, row in enumerate(reader, start=2):
            try:
                emp = Employee.objects.get(employee_id=row['employee_id'].strip())
                current_salary = EmployeeSalary.objects.filter(
                    employee=emp, is_active=True
                ).order_by('-effective_from').first()

                if not current_salary:
                    errors.append(f'Row {row_num}: No active salary for {row["employee_id"]}')
                    continue

                revised_ctc = Decimal(row['revised_ctc'])
                revised_gross = Decimal(row.get('revised_gross', revised_ctc * Decimal('0.8')))
                revised_basic = Decimal(row.get('revised_basic', revised_gross * Decimal('0.5')))
                effective_month = int(row.get('effective_month', timezone.now().month))
                effective_year = int(row.get('effective_year', timezone.now().year))

                SalaryRevision.objects.create(
                    employee=emp,
                    previous_ctc=current_salary.ctc,
                    previous_gross=current_salary.gross_salary,
                    previous_basic=current_salary.basic_salary,
                    revised_ctc=revised_ctc,
                    revised_gross=revised_gross,
                    revised_basic=revised_basic,
                    effective_month=effective_month,
                    effective_year=effective_year,
                    revision_type=row.get('revision_type', 'ANNUAL_INCREMENT'),
                    reason=row.get('reason', 'Bulk upload'),
                    status='DRAFT',
                )
                created += 1
            except Employee.DoesNotExist:
                errors.append(f'Row {row_num}: Employee {row["employee_id"]} not found')
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')

        return Response({
            'created': created,
            'errors': len(errors),
            'error_details': errors[:50],
            'total': created + len(errors),
        })

