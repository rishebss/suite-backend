from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hr.views import (
    DesignationViewSet, WorkLocationViewSet, CostCenterViewSet,
    ShiftViewSet, EmployeeViewSet, EmployeeDocumentViewSet,
    LeaveTypeViewSet, EmployeeLeaveBalanceViewSet, LeaveApplicationViewSet,
    AttendanceViewSet, CompensatoryOffViewSet, SalaryComponentViewSet,
    SalaryStructureViewSet, EmployeeSalaryViewSet, PayrollViewSet,
    HolidayViewSet,
    SalaryRevisionViewSet, EmployeeLoanViewSet, LoanRepaymentViewSet,
    EmployeeReimbursementViewSet,
    PFConfigurationViewSet, PFContributionViewSet, ESIConfigurationViewSet,
    ESIContributionViewSet, ProfessionalTaxSlabViewSet, PTContributionViewSet,
    TDSConfigurationViewSet, InvestmentDeclarationViewSet, TDSCalculationViewSet,
    GratuityConfigurationViewSet, GratuityCalculationViewSet,
    BonusConfigurationViewSet, BonusCalculationViewSet,
    ComplianceCalendarEntryViewSet,
    LWFConfigurationViewSet, LWFContributionViewSet,
    OvertimeRequestViewSet, ShiftSwapRequestViewSet,
    AttendanceRegularizationRequestViewSet,
    VPFContributionViewSet, PFStatementViewSet, ESICardViewSet,
    LowerDeductionCertificateViewSet, PTEnrollmentViewSet,
    InternationalWorkerViewSet, Form12BAViewSet, Form24QReturnViewSet,
    IPAccessRestrictionViewSet, DataRetentionViewSet
)
from hr.views_extended import (
    GoalLibraryViewSet, RatingScaleViewSet,
    AppraisalFormTemplateViewSet, AppraisalFormSectionViewSet,
    AppraisalFormQuestionViewSet, AppraisalFormResponseViewSet,
    BellCurveConfigViewSet, PromotionMatrixViewSet,
    GoalCascadeViewSet, AppraisalCycleStageViewSet,
    JobRequisitionViewSet, CandidateViewSet, JobApplicationViewSet,
    AppraisalCycleViewSet, PerformanceGoalViewSet, PerformanceReviewViewSet,
    TrainingProgramViewSet, TrainingNominationViewSet,
    ResignationViewSet, ExitClearanceViewSet,
    EmployeeFamilyViewSet, EmployeeEmergencyContactViewSet,
    EmployeeBankAccountViewSet, EmployeeDocumentVersionViewSet,
    ExitInterviewViewSet, FnFSettlementViewSet, AlumniRecordViewSet,
    HRTicketViewSet, AssetRequestViewSet,
    OKRViewSet, Feedback360ViewSet, PIPlanViewSet, CalibrationSessionViewSet,
    SkillViewSet, EmployeeSkillViewSet,
    TrainingNeedViewSet, TrainingAssessmentViewSet, TrainingCostViewSet,
    InterviewScheduleViewSet, OfferLetterViewSet, BGVCheckViewSet,
    OnboardingTaskViewSet, ReportsViewSet,
    InternalJobPostingViewSet, InternalJobApplicationViewSet,
    EmployeeReferralViewSet, OnboardingBuddyViewSet,
    PreJoiningDocumentViewSet, OnboardingFeedbackViewSet,
    POSHComplaintViewSet, POSHInquiryNoteViewSet,
    DataConsentRecordViewSet,
    StayInterviewViewSet,
    SalaryFreezeViewSet,
    BulkSalaryRevisionUploadViewSet,
)

router = DefaultRouter()

# Master Data Routers
router.register(r'designations', DesignationViewSet, basename='designation')
router.register(r'work-locations', WorkLocationViewSet, basename='work-location')
router.register(r'cost-centers', CostCenterViewSet, basename='cost-center')
router.register(r'shifts', ShiftViewSet, basename='shift')

# Employee Management
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'employee-documents', EmployeeDocumentViewSet, basename='employee-document')

# Attendance & Leave
router.register(r'leave-types', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-balances', EmployeeLeaveBalanceViewSet, basename='leave-balance')
router.register(r'leave-applications', LeaveApplicationViewSet, basename='leave-application')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'comp-offs', CompensatoryOffViewSet, basename='comp-off')

# Payroll
router.register(r'salary-components', SalaryComponentViewSet, basename='salary-component')
router.register(r'salary-structures', SalaryStructureViewSet, basename='salary-structure')
router.register(r'employee-salary', EmployeeSalaryViewSet, basename='employee-salary')
router.register(r'payroll', PayrollViewSet, basename='payroll')

# Others
router.register(r'holidays', HolidayViewSet, basename='holiday')

# Payroll Enhancements
router.register(r'salary-revisions', SalaryRevisionViewSet, basename='salary-revision')
router.register(r'employee-loans', EmployeeLoanViewSet, basename='employee-loan')
router.register(r'loan-repayments', LoanRepaymentViewSet, basename='loan-repayment')
router.register(r'reimbursements', EmployeeReimbursementViewSet, basename='reimbursement')

# Statutory Compliance
router.register(r'pf-configurations', PFConfigurationViewSet, basename='pf-configuration')
router.register(r'pf-contributions', PFContributionViewSet, basename='pf-contribution')
router.register(r'esi-configurations', ESIConfigurationViewSet, basename='esi-configuration')
router.register(r'esi-contributions', ESIContributionViewSet, basename='esi-contribution')
router.register(r'professional-tax-slabs', ProfessionalTaxSlabViewSet, basename='professional-tax-slab')
router.register(r'pt-deductions', PTContributionViewSet, basename='pt-deduction')
router.register(r'tds-configurations', TDSConfigurationViewSet, basename='tds-configuration')
router.register(r'investment-declarations', InvestmentDeclarationViewSet, basename='investment-declaration')
router.register(r'tds-calculations', TDSCalculationViewSet, basename='tds-calculation')
router.register(r'gratuity-configurations', GratuityConfigurationViewSet, basename='gratuity-configuration')
router.register(r'gratuity-calculations', GratuityCalculationViewSet, basename='gratuity-calculation')
router.register(r'bonus-configurations', BonusConfigurationViewSet, basename='bonus-configuration')
router.register(r'bonus-calculations', BonusCalculationViewSet, basename='bonus-calculation')
router.register(r'compliance-calendar', ComplianceCalendarEntryViewSet, basename='compliance-calendar')

# Core HR Enhancements
router.register(r'employee-family', EmployeeFamilyViewSet, basename='employee-family')
router.register(r'emergency-contacts', EmployeeEmergencyContactViewSet, basename='employee-emergency-contact')
router.register(r'employee-bank-accounts', EmployeeBankAccountViewSet, basename='employee-bank-account')
router.register(r'document-versions', EmployeeDocumentVersionViewSet, basename='employee-document-version')

# Recruitment
router.register(r'job-requisitions', JobRequisitionViewSet, basename='job-requisition')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'job-applications', JobApplicationViewSet, basename='job-application')
router.register(r'interview-schedules', InterviewScheduleViewSet, basename='interview-schedule')
router.register(r'offer-letters', OfferLetterViewSet, basename='offer-letter')
router.register(r'bgv-checks', BGVCheckViewSet, basename='bgv-check')
router.register(r'onboarding-tasks', OnboardingTaskViewSet, basename='onboarding-task')

# Recruitment Enhancements: IJP, Referral, Pre-Joining, Buddy
router.register(r'internal-job-postings', InternalJobPostingViewSet, basename='internal-job-posting')
router.register(r'internal-job-applications', InternalJobApplicationViewSet, basename='internal-job-application')
router.register(r'employee-referrals', EmployeeReferralViewSet, basename='employee-referral')
router.register(r'onboarding-buddies', OnboardingBuddyViewSet, basename='onboarding-buddy')
router.register(r'pre-joining-documents', PreJoiningDocumentViewSet, basename='pre-joining-document')
router.register(r'onboarding-feedbacks', OnboardingFeedbackViewSet, basename='onboarding-feedback')

# Performance (PMS)
router.register(r'appraisal-cycles', AppraisalCycleViewSet, basename='appraisal-cycle')
router.register(r'performance-goals', PerformanceGoalViewSet, basename='performance-goal')
router.register(r'performance-reviews', PerformanceReviewViewSet, basename='performance-review')
router.register(r'okrs', OKRViewSet, basename='okr')
router.register(r'feedback-360', Feedback360ViewSet, basename='feedback-360')
router.register(r'pip-plans', PIPlanViewSet, basename='pip-plan')
router.register(r'calibration-sessions', CalibrationSessionViewSet, basename='calibration-session')

# Training (L&D)
router.register(r'training-programs', TrainingProgramViewSet, basename='training-program')
router.register(r'training-nominations', TrainingNominationViewSet, basename='training-nomination')
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'employee-skills', EmployeeSkillViewSet, basename='employee-skill')
router.register(r'training-needs', TrainingNeedViewSet, basename='training-need')
router.register(r'training-assessments', TrainingAssessmentViewSet, basename='training-assessment')
router.register(r'training-costs', TrainingCostViewSet, basename='training-cost')

# Exit Management
router.register(r'resignations', ResignationViewSet, basename='resignation')
router.register(r'exit-clearances', ExitClearanceViewSet, basename='exit-clearance')
router.register(r'exit-interviews', ExitInterviewViewSet, basename='exit-interview')
router.register(r'fnf-settlements', FnFSettlementViewSet, basename='fnf-settlement')
router.register(r'alumni-records', AlumniRecordViewSet, basename='alumni-record')

# ESS / MSS Portal
router.register(r'hr-tickets', HRTicketViewSet, basename='hr-ticket')
router.register(r'asset-requests', AssetRequestViewSet, basename='asset-request')

# Reports & Analytics
router.register(r'reports', ReportsViewSet, basename='report')

# Labour Welfare Fund
router.register(r'lwf-configurations', LWFConfigurationViewSet, basename='lwf-configuration')
router.register(r'lwf-contributions', LWFContributionViewSet, basename='lwf-contribution')

# Overtime & Shift Management
router.register(r'overtime-requests', OvertimeRequestViewSet, basename='overtime-request')
router.register(r'shift-swap-requests', ShiftSwapRequestViewSet, basename='shift-swap-request')

# Attendance Regularization
router.register(r'attendance-regularization', AttendanceRegularizationRequestViewSet, basename='attendance-regularization')

# Statutory Compliance Forms
router.register(r'vpf-contributions', VPFContributionViewSet, basename='vpf-contribution')
router.register(r'pf-statements', PFStatementViewSet, basename='pf-statement')
router.register(r'esi-cards', ESICardViewSet, basename='esi-card')
router.register(r'lower-deduction-certificates', LowerDeductionCertificateViewSet, basename='lower-deduction-certificate')
router.register(r'pt-enrollments', PTEnrollmentViewSet, basename='pt-enrollment')
router.register(r'international-workers', InternationalWorkerViewSet, basename='international-worker')
router.register(r'form-12ba', Form12BAViewSet, basename='form-12ba')
router.register(r'form-24q-returns', Form24QReturnViewSet, basename='form-24q-return')

# Data Security
router.register(r'ip-access-restrictions', IPAccessRestrictionViewSet, basename='ip-access-restriction')
router.register(r'data-retention', DataRetentionViewSet, basename='data-retention')


app_name = 'hr'

# PMS Enhancement: Goal Library, Rating Scales, Form Designer
router.register(r'goal-library', GoalLibraryViewSet, basename='goal-library')
router.register(r'rating-scales', RatingScaleViewSet, basename='rating-scale')
router.register(r'appraisal-form-templates', AppraisalFormTemplateViewSet, basename='appraisal-form-template')
router.register(r'appraisal-form-sections', AppraisalFormSectionViewSet, basename='appraisal-form-section')
router.register(r'appraisal-form-questions', AppraisalFormQuestionViewSet, basename='appraisal-form-question')
router.register(r'appraisal-form-responses', AppraisalFormResponseViewSet, basename='appraisal-form-response')
router.register(r'bell-curve-configs', BellCurveConfigViewSet, basename='bell-curve-config')
router.register(r'promotion-matrices', PromotionMatrixViewSet, basename='promotion-matrix')
router.register(r'goal-cascades', GoalCascadeViewSet, basename='goal-cascade')
router.register(r'appraisal-cycle-stages', AppraisalCycleStageViewSet, basename='appraisal-cycle-stage')

# POSH Module
router.register(r'posh-complaints', POSHComplaintViewSet, basename='posh-complaint')
router.register(r'posh-inquiry-notes', POSHInquiryNoteViewSet, basename='posh-inquiry-note')

# Data Privacy Consent (DPDP Act)
router.register(r'data-consents', DataConsentRecordViewSet, basename='data-consent')

# Stay Interviews
router.register(r'stay-interviews', StayInterviewViewSet, basename='stay-interview')

# Salary Freeze
router.register(r'salary-freezes', SalaryFreezeViewSet, basename='salary-freeze')

# Bulk Salary Revision Upload
router.register(r'bulk-salary-revisions', BulkSalaryRevisionUploadViewSet, basename='bulk-salary-revision')

urlpatterns = [
    path('', include(router.urls)),
]

