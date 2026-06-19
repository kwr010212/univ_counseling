from django.contrib import admin
from .models import Question, Quote, AnalysisLog

admin.site.register(Question)
admin.site.register(Quote)
admin.site.register(AnalysisLog)