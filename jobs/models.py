from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone
from django.utils.html import format_html
# Create your models here.

class EmailJob(models.Model):
    TRIGGER_TYPE = (
        ('d', '时间类型(一次执行)'),
        ('i', '循环类型(多次执行)'),
        ('c', '任意类型')
    )
    job_name = models.CharField('任务名称', max_length=100)
    created_date = models.DateTimeField('创建时间', default=timezone.now)
    #Trigger
    trigger_type = models.CharField('触发类型', max_length=1, choices=TRIGGER_TYPE)
    trigger_value = models.CharField('触发时间', max_length=100)
    #DB
    conn_str = models.CharField('目标数据库连接', max_length=100)
    #Email
    smtp_server = models.CharField('发送邮件服务器(SMTP)', default='smtp.cq.sgcc.com.cn', max_length=50)
    # smtp_ssl = models.BooleanField('发送邮件服务器是否加密(SSL)', default = False)
    smtp_port = models.IntegerField('发送邮件服务器端口', default=25)
    sender = models.EmailField('发送人邮件地址')
    sender_pass = models.CharField('发送人邮件密码', max_length=50)
    subject = models.CharField('发送邮件主题', max_length=200)
    content = models.TextField('发送邮件内容', max_length=500 , null=True, blank=True)
    to_email = models.CharField('接收人邮件地址', max_length=250)
    status = models.BooleanField('状态', default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='users')

    def user_name_property(self):
        return self.user.first_name + ' ' + self.user.last_name
    user_name_property.short_description = '用户'
    full_name = property(user_name_property)

    
    class Meta:
        verbose_name = 'Email任务详情'
        verbose_name_plural = 'Email任务列表'

    def __str__(self):
        return self.job_name


class ScriptFile(models.Model):
    script_file = models.FileField('数据库脚本', upload_to='scripts/%Y%m%d%H%M%S/')
    email_job = models.ForeignKey(EmailJob, on_delete=models.CASCADE, related_name='email_jobs')

    class Meta:
        verbose_name = '执行脚本'
        verbose_name_plural = '执行脚本'