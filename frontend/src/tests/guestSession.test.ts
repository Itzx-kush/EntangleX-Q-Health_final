import {beforeEach,describe,expect,it} from 'vitest';
import {defaultDraft} from '../hooks/useDraft';
import {
  ACTIVE_GUEST_SESSION_KEY,
  createGuestMigration,
  ensureActiveGuestSession,
  guestMigrationActivity,
  inspectMigratableGuestState,
  readGuestMigration,
  writeGuestMigration,
} from '../auth/guestSession';

describe('guest-to-account research continuity',()=>{
  beforeEach(()=>{
    localStorage.clear();
    sessionStorage.clear();
  });

  it('does not inspect unrelated browser storage without an active guest session',()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({...defaultDraft,dataset_id:'dataset-1'}));
    expect(inspectMigratableGuestState('/training')).toBeNull();
  });

  it('does not create a migration for an untouched default draft',()=>{
    ensureActiveGuestSession();
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify(defaultDraft));
    expect(createGuestMigration('/training')).toBeNull();
  });

  it('captures bounded reference metadata without raw feature names',()=>{
    sessionStorage.setItem(ACTIVE_GUEST_SESSION_KEY,'guest-session-1');
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({
      ...defaultDraft,
      dataset_id:'dataset-1',
      features:['private-feature-a','private-feature-b'],
      models:['qsvc'],
      pipeline:{...defaultDraft.pipeline,log_features:['private-feature-a']},
    }));

    const snapshot=createGuestMigration('/training?step=models');
    expect(snapshot).toMatchObject({
      migrationId:'guest-session-1',
      status:'pending',
      destination:'/training?step=models',
      datasetId:'dataset-1',
    });
    expect(snapshot?.metadata).toMatchObject({
      source:'guest_session',
      selected_feature_count:2,
      log_feature_count:1,
      models:['qsvc'],
    });
    expect(JSON.stringify(snapshot)).not.toContain('private-feature');
  });

  it('uses a stable per-session idempotency key and safely resumes interrupted imports',()=>{
    sessionStorage.setItem(ACTIVE_GUEST_SESSION_KEY,'guest-session-2');
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({...defaultDraft,dataset_id:'dataset-2'}));
    const snapshot=createGuestMigration('/datasets');
    expect(snapshot).not.toBeNull();
    expect(guestMigrationActivity(snapshot!).idempotencyKey).toBe('guest-session:guest-session-2');

    writeGuestMigration({...snapshot!,status:'importing'});
    expect(readGuestMigration()?.status).toBe('pending');
    expect(createGuestMigration('/quantum')?.migrationId).toBe('guest-session-2');
  });
});