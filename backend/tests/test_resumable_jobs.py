from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import inspect
from app.database import engine, session_scope
from app.jobs.engine import (acquire_lease, begin_logical_unit, complete_logical_unit, create_checkpoint,
    heartbeat, latest_valid_checkpoint, mark_paused, recover_stale_jobs, request_cancel, request_pause, transition_job)
from app.storage.entities import Experiment, Job, JobCheckpoint
from app.utils.errors import AppError
from app.utils.serialization import fingerprint, utcnow

def make_job(registered, *, status="queued", total_units=3):
    with session_scope() as session:
        experiment = Experiment(id=str(uuid4()), dataset_id=registered.id, name=f"Resumable test {uuid4()}", status=status, config={}, summary={})
        session.add(experiment); session.flush()
        job = Job(id=str(uuid4()), experiment_id=experiment.id, status=status, job_type="test", total_units=total_units,
            configuration_fingerprint=fingerprint({"config": 1}), input_fingerprint=fingerprint({"input": 1}))
        session.add(job); session.flush(); return job.id

def state(n): return {"phase": "test", "completed_logical_units": [f"unit:{i}" for i in range(n)]}

def test_invalid_terminal_transition(registered):
    jid=make_job(registered,status="succeeded")
    with session_scope() as session:
        with pytest.raises(AppError): transition_job(session, session.get(Job,jid), "running")

def test_atomic_lease_conflict_and_heartbeat(registered):
    jid=make_job(registered); lease,job=acquire_lease(jid,"worker-a"); assert job.attempt_count==1
    with pytest.raises(AppError): acquire_lease(jid,"worker-b")
    assert heartbeat(jid,lease).last_heartbeat_at is not None

def test_checkpoint_ordering_corruption_and_fallback(registered):
    jid=make_job(registered); lease,_=acquire_lease(jid,"worker-a")
    first=create_checkpoint(jid,lease,state(0),checkpoint_type="phase_completion",completed_units=0)
    begin_logical_unit(jid,"unit:0"); complete_logical_unit(jid,"unit:0")
    second=create_checkpoint(jid,lease,state(1),completed_units=1)
    assert second.sequence_number==first.sequence_number+1
    with session_scope() as session: session.get(JobCheckpoint,second.id).checkpoint_state={"tampered":True}
    assert latest_valid_checkpoint(jid).id==first.id

def test_fingerprint_mismatch_invalidates_checkpoint(registered):
    jid=make_job(registered); lease,_=acquire_lease(jid,"worker-a")
    cp=create_checkpoint(jid,lease,state(0),checkpoint_type="manual",completed_units=0)
    with session_scope() as session: session.get(Job,jid).configuration_fingerprint=fingerprint({"config":2})
    assert latest_valid_checkpoint(jid) is None
    with session_scope() as session: assert session.get(JobCheckpoint,cp.id).status=="invalid"

def test_logical_unit_is_idempotent(registered):
    jid=make_job(registered); unit,done=begin_logical_unit(jid,"phase:unit:1"); assert not done
    complete_logical_unit(jid,"phase:unit:1",result_fingerprint=fingerprint({"result":1}))
    same,done=begin_logical_unit(jid,"phase:unit:1"); assert done and same.id==unit.id

def test_pause_requires_checkpoint(registered):
    jid=make_job(registered); lease,_=acquire_lease(jid,"worker-a"); request_pause(jid)
    with pytest.raises(AppError): mark_paused(jid,lease)
    create_checkpoint(jid,lease,state(0),checkpoint_type="manual",completed_units=0)
    assert mark_paused(jid,lease).status=="paused"; assert request_pause(jid).status=="paused"

def test_cancel_is_idempotent(registered):
    jid=make_job(registered); assert request_cancel(jid).status==request_cancel(jid).status=="cancel_requested"

def test_expired_worker_becomes_recoverable(registered):
    jid=make_job(registered); acquire_lease(jid,"lost")
    with session_scope() as session: session.get(Job,jid).lease_expires_at=utcnow()-timedelta(seconds=1)
    assert jid in recover_stale_jobs()
    with session_scope() as session:
        job=session.get(Job,jid); assert job.status=="recoverable" and job.lease_id is None

def test_unknown_progress_is_indeterminate(client, registered):
    jid=make_job(registered,total_units=None); data=client.get(f"/api/jobs/{jid}/progress").json()
    assert data["determinate"] is False and data["percentage"] is None

def test_migration_tables_present():
    assert {"job_checkpoints","job_execution_units","job_events"} <= set(inspect(engine).get_table_names())
    cols={c["name"] for c in inspect(engine).get_columns("jobs")}
    assert {"job_type","lease_id","current_checkpoint_id","configuration_fingerprint","input_fingerprint"} <= cols
