type Service = {data?: unknown; isError: boolean; isFetching: boolean; failureCount: number};
type Status = Service & {data?: {database_available?: boolean; storage_available?: boolean}};
export function connectionState(health: Service, status: Status) {
  if ([health, status].some(service => service.isFetching && (service.isError || service.failureCount > 0)))
    return {label: 'Retrying', detail: 'Rechecking the research services.', tone: 'pending'};
  if (health.data && status.data && !health.isError && !status.isError && status.data.database_available !== false && status.data.storage_available !== false)
    return {label: 'Connected', detail: 'The research service and workspace storage are responding.', tone: 'live'};
  if (!health.data && !status.data && !health.isError && !status.isError)
    return {label: 'Connecting', detail: 'Waiting for the research service.', tone: 'pending'};
  if (health.data || status.data)
    return {label: 'Partial availability', detail: 'Some services have not confirmed availability. Loaded evidence is still accessible.', tone: 'partial'};
  return {label: 'Unavailable', detail: 'The research service could not be reached. Retry the connection.', tone: 'offline'};
}
