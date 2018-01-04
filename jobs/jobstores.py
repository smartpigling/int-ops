import logging
import pickle
from apscheduler import events
from apscheduler.events import JobExecutionEvent, JobSubmissionEvent
from apscheduler.job import Job
from apscheduler.jobstores.base import BaseJobStore, ConflictingIdError, JobLookupError
from apscheduler.schedulers.base import BaseScheduler

from django.core.exceptions import ObjectDoesNotExist
from django.db import connections

from .models import DjangoJob
from .result_storage import DjangoResultStorage
from .util import deserialize_dt, serialize_dt

LOGGER = logging.getLogger("django_apscheduler")


class DjangoJobStore(BaseJobStore):
    """
    Stores jobs in a Django database.
    :param int pickle_protocol: pickle protocol level to use (for serialization), defaults to the
        highest available
    """

    def __init__(self, pickle_protocol=pickle.HIGHEST_PROTOCOL):
        super(DjangoJobStore, self).__init__()
        self.pickle_protocol = pickle_protocol

    def lookup_job(self, job_id):
        try:
            job_state = DjangoJob.objects.get(name=job_id).job_state
        except DjangoJob.DoesNotExist:
            return None
        return self._reconstitute_job(job_state) if job_state else None

    def get_due_jobs(self, now):
        try:
            return self._get_jobs(next_run_time__lte=serialize_dt(now))
        except:
            logging.exception("")

    def get_next_run_time(self):
        try:
            return deserialize_dt(DjangoJob.objects.first().next_run_time)
        except AttributeError:  # no active jobs
            return None

    def get_all_jobs(self):
        jobs = self._get_jobs()
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def add_job(self, job):
        if DjangoJob.objects.filter(
            name=job.id
        ).exists():
            raise ConflictingIdError(job.id)

        DjangoJob.objects.create(
            name=job.id,
            next_run_time=serialize_dt(job.next_run_time),
            job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol)
        )


    def update_job(self, job):
        updated = DjangoJob.objects.filter(name=job.id).update(
            next_run_time=serialize_dt(job.next_run_time),
            job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol)
        )
        if updated == 0:
            raise JobLookupError(job.id)

    def remove_job(self, job_id):
        deleted, _ = DjangoJob.objects.filter(name=job_id).delete()
        if deleted == 0:
            raise JobLookupError(job_id)

    def remove_all_jobs(self):
        with connections["default"].cursor() as c:
            c.execute("""
                DELETE FROM django_apscheduler_djangojobexecution;
                DELETE FROM django_apscheduler_djangojob
            """)

    def _reconstitute_job(self, job_state):
        job_state = pickle.loads(job_state)
        job_state['jobstore'] = self
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _get_jobs(self, **filters):
        job_states = DjangoJob.objects.filter(**filters).values_list('id', 'job_state')
        jobs = []
        failed_job_ids = set()
        for job_id, job_state in job_states:
            try:
                jobs.append(self._reconstitute_job(job_state))
            except:
                self._logger.exception('Unable to restore job "%s" -- removing it', job_id)
                failed_job_ids.add(job_id)

        # Remove all the jobs we failed to restore
        DjangoJob.objects.filter(name__in=failed_job_ids).delete()

        def map_jobs(job):
            job.next_run_time = deserialize_dt(job.next_run_time)
            return job

        return list(map(map_jobs, jobs))


def event_name(code):
    for key in dir(events):
        if getattr(events, key) == code:
            return key


class _EventManager(object):

    LOGGER = LOGGER.getChild("events")

    def __init__(self, storage=None):
        self.storage = storage or DjangoResultStorage()

    def __call__(self, event):
        # print event, type(event), event.__dict__
        try:
            if isinstance(event, JobSubmissionEvent):
                self._process_submission_event(event)
            elif isinstance(event, JobExecutionEvent):
                self._process_execution_event(event)
        except Exception as e:
            self.LOGGER.exception(str(e))

    def _process_submission_event(self, event):
        # type: (JobSubmissionEvent)->None

        try:
            job = DjangoJob.objects.get(name=event.job_id)
        except ObjectDoesNotExist:
            self.LOGGER.warning("Job with id %s not found in database", event.job_id)
            return

        self.storage.get_or_create_job_execution(job, event)

    def _process_execution_event(self, event):
        # type: (JobExecutionEvent)->None

        try:
            job = DjangoJob.objects.get(name=event.job_id)
        except ObjectDoesNotExist:
            self.LOGGER.warning("Job with id %s not found in database", event.job_id)
            return

        self.storage.register_job_executed(job, event)


def register_events(scheduler, result_storage=None):
    scheduler.add_listener(_EventManager(result_storage))


def register_job(scheduler, *a, **k):
    # type: (BaseScheduler)->callable

    def inner(func):
        k.setdefault("id", "{}.{}".format(func.__module__, func.__name__))
        scheduler.add_job(func, *a, **k)
        return func

    return inner
