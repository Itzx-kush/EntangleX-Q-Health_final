import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {ChevronDown,History,LogIn,LogOut,Settings2,UserRound} from 'lucide-react';
import {NavLink} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import {AccountAvatar,accountEmail,accountName} from './AccountIdentity';
import {useGuestMigration} from './GuestMigrationProvider';

export function AccountMenu(){
  const {user,isAuthenticated,error,signingOut,signOut}=useAuth();
  const {beginUpgrade,hasMigratableState}=useGuestMigration();
  const [open,setOpen]=useState(false);
  const [mobile,setMobile]=useState(()=>typeof window.matchMedia==='function'&&window.matchMedia('(max-width: 767px)').matches);
  const triggerRef=useRef<HTMLButtonElement>(null);
  const containerRef=useRef<HTMLDivElement>(null);
  const menuRef=useRef<HTMLDivElement>(null);

  const close=(restoreFocus=false)=>{
    setOpen(false);
    if(restoreFocus)window.requestAnimationFrame(()=>triggerRef.current?.focus());
  };

  useEffect(()=>{
    if(!open)return;
    const focusTimer=window.requestAnimationFrame(()=>{
      menuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    });
    const onPointerDown=(event:PointerEvent)=>{
      const target=event.target as Node;
      if(!containerRef.current?.contains(target)&&!menuRef.current?.contains(target))close();
    };
    const onKeyDown=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();close(true)}
    };
    document.addEventListener('pointerdown',onPointerDown);
    document.addEventListener('keydown',onKeyDown);
    return()=>{
      window.cancelAnimationFrame(focusTimer);
      document.removeEventListener('pointerdown',onPointerDown);
      document.removeEventListener('keydown',onKeyDown);
    };
  },[open]);

  useEffect(()=>{
    if(typeof window.matchMedia!=='function')return;
    const media=window.matchMedia('(max-width: 767px)');
    const update=()=>setMobile(media.matches);
    update();
    media.addEventListener?.('change',update);
    return()=>media.removeEventListener?.('change',update);
  },[]);

  const onMenuKeyDown=(event:React.KeyboardEvent<HTMLDivElement>)=>{
    if(!['ArrowDown','ArrowUp','Home','End'].includes(event.key))return;
    const items=Array.from(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([disabled])')||[]);
    if(!items.length)return;
    event.preventDefault();
    const current=items.indexOf(document.activeElement as HTMLElement);
    const next=event.key==='Home'?0:event.key==='End'?items.length-1:event.key==='ArrowDown'?(current+1)%items.length:(current<=0?items.length-1:current-1);
    items[next]?.focus();
  };

  if(!isAuthenticated){
    return <div className="guest-account-control" aria-label="Guest access">
      <span><span className="guest-account-dot"/>Guest mode</span>
      <button type="button" onClick={beginUpgrade}><LogIn size={14}/>{hasMigratableState?'Save work':'Sign in'}</button>
    </div>;
  }

  const menu=open&&<div ref={menuRef} id="account-menu" className="account-menu" role="menu" aria-label="Account menu" onKeyDown={onMenuKeyDown}>
    <div className="account-menu-identity">
      <AccountAvatar user={user} size="medium"/>
      <span><strong>{accountName(user)}</strong><small>{accountEmail(user)}</small></span>
    </div>
    <div className="account-menu-section">
      <span className="account-menu-label">Account</span>
      <NavLink to="/account" role="menuitem" onClick={()=>close()}><UserRound size={16}/><span><strong>My account</strong><small>Identity and session</small></span></NavLink>
      <NavLink to="/my-research" role="menuitem" onClick={()=>close()}><History size={16}/><span><strong>My Research</strong><small>Private research activity</small></span></NavLink>
      <NavLink to="/settings" role="menuitem" onClick={()=>close()}><Settings2 size={16}/><span><strong>Preferences</strong><small>Interface and research settings</small></span></NavLink>
    </div>
    <div className="account-menu-section account-menu-auth">
      <span className="account-menu-label">Authentication</span>
      <button role="menuitem" type="button" disabled={signingOut} onClick={()=>void signOut()}><LogOut size={16}/><span><strong>{signingOut?'Signing out…':'Sign out'}</strong><small>Return to research access</small></span></button>
      {error&&<p className="account-menu-error" role="alert">{error}</p>}
    </div>
  </div>;

  const mobileLayer=open&&mobile?createPortal(<>
    <button className="account-menu-scrim" aria-label="Close account menu" type="button" onClick={()=>close(true)}/>
    {menu}
  </>,document.body):null;

  return <div className="account-menu-root" ref={containerRef}>
    <button
      ref={triggerRef}
      className="account-trigger"
      type="button"
      aria-haspopup="menu"
      aria-expanded={open}
      aria-controls="account-menu"
      onClick={()=>setOpen(value=>!value)}
    >
      <AccountAvatar user={user} size="small"/>
      <span className="account-trigger-copy"><strong>{accountName(user)}</strong><small>Personal workspace</small></span>
      <ChevronDown size={14} aria-hidden="true"/>
    </button>
    {open&&!mobile&&menu}
    {mobileLayer}
  </div>;
}
