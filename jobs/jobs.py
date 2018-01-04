# -*- coding: utf-8 -*-
import os
import time
import sys
import xlwt
import smtplib
import json
import logging
# import cx_Oracle
from datetime import datetime
from django.db import connections
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
from email.mime.application import MIMEApplication 
from apscheduler.schedulers.background import BackgroundScheduler
from int_ops.settings import BASE_DIR
from .jobstores import DjangoJobStore, register_events, register_job
from .models import EmailJob

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")

register_events(scheduler)

scheduler.start()
LOGGER = logging.getLogger("jobs")


def exp_oracle_script_job(job):

    _exp_dir = 'exports/%s' % datetime.now().strftime('%Y%m%d%H%M%S')

    files = job.script_files.all()

    try:
        # tns_name = cx_Oracle.makedsn('ip','port','sid')
        # conn = cx_Oracle.connect('username','password', tns_name)

        conn = connections["default"]

        for f in files:
            try:
                f_name, f_ext = os.path.splitext(str(f.script_file))
                cursor = conn.cursor()
                cursor.execute(f.read())
                fields = cursor.description
                results = cursor.fetchall()

                workbook = xlwt.Workbook()
                sheet = workbook.add_sheet(f_name,cell_overwrite_ok=True)
                for field in range(0, len(fields)):
                    sheet.write(0, field, fields[field][0])

                for row in range(1,len(results)+1):
                    for col in range(0,len(fields)):
                        sheet.write(row, col, u'%s' % results[row-1][col])        
                workbook.save(os.path.join(os.path.join(BASE_DIR, _exp_dir), '%s.xls' % f_name))
            except (Exception) as e:
                LOGGER.error('The Script [%s] Error: %s' % (f_name, e))
            finally:
                cursor.close()
    except (Exception) as e:
        LOGGER.error('The DB Conn Error: %s' % e)
    else:
        msg = MIMEMultipart()
        for file_name in os.listdir(os.path.join(os.path.join(BASE_DIR, _exp_dir))):
            if file_name.find('.xls') == -1:
                continue
            exp_file = os.path.join(os.path.join(os.path.join(BASE_DIR, _exp_dir), file_name))
            #xlsx类型附件 
            att = MIMEText(open(exp_file,'rb').read(),'base64','gb2312')
            att["Content-Type"] = 'application/octet-stream'
            att["Content-Disposition"] = 'attachment;filename=%s' % file_name
            msg.attach(att) 

        body = MIMEText(job.content)
        msg.attach(body)

        msg['Accept-Language'] = 'zh-CN'
        msg['Accept-Charset'] = 'ISO-8859-1,utf-8'
        msg['Subject'] = job.subject
        msg['From'] = job.sender
        msg['To'] = job.to_email
        try:
            server = smtplib.SMTP_SSL(job.smtp_server, job.smtp_port)
            server.login(job.sender, job.sender_pass)
            server.send_message(msg)
            server.close()       
        except (Exception) as e:
            LOGGER.error('The Email Send Error: %s' % e)
    finally:
        conn.close()

