import {fireEvent, render, screen} from '@testing-library/react';
import {describe, expect, it} from 'vitest';
import {DataTable, Input, Pagination, SearchInput, StatusBadge, Tabs} from '../components/Primitives';
import {EnterpriseEmptyState, EnterprisePageHeader} from '../components/Primitives';

describe('enterprise component vocabulary', () => {
  it('associates form labels and exposes invalid state', () => {
    render(<Input label="Dataset name" error="A dataset name is required" required />);
    const input = screen.getByLabelText(/Dataset name/);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('A dataset name is required');
  });

  it('supports compact search and semantic statuses', () => {
    const onChange = (value: string) => expect(value).toBe('heart');
    render(<><SearchInput label="Search datasets" value="" onChange={onChange} /><StatusBadge status="running" /></>);
    fireEvent.change(screen.getByRole('searchbox', {name: 'Search datasets'}), {target: {value: 'heart'}});
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('renders sortable table headers, rows, and selected row state', () => {
    const onSort = (key: string) => expect(key).toBe('name');
    render(<DataTable caption="Datasets" columns={[{key: 'name', header: 'Dataset', sortable: true}, {key: 'count', header: 'Samples', numeric: true}]} rows={[{id: 'a', name: 'Heart cohort', count: 42}]} onSort={onSort} selectedRowKey="a" />);
    expect(screen.getByRole('columnheader', {name: /Dataset/})).toBeInTheDocument();
    expect(screen.getByRole('cell', {name: 'Heart cohort'})).toBeInTheDocument();
    expect(screen.getByRole('row', {name: /Heart cohort/})).toHaveClass('is-selected');
    fireEvent.click(screen.getByRole('button', {name: 'Sort by Dataset'}));
  });

  it('keeps empty state truthful and pagination accessible', () => {
    render(<><EnterpriseEmptyState title="No datasets available" description="Upload or load a dataset to begin." /><Pagination page={2} pageCount={3} onChange={() => undefined} /></>);
    expect(screen.getByText('No datasets available')).toBeInTheDocument();
    expect(screen.getByRole('navigation', {name: 'Pagination'})).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Previous page'})).not.toBeDisabled();
  });

  it('renders compact page header and tab semantics together', () => {
    render(<><EnterprisePageHeader eyebrow="DATA LAB" title="Datasets" description="Inspect research inputs." /><Tabs items={[{value: 'summary', label: 'Summary'}]} value="summary" onChange={() => undefined} /></>);
    expect(screen.getByRole('heading', {name: 'Datasets'})).toBeInTheDocument();
    expect(screen.getByRole('tab', {name: 'Summary'})).toHaveAttribute('aria-selected', 'true');
  });
});
