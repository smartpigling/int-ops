import datetime
from django.contrib import admin
from django.db import models
from django import forms
# Register your models here.
from .models import EmailJob, ScriptFile, DjangoJob, DjangoJobExecution
from django.db.models import Avg
from django.utils.timezone import now


class EmailJobForm(forms.ModelForm):

    class Meta:
        model = EmailJob
        exclude = ['created_date', 'user', 'status']
        widgets = {
            'sender_pass' : forms.PasswordInput()
        }

    # error_messages = {
    #     'job_name': {
    #         'max_length': "名字长度应在15个字符以内",
    #     },
    # }



class ScriptInline(admin.StackedInline):
    model = ScriptFile
    extra = 1


@admin.register(EmailJob)
class EmailJobAdmin(admin.ModelAdmin):
    list_display = ('job_name', 'created_date', 'full_name', 'status')
    # exclude = ('created_date', 'user', 'status')
    search_fields = ('job_name',)
    form = EmailJobForm

    inlines = (ScriptInline,)
    actions = ('start_email_job',)

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)

    def start_email_job(self, request, queryset):

        # scheduler.add_job(test_email_job, 'interval', seconds=1, id='test_email_job')

        queryset.update(status=True)

    start_email_job.short_description = '启动任务'

    formfield_overrides = {
        models.CharField: {'widget': forms.TextInput(attrs={'size': '100'})},
    }



def execute_now(ma, r, qs):
    for item in qs:
        item.next_run_time = now()
        item.save()


execute_now.short_description = "Force tasks to execute right now"


@admin.register(DjangoJob)
class DjangoJobAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "next_run_time_sec", "average_duration"]
    actions = []

    def get_queryset(self, request):
        self._durations = {
            item[0]: item[1]
            for item in DjangoJobExecution.objects.filter(
                status=DjangoJobExecution.SUCCESS,
                run_time__gte=now() - datetime.timedelta(days=2)
            ).values_list("job").annotate(duration=Avg("duration"))
        }
        return super(DjangoJobAdmin, self).get_queryset(request)

    def next_run_time_sec(self, obj):
        return obj.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

    def average_duration(self, obj):
        return self._durations.get(obj.id) or 0


@admin.register(DjangoJobExecution)
class DjangoJobExecutionAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "html_status", "run_time_sec", "duration"]

    list_filter = ["job__name", "run_time", "status"]

    def run_time_sec(self, obj):
        return obj.run_time.strftime("%Y-%m-%d %H:%M:%S")

    def get_queryset(self, request):
        return super(DjangoJobExecutionAdmin, self).get_queryset(
            request
        ).select_related("job")
    