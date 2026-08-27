from rest_framework import serializers
from .models import (
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
    InternalJobPosting, InternalJobApplication, EmployeeReferral,
    OnboardingBuddy, PreJoiningDocument, OnboardingFeedback,
    POSHComplaint, POSHInquiryNote,
    DataConsentRecord,
    StayInterview,
    SalaryFreeze,
)


# ============================================================================
# CORE HR ENHANCEMENTS
# ============================================================================

class EmployeeFamilySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = EmployeeFamily
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeEmergencyContactSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = EmployeeEmergencyContact
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeBankAccountSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = EmployeeBankAccount
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_ifsc_code(self, value):
        import re
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', value):
            raise serializers.ValidationError('Invalid IFSC code format')
        return value


class EmployeeDocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)

    class Meta:
        model = EmployeeDocumentVersion
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_date', 'created_at']


# ============================================================================
# RECRUITMENT ENHANCEMENTS
# ============================================================================

class JobRequisitionSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = JobRequisition
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'requested_by']


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Normalize email to lowercase
        if 'email' in validated_data:
            validated_data['email'] = validated_data['email'].lower().strip()
        return super().create(validated_data)


class JobApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.first_name', read_only=True)
    candidate_first_name = serializers.CharField(source='candidate.first_name', read_only=True)
    candidate_last_name = serializers.CharField(source='candidate.last_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    candidate_phone = serializers.CharField(source='candidate.phone', read_only=True)
    candidate_source = serializers.CharField(source='candidate.source', read_only=True)
    candidate_experience_years = serializers.DecimalField(source='candidate.experience_years', read_only=True, max_digits=4, decimal_places=1)
    requisition_title = serializers.CharField(source='requisition.designation.name', read_only=True)
    requisition_department = serializers.CharField(source='requisition.department.name', read_only=True)

    class Meta:
        model = JobApplication
        fields = '__all__'
        read_only_fields = ['id', 'applied_on', 'created_at', 'updated_at']


class InterviewScheduleSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='application.candidate.first_name', read_only=True)
    candidate_email = serializers.CharField(source='application.candidate.email', read_only=True)
    interviewer_names = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSchedule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_interviewer_names(self, obj):
        return [u.get_full_name() for u in obj.interviewers.all()]


class OfferLetterSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.first_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)

    class Meta:
        model = OfferLetter
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BGVCheckSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.first_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)

    class Meta:
        model = BGVCheck
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class OnboardingTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True)

    class Meta:
        model = OnboardingTask
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# EXIT MANAGEMENT ENHANCEMENTS
# ============================================================================

class ResignationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = Resignation
        fields = '__all__'
        read_only_fields = ['id', 'submitted_on', 'created_at', 'updated_at']


class ExitClearanceSerializer(serializers.ModelSerializer):
    department_name_display = serializers.SerializerMethodField()
    cleared_by_name = serializers.CharField(source='cleared_by.get_full_name', read_only=True)

    class Meta:
        model = ExitClearance
        fields = '__all__'
        read_only_fields = ['id', 'cleared_date', 'created_at', 'updated_at']

    def get_department_name_display(self, obj):
        return obj.get_department_code_display()


class ExitInterviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    interviewed_by_name = serializers.CharField(source='interviewed_by.get_full_name', read_only=True)

    class Meta:
        model = ExitInterview
        fields = '__all__'
        read_only_fields = ['id', 'interview_date', 'created_at', 'updated_at']


class ExitInterviewResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitInterviewResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class FnFSettlementSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = FnFSettlement
        fields = '__all__'
        read_only_fields = ['id', 'total_earnings', 'total_deductions', 'net_settlement',
                           'created_at', 'updated_at']


class FnFSettlementComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FnFSettlementComponent
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class FnFSettlementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing F&F settlements."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = FnFSettlement
        fields = ['id', 'employee', 'employee_name', 'employee_id_field', 'exit_date',
                  'total_earnings', 'total_deductions', 'net_settlement', 'status',
                  'created_at']


class AlumniRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = AlumniRecord
        fields = '__all__'
        read_only_fields = ['id', 'last_access_date', 'created_at', 'updated_at']


# ============================================================================
# ESS / MSS PORTAL ENHANCEMENTS
# ============================================================================

class HRTicketSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)

    class Meta:
        model = HRTicket
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class HRTicketConversationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = HRTicketConversation
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class AssetRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = AssetRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# PERFORMANCE ENHANCEMENTS
# ============================================================================

class AppraisalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalCycle
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceGoalSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = PerformanceGoal
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = PerformanceReview
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class OKRSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = OKR
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class Feedback360Serializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)

    class Meta:
        model = Feedback360
        fields = '__all__'
        read_only_fields = ['id', 'submitted_date', 'created_at', 'updated_at']

    def validate(self, data):
        # Prevent self-feedback if not self type
        if data.get('relationship') != 'SELF' and data.get('employee') == data.get('reviewer'):
            raise serializers.ValidationError("Cannot submit feedback for yourself unless relationship is 'Self'")
        return data


class PIPlanSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = PIPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CalibrationSessionSerializer(serializers.ModelSerializer):
    participant_names = serializers.SerializerMethodField()

    class Meta:
        model = CalibrationSession
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_participant_names(self, obj):
        return [u.get_full_name() for u in obj.participants.all()]


# ============================================================================
# TRAINING ENHANCEMENTS
# ============================================================================

class TrainingProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingProgram
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingNominationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)

    class Meta:
        model = TrainingNomination
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSkillSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_category = serializers.CharField(source='skill.category', read_only=True)
    proficiency_label = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeSkill
        fields = '__all__'
        read_only_fields = ['id', 'last_assessed_date', 'created_at', 'updated_at']

    def get_proficiency_label(self, obj):
        labels = {1: 'Beginner', 2: 'Intermediate', 3: 'Advanced', 4: 'Expert', 5: 'Thought Leader'}
        return labels.get(obj.proficiency, 'Unknown')


class TrainingNeedSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    skill_name = serializers.CharField(source='skill.name', read_only=True)

    class Meta:
        model = TrainingNeed
        fields = '__all__'
        read_only_fields = ['id', 'gap', 'created_at', 'updated_at']


class TrainingAssessmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='nomination.employee.get_full_name', read_only=True)

    class Meta:
        model = TrainingAssessment
        fields = '__all__'
        read_only_fields = ['id', 'assessed_date', 'created_at']


class TrainingCostSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)

    class Meta:
        model = TrainingCost
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# RECRUITMENT & ONBOARDING ENHANCED SERIALIZERS
# ============================================================================

class InternalJobPostingSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    location_name = serializers.CharField(source='work_location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.get_full_name', read_only=True)
    class Meta:
        model = InternalJobPosting
        fields = '__all__'
        read_only_fields = ['id', 'posting_date', 'total_applications', 'shortlisted_count', 'created_at', 'updated_at']


class InternalJobApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    applicant_id_field = serializers.CharField(source='applicant.employee_id', read_only=True)
    posting_title = serializers.CharField(source='posting.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = InternalJobApplication
        fields = '__all__'
        read_only_fields = ['id', 'applied_date', 'created_at', 'updated_at']


class EmployeeReferralSerializer(serializers.ModelSerializer):
    referring_employee_name = serializers.CharField(source='referring_employee.get_full_name', read_only=True)
    referring_employee_id_field = serializers.CharField(source='referring_employee.employee_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = EmployeeReferral
        fields = '__all__'
        read_only_fields = ['id', 'referral_date', 'bonus_paid', 'bonus_paid_date', 'created_at', 'updated_at']


class OnboardingBuddySerializer(serializers.ModelSerializer):
    new_employee_name = serializers.CharField(source='new_employee.get_full_name', read_only=True)
    new_employee_id_field = serializers.CharField(source='new_employee.employee_id', read_only=True)
    buddy_name = serializers.CharField(source='buddy.get_full_name', read_only=True)
    buddy_id_field = serializers.CharField(source='buddy.employee_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    class Meta:
        model = OnboardingBuddy
        fields = '__all__'
        read_only_fields = ['id', 'assigned_date', 'created_at', 'updated_at']


class PreJoiningDocumentSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.first_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    portal_url = serializers.SerializerMethodField()
    class Meta:
        model = PreJoiningDocument
        fields = '__all__'
        read_only_fields = ['id', 'portal_token', 'last_activity', 'documents_uploaded',
                           'welcome_email_sent', 'welcome_email_date', 'created_at', 'updated_at']
    def get_portal_url(self, obj):
        from django.conf import settings
        base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        return f"{base}/candidate-portal/{obj.portal_token}"


class OnboardingFeedbackSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    feedback_type_display = serializers.CharField(source='get_feedback_type_display', read_only=True)
    class Meta:
        model = OnboardingFeedback
        fields = '__all__'
        read_only_fields = ['id', 'submitted_date', 'created_at', 'updated_at']


# ============================================================================
# PMS ENHANCEMENT SERIALIZERS: GOAL LIBRARY, RATING SCALES, FORM DESIGNER, BELL CURVE, PROMOTION MATRIX
# ============================================================================

class GoalLibrarySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    class Meta:
        model = GoalLibrary
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RatingScaleOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingScaleOption
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class RatingScaleSerializer(serializers.ModelSerializer):
    options = RatingScaleOptionSerializer(many=True, read_only=True, source='options')
    scale_type_display = serializers.CharField(source='get_scale_type_display', read_only=True)
    class Meta:
        model = RatingScale
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppraisalFormQuestionSerializer(serializers.ModelSerializer):
    question_type_display = serializers.CharField(source='get_question_type_display', read_only=True)
    class Meta:
        model = AppraisalFormQuestion
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppraisalFormSectionSerializer(serializers.ModelSerializer):
    questions = AppraisalFormQuestionSerializer(many=True, read_only=True, source='questions')
    class Meta:
        model = AppraisalFormSection
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppraisalFormTemplateSerializer(serializers.ModelSerializer):
    sections = AppraisalFormSectionSerializer(many=True, read_only=True, source='sections')
    form_type_display = serializers.CharField(source='get_form_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    class Meta:
        model = AppraisalFormTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppraisalFormResponseSerializer(serializers.ModelSerializer):
    respondent_name = serializers.CharField(source='respondent.get_full_name', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    class Meta:
        model = AppraisalFormResponse
        fields = '__all__'
        read_only_fields = ['id', 'submitted_date', 'created_at']


class BellCurveConfigSerializer(serializers.ModelSerializer):
    curve_type_display = serializers.CharField(source='get_curve_type_display', read_only=True)
    class Meta:
        model = BellCurveConfig
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PromotionMatrixRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionMatrixRow
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class PromotionMatrixSerializer(serializers.ModelSerializer):
    rows = PromotionMatrixRowSerializer(many=True, read_only=True, source='rows')
    rating_scale_name = serializers.CharField(source='rating_scale.name', read_only=True)
    class Meta:
        model = PromotionMatrix
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class GoalCascadeSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    target_department_name = serializers.CharField(source='target_department.name', read_only=True)
    target_employee_name = serializers.CharField(source='target_employee.get_full_name', read_only=True)
    aligned_goal_text = serializers.CharField(source='aligned_goal.description', read_only=True)
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    class Meta:
        model = GoalCascade
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppraisalCycleStageSerializer(serializers.ModelSerializer):
    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    form_template_name = serializers.CharField(source='form_template.name', read_only=True)
    class Meta:
        model = AppraisalCycleStage
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# POSH (SEXUAL HARASSMENT) SERIALIZERS
# ============================================================================

class POSHComplaintSerializer(serializers.ModelSerializer):
    complainant_name = serializers.CharField(source='complainant.get_full_name', read_only=True)
    respondent_name = serializers.CharField(source='respondent.get_full_name', read_only=True)
    presiding_officer_name = serializers.CharField(source='presiding_officer.get_full_name', read_only=True)
    complaint_type_display = serializers.CharField(source='get_complaint_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = POSHComplaint
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class POSHInquiryNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = POSHInquiryNote
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ============================================================================
# DATA PRIVACY CONSENT SERIALIZERS
# ============================================================================

class DataConsentRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    consent_type_display = serializers.CharField(source='get_consent_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DataConsentRecord
        fields = '__all__'
        read_only_fields = ['id', 'consent_date', 'created_at', 'updated_at']


# ============================================================================
# STAY INTERVIEW SERIALIZERS
# ============================================================================

class StayInterviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    conducted_by_name = serializers.CharField(source='conducted_by.get_full_name', read_only=True)

    class Meta:
        model = StayInterview
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SALARY FREEZE SERIALIZERS
# ============================================================================

class SalaryFreezeSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    frozen_by_name = serializers.CharField(source='frozen_by.get_full_name', read_only=True)
    unfrozen_by_name = serializers.CharField(source='unfrozen_by.get_full_name', read_only=True)
    freeze_reason_display = serializers.CharField(source='get_freeze_reason_display', read_only=True)

    class Meta:
        model = SalaryFreeze
        fields = '__all__'
        read_only_fields = ['id', 'frozen_date', 'created_at', 'updated_at']

