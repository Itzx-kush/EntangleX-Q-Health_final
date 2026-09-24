import {describe,expect,it} from 'vitest';

describe('dataset registration metadata payload',()=>{
 it('normalizes metadata fields that arrive as JSON strings',()=>{
  const metadata={metadata_sources:'{"target_source":"inspection.target_candidates[0]"}',metadata_suggestions:'{"target":"target"}',metadata_warnings:'["review target"]'} as Record<string,unknown>;
  for(const key of ['metadata_sources','metadata_suggestions','metadata_warnings']){
   if(typeof metadata[key]==='string') metadata[key]=JSON.parse(metadata[key] as string);
  }
  expect(metadata.metadata_sources).toEqual({target_source:'inspection.target_candidates[0]'});
  expect(metadata.metadata_suggestions).toEqual({target:'target'});
  expect(metadata.metadata_warnings).toEqual(['review target']);
 });
});
