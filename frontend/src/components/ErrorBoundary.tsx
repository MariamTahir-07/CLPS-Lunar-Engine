import { Component, ReactNode } from 'react'
export default class ErrorBoundary extends Component<{children:ReactNode},{err:string|null}>{
  state={err:null as string|null}
  static getDerivedStateFromError(e:Error){return {err:e.message}}
  render(){ return this.state.err
    ? <div className="card err" role="alert">Something went wrong: {this.state.err}. <button onClick={()=>this.setState({err:null})}>Retry</button></div>
    : this.props.children }
}
