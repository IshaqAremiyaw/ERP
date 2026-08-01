from django.contrib import admin
from .models import (
    User, ApplicantProfile, HRProfile, JobPosting,
    Application, ApplicationStatusHistory, Interview, Employee,
)

admin.site.register(User)
admin.site.register(ApplicantProfile)
admin.site.register(HRProfile)
admin.site.register(JobPosting)
admin.site.register(Application)
admin.site.register(ApplicationStatusHistory)
admin.site.register(Interview)
admin.site.register(Employee)
