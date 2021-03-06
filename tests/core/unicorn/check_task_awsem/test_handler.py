from core.check_task_awsem import service
from ..conftest import valid_env
import pytest
import boto3
import random
import string


@pytest.fixture()
def check_task_input():
    return {"config": {"log_bucket": "tibanna-output"},
            "jobid": "test_job",
            "push_error_to_end": True
            }


@pytest.fixture()
def s3(check_task_input):
    bucket_name = check_task_input['config']['log_bucket']
    return boto3.resource('s3').Bucket(bucket_name)


@valid_env
@pytest.mark.webtest
def test_check_task_awsem_fails_if_no_job_started(check_task_input, s3):
    # ensure there is no job started
    jobid = 'notmyjobid'
    check_task_input_modified = check_task_input
    check_task_input_modified['jobid'] = jobid
    job_started = "%s.job_started" % jobid
    s3.delete_objects(Delete={'Objects': [{'Key': job_started}]})
    with pytest.raises(service.EC2StartingException) as excinfo:
        service.handler(check_task_input_modified, '')

    assert 'Failed to find jobid' in str(excinfo.value)


@valid_env
@pytest.mark.webtest
def test_check_task_awsem_fails_if_job_error_found(check_task_input, s3):
    jobid = 'hahaha'
    check_task_input_modified = check_task_input
    check_task_input_modified['jobid'] = jobid
    job_started = "%s.job_started" % jobid
    s3.put_object(Body=b'', Key=job_started)
    job_error = "%s.error" % jobid
    s3.put_object(Body=b'', Key=job_error)
    res = service.handler(check_task_input_modified, '')
    assert ('error' in res)
    s3.delete_objects(Delete={'Objects': [{'Key': job_started}]})
    s3.delete_objects(Delete={'Objects': [{'Key': job_error}]})


@valid_env
@pytest.mark.webtest
def test_check_task_awsem_throws_exception_if_not_done(check_task_input):
    with pytest.raises(service.StillRunningException) as excinfo:
        service.handler(check_task_input, '')

    assert 'still running' in str(excinfo.value)
    assert 'error' not in check_task_input


@valid_env
@pytest.mark.webtest
def test_check_task_awsem(check_task_input, s3):
    jobid = 'lalala'
    check_task_input_modified = check_task_input
    check_task_input_modified['jobid'] = jobid
    job_started = "%s.job_started" % jobid
    s3.put_object(Body=b'', Key=job_started)
    job_success = "%s.success" % jobid
    s3.put_object(Body=b'', Key=job_success)
    postrunjson = "%s.postrun.json" % jobid
    s3.put_object(Body=b'{"test":"test"}', Key=postrunjson)
    retval = service.handler(check_task_input_modified, '')
    s3.delete_objects(Delete={'Objects': [{'Key': job_started}]})
    s3.delete_objects(Delete={'Objects': [{'Key': job_success}]})
    s3.delete_objects(Delete={'Objects': [{'Key': postrunjson}]})
    assert 'postrunjson' in retval
    assert retval['postrunjson'] == {"test": "test"}
    del retval['postrunjson']
    assert retval == check_task_input_modified


@valid_env
@pytest.mark.webtest
def test_check_task_awsem_with_long_postrunjson(check_task_input, s3):
    jobid = 'some_uniq_jobid'
    check_task_input_modified = check_task_input
    check_task_input_modified['jobid'] = jobid
    job_started = "%s.job_started" % jobid
    s3.put_object(Body=b'', Key=job_started)
    job_success = "%s.success" % jobid
    s3.put_object(Body=b'', Key=job_success)
    postrunjson = "%s.postrun.json" % jobid
    verylongstring = ''.join(random.choice(string.ascii_uppercase) for _ in range(50000))
    s3.put_object(Body=b'{"test": "' + verylongstring + '", "Job": {"Output": {}}}', Key=postrunjson)
    retval = service.handler(check_task_input_modified, '')
    s3.delete_objects(Delete={'Objects': [{'Key': job_started}]})
    s3.delete_objects(Delete={'Objects': [{'Key': job_success}]})
    s3.delete_objects(Delete={'Objects': [{'Key': postrunjson}]})
    assert 'postrunjson' in retval
    assert 'Job' in retval['postrunjson']
    assert 'Output' in retval['postrunjson']['Job']
    assert 'log' in retval['postrunjson']
    assert retval['postrunjson']['log'] == "postrun json not included due to data size limit"
    del retval['postrunjson']
    assert retval == check_task_input_modified
