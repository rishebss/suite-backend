with open('hr/models.py', 'a') as f:
    f.write('''
# ==========================================
# RECRUITMENT & ONBOARDING MODELS
# ==========================================

class JobRequisition(Main):
    """Job Requisition Form (JRF)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='requisitions_raised')
    vacancies = models.PositiveIntegerField()
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')])
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Closed', 'Closed')], default='Pending')
    justification = models.TextField()
    budget_allocated = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Job Requisition'
        verbose_name_plural = 'Job Requisitions'
        ordering = ['-created_at']

class Candidate(Main):
    """Candidate Database for ATS"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/%Y/%m/', null=True, blank=True)
    source = models.CharField(max_length=50, null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    class Meta:
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

class JobApplication(Main):
    """ATS Pipeline for a Candidate"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    requisition = models.ForeignKey(JobRequisition, on_delete=models.CASCADE, related_name='applications')
    stage = models.CharField(max_length=50, choices=[
        ('Applied', 'Applied'), ('Screening', 'Screening'), ('L1_Interview', 'L1 Interview'),
        ('L2_Interview', 'L2 Interview'), ('HR_Round', 'HR Round'), ('Offered', 'Offered'),
        ('Accepted', 'Accepted'), ('Rejected', 'Rejected')
    ], default='Applied')
    applied_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Job Application'
        verbose_name_plural = 'Job Applications'

# ==========================================
# PERFORMANCE MANAGEMENT SYSTEM (PMS)
# ==========================================

class AppraisalCycle(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # e.g. FY 2025-26 Annual Appraisal
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Closed', 'Closed')])
    
    class Meta:
        verbose_name = 'Appraisal Cycle'
        verbose_name_plural = 'Appraisal Cycles'

class PerformanceGoal(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='goals')
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    description = models.TextField()
    weightage = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    status = models.CharField(max_length=20, default='Pending')

class PerformanceReview(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    self_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    manager_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    final_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    manager_comments = models.TextField(null=True, blank=True)

# ==========================================
# TRAINING & DEVELOPMENT (L&D)
# ==========================================

class TrainingProgram(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    training_type = models.CharField(max_length=50, choices=[('Internal', 'Internal'), ('External', 'External'), ('Online', 'Online')])
    start_date = models.DateField()
    end_date = models.DateField()
    trainer_name = models.CharField(max_length=100, null=True, blank=True)

class TrainingNomination(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Nominated', 'Nominated'), ('Approved', 'Approved'), ('Completed', 'Completed'), ('Failed', 'Failed')])
    completion_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

# ==========================================
# EXIT MANAGEMENT
# ==========================================

class Resignation(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='resignations')
    submitted_on = models.DateField(auto_now_add=True)
    reason = models.TextField()
    requested_last_working_day = models.DateField()
    approved_last_working_day = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Withdrawn', 'Withdrawn')])

class ExitClearance(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    is_cleared = models.BooleanField(default=False)
    comments = models.TextField(null=True, blank=True)
''')
