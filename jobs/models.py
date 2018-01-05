import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe
# Create your models here.


class DjangoJob(models.Model):
    name = models.CharField('任务名称', max_length=255, unique=True)  # id of job
    next_run_time = models.DateTimeField('执行时间', db_index=True)
    # Perhaps consider using PickleField down the track.
    job_state = models.BinaryField()

    def __str__(self):
        status = '执行时间: %s' % self.next_run_time if self.next_run_time else '暂停'
        return '%s (%s)' % (self.name, status)

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '启动列表'
        ordering = ('next_run_time', )


class DjangoJobExecution(models.Model):
    ADDED = u"Added"
    SENT = u"Started execution"
    MAX_INSTANCES = u"Max instances reached!"
    MISSED = u"Missed!"
    MODIFIED = u"Modified!"
    REMOVED = u"Removed!"
    ERROR = u"Error!"
    SUCCESS = u"Executed"

    job = models.ForeignKey(DjangoJob, verbose_name='任务', on_delete=models.CASCADE)
    status = models.CharField('状态', max_length=50, choices=[
        [x, x]
        for x in [ADDED, SENT, MAX_INSTANCES, MISSED, MODIFIED,
                  REMOVED, ERROR, SUCCESS]
    ])
    run_time = models.DateTimeField('运行时间', db_index=True)
    duration = models.DecimalField('平均时长', max_digits=15, decimal_places=2,
                                   default=None, null=True)

    started = models.DecimalField('开始时间', max_digits=15, decimal_places=2,
                                  default=None, null=True)
    finished = models.DecimalField('结束时间', max_digits=15, decimal_places=2,
                                   default=None, null=True)

    exception = models.CharField('错误描述', max_length=1000, null=True)
    traceback = models.TextField('错误回溯', null=True)

    def html_status(self):
        m = {
            self.ADDED: "RoyalBlue",
            self.SENT: "SkyBlue",
            self.MAX_INSTANCES: "yellow",
            self.MISSED: "yellow",
            self.MODIFIED: "yellow",
            self.REMOVED: "red",
            self.ERROR: "red",
            self.SUCCESS: "green"
        }

        return mark_safe("<p style=\"color: {}\">{}</p>".format(
            m[self.status],
            self.status
        ))
    html_status.short_description = '状态'

    def __unicode__(self):
        return "Execution id={}, status={}, job={}".format(
            self.id, self.status, self.job
        )

    class Meta:
        ordering = ('-run_time', )
        verbose_name = '记录'
        verbose_name_plural = '执行记录'


class EmailJob(models.Model):

    TRIGGER_TYPE = (
        ('date', '时间类型(仅执行一次)'),
        # ('interval', '循环类型(指定时间间隔周期执行)'),
        ('cron', 'cron风格(周期性执行)')
    )
    name = models.CharField('任务名称', max_length=255, unique=True)  # id of job
    # next_run_time = models.DateTimeField('执行时间', db_index=True)
    created_date = models.DateTimeField('创建时间', default=timezone.now)
    #Trigger
    trigger_type = models.CharField('触发类型', max_length=10, choices=TRIGGER_TYPE)
    trigger_value = models.CharField('触发参数', max_length=100, null=True, blank=True, help_text="""
        <strong>cron风格(周期性执行)参数:</strong><br/>
        &nbsp;&nbsp;&nbsp;&nbsp; year (int|str) – 4-digit year<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; month (int|str) – month (1-12)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; day (int|str) – day of the (1-31)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; week (int|str) – ISO week (1-53)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; day_of_week (int|str) – number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; hour (int|str) – hour (0-23)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; minute (int|str) – minute (0-59)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp; second (int|str) – second (0-59)<br/>
    """)
    #DB
    conn_str = models.CharField('目标数据库连接', max_length=100)
    #Email
    smtp_server = models.CharField('发送邮件服务器(SMTP)', default='smtp.cq.sgcc.com.cn', max_length=50)
    # smtp_ssl = models.BooleanField('发送邮件服务器是否加密(SSL)', default = False)
    smtp_port = models.IntegerField('发送邮件服务器端口', default=25)
    sender = models.EmailField('发送人邮件地址', default='@cq.sgcc.com.cn')
    sender_pass = models.CharField('发送人邮件密码', max_length=50)
    subject = models.CharField('发送邮件主题', max_length=200)
    content = models.TextField('发送邮件内容', max_length=500 , null=True, blank=True)
    to_email = models.CharField('接收人邮件地址', max_length=250)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='users')

    def user_name_property(self):
        return '%s(%s)' % (self.user.get_full_name(), self.user.username)
    user_name_property.short_description = '创建人'
    full_name = property(user_name_property)

    
    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务设置'
        ordering = ('created_date', )

    def __str__(self):
        return self.name


class ScriptFile(models.Model):
    script_file = models.FileField('数据库脚本', upload_to='scripts/%Y%m%d%H%M%S/')
    email_job = models.ForeignKey(EmailJob, on_delete=models.CASCADE, related_name='script_files')

    class Meta:
        verbose_name = '执行脚本'
        verbose_name_plural = '执行脚本'

    def __str__(self):
        return os.path.split(str(self.script_file))[-1]