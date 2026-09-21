import {useEffect, useRef, useState} from 'react';
import {api} from '../services/api';
import type {Preview} from '../types';
import {useDraft} from './ExperimentDraft';
import {useAction} from './useLoad';
export function usePreview(endpoint = '/preprocessing/preview') {
  const {draft} = useDraft(); const [preview, setPreview] = useState<Preview>(); const action = useAction();
  const signature = JSON.stringify(draft); const latest = useRef(signature); latest.current = signature;
  useEffect(() => setPreview(undefined), [signature]);
  async function refresh() {
    const sent = signature;
    const result = await action.run(() => api.post<Preview>(endpoint, draft));
    if (result && latest.current === sent) setPreview(result);
  }
  return {...action, preview, refresh};
}
