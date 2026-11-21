import type {KeyboardEvent, ReactNode} from 'react';

export function moveTab(event: KeyboardEvent<HTMLElement>) {
  const list = event.currentTarget;
  const tabs = Array.from(list.querySelectorAll<HTMLElement>('[role="tab"]:not([disabled])'));
  const index = tabs.indexOf(event.target as HTMLElement);
  if (index < 0 || !tabs.length) return;
  const vertical = list.getAttribute('aria-orientation') === 'vertical';
  let next: number;
  switch (event.key) {
    case 'Home': next = 0; break;
    case 'End': next = tabs.length - 1; break;
    case vertical ? 'ArrowUp' : 'ArrowLeft': next = (index - 1 + tabs.length) % tabs.length; break;
    case vertical ? 'ArrowDown' : 'ArrowRight': next = (index + 1) % tabs.length; break;
    default: return;
  }
  event.preventDefault();
  tabs[next].focus();
  tabs[next].click();
}

type Item<T extends string> = {id: T; label: ReactNode};
type Props<T extends string> = {
  label: string; prefix: string; items: readonly Item<T>[]; value: T; onChange: (value: T) => void;
};
export function ChoiceTabs<T extends string>({label, prefix, items, value, onChange}: Props<T>) {
  return <div className="choice-tabs" role="tablist" aria-label={label} onKeyDown={moveTab}>
    {items.map(item => <button type="button" key={item.id} id={prefix + '-tab-' + item.id}
      role="tab" aria-controls={prefix + '-panel'} aria-selected={item.id === value}
      tabIndex={item.id === value ? 0 : -1} onClick={() => onChange(item.id)}>{item.label}</button>)}
  </div>;
}
