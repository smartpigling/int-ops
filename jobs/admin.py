import os
import json
import datetime
from django.contrib import admin
from django.db import models
from django import forms
# Register your models here.
from .models import EmailJob, ScriptFile, DjangoJob, DjangoJobExecution
from django.db.models import Avg
from django.utils.timezone import now
from .jobs import scheduler, exp_oracle_script_job



admin.site.site_header = '内部运维系统'
admin.site.site_title = '内部运维系统'

class EmailJobForm(forms.ModelForm):

    class Meta:
        model = EmailJob
        exclude = ['created_date', 'user']
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
    list_display = ('name', 'next_run_time_sec', 'average_duration', 'full_name',)
    search_fields = ('name',)
    form = EmailJobForm

    inlines = (ScriptInline,)
    actions = ('start_job',)


    def get_queryset(self, request):
        self._durations = {
            item[0]: item[1]
            for item in DjangoJobExecution.objects.filter(
                status=DjangoJobExecution.SUCCESS,
                run_time__gte=now() - datetime.timedelta(days=2)
            ).values_list('job').annotate(duration=Avg('duration'))
        }
        return super().get_queryset(request)

    def next_run_time_sec(self, obj):
        return obj.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
    next_run_time_sec.short_description = '执行时间'

    def average_duration(self, obj):
        return self._durations.get(obj.id) or 0
    average_duration.short_description = '两日内平均执行时长(S)'    

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)

    def start_job(self, request, queryset):
        for obj in queryset:
            kwargs = {}
            if obj.trigger_type == 'cron':
                kwargs.update(json.loads(obj.trigger_value))
            scheduler.add_job(exp_oracle_script_job, 
                                obj.trigger_type, 
                                id=obj.name, 
                                next_run_time=obj.next_run_time
                                **kwargs)


    start_job.short_description = '启动任务'

    formfield_overrides = {
        models.CharField: {'widget': forms.TextInput(attrs={'size': '100'})},
    }



def execute_now(ma, r, qs):
    for item in qs:
        item.next_run_time = now()
        item.save()


execute_now.short_description = "Force tasks to execute right now"


@admin.register(DjangoJobExecution)
class DjangoJobExecutionAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "html_status", "run_time_sec", "duration"]

    list_filter = ["job__name", "run_time", "status"]

    list_per_page = 50  

    def run_time_sec(self, obj):
        return obj.run_time.strftime("%Y-%m-%d %H:%M:%S")
    run_time_sec.short_description = '运行时间'

    def get_queryset(self, request):
        return super(DjangoJobExecutionAdmin, self).get_queryset(
            request
        ).select_related("job")
 
    