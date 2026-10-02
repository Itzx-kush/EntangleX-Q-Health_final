export const researchActivityTypes=['experiment','prediction','explanation','quantum','session'] as const;
export type ResearchActivityType=typeof researchActivityTypes[number];
export type ResearchHistoryFilter='all'|ResearchActivityType;

export type ResearchMetadataValue=string|number|boolean|null|string[]|number[];
export type ResearchMetadata=Record<string,ResearchMetadataValue>;

export type ResearchActivity={
  id:string;
  user_id:string;
  activity_type:ResearchActivityType;
  title:string;
  status:string|null;
  occurred_at:string;
  route:string;
  reference_id:string|null;
  experiment_id:string|null;
  model_id:string|null;
  dataset_id:string|null;
  method:string|null;
  metadata:ResearchMetadata;
  idempotency_key:string|null;
  created_at:string;
};

export type NewResearchActivity={
  activityType:ResearchActivityType;
  title:string;
  status?:string|null;
  occurredAt?:string;
  route:string;
  referenceId?:string|null;
  experimentId?:string|null;
  modelId?:string|null;
  datasetId?:string|null;
  method?:string|null;
  metadata?:ResearchMetadata;
  idempotencyKey?:string|null;
};

export type ResearchHistoryPage={
  records:ResearchActivity[];
  total:number;
};
