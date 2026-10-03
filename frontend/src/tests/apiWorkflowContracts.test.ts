import {afterEach,describe,expect,it,vi} from 'vitest';
import {ApiError,ApiTransportError,qh} from '../lib/api';

afterEach(()=>{
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function jsonResponse(body:unknown,status=200,headers:Record<string,string>={}){
  return new Response(JSON.stringify(body),{
    status,
    headers:{'Content-Type':'application/json',...headers},
  });
}

describe('research workflow API contracts',()=>{
  it('treats only the typed latest-scorecard 404 as not assessed',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(jsonResponse({
      error:{
        code:'quality_scorecard_not_found',
        message:'No quality scorecard found for this dataset/version.',
        request_id:'request-empty',
      },
    },404)));

    await expect(qh.latestDatasetQualityScorecard('dataset-a')).resolves.toBeNull();
  });

  it('does not swallow an unrelated latest-scorecard 404',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(jsonResponse({
      error:{code:'not_found',message:'The requested resource does not exist.',request_id:'request-stale'},
    },404)));

    await expect(qh.latestDatasetQualityScorecard('stale-dataset')).rejects.toMatchObject({
      name:'ApiError',
      status:404,
      code:'not_found',
      requestId:'request-stale',
    });
  });

  it('uses dataset_version_id for list and latest quality requests',async()=>{
    const fetchMock=vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        error:{code:'quality_scorecard_not_found',message:'No quality scorecard found.'},
      },404));
    vi.stubGlobal('fetch',fetchMock);

    await qh.datasetQualityScorecards('dataset-a','version / 1');
    await qh.latestDatasetQualityScorecard('dataset-a','version / 1');

    expect(String(fetchMock.mock.calls[0][0])).toContain('?dataset_version_id=version%20%2F%201');
    expect(String(fetchMock.mock.calls[1][0])).toContain('?dataset_version_id=version%20%2F%201');
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('?version_id=');
  });

  it('preserves backend validation messages, codes, and request IDs',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(jsonResponse({
      error:{
        code:'pipeline_configuration',
        message:'PCA components exceed the transformed training dimensions.',
        request_id:'request-validation',
        fields:[{location:['body','pipeline','pca_components'],type:'less_than_equal'}],
      },
    },422)));

    const error=await qh.pipelinePreview({} as never,'/pca/preview').catch(value=>value);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status:422,
      code:'pipeline_configuration',
      requestId:'request-validation',
    });
    expect(error.message).toContain('PCA components exceed');
    expect(error.message).toContain('request-validation');
  });

  it('keeps transport failures distinct from backend empty states',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(qh.latestDatasetQualityScorecard('dataset-a')).rejects.toBeInstanceOf(ApiTransportError);
  });
});