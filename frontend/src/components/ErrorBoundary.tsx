import {Component,type ReactNode} from 'react';

export class ErrorBoundary extends Component<{children:ReactNode},{failed:boolean}>{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){
    if(this.state.failed)return <section className="glass-card p-6" role="alert"><h2 className="section-title">This research view could not load</h2><p className="section-copy mt-2">Your saved experiments remain in the backend. Reload this view to retry.</p><button className="btn btn-primary mt-4" onClick={()=>window.location.reload()}>Reload workspace</button></section>;
    return this.props.children;
  }
}