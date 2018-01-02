from django.contrib import admin

# Register your models here.
from .models import EmailJob, ScriptFile


def make_start(modeladmin, request, queryset):
    queryset.update(status=True)
make_start.short_description = '启动任务'

class ScriptInline(admin.StackedInline):
    model = ScriptFile
    extra = 1


@admin.register(EmailJob)
class EmailJobAdmin(admin.ModelAdmin):
    list_display = ('job_name', 'created_date', 'full_name', 'status')
    exclude = ('created_date',)
    search_fields = ('job_name',)

    inlines = (ScriptInline,)
    actions = (make_start,)

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)