// Gateway control core. Bind ONLY to server-owned SFU Consumers/Transports.
// Consumers MUST be created paused and must not be resumed elsewhere.
// Tests use fakes. Production requires actual SFU and process-level watchdog.
export class LeaseGate{
 constructor({sessionId,userIds,authorize,connected,consumers,closeTransport,watchdog=null,clock=Date.now,schedule=setTimeout,cancel=clearTimeout}){
  if(userIds.length!==2||new Set(userIds).size!==2)throw Error("Two participants required");
  Object.assign(this,{sessionId,userIds,authorize,connected,consumers,closeTransport,watchdog,clock,schedule,cancel});
  this.minute=0;this.deadline=0;this.armedDeadline=0;this.pausedEarly=false;this.closed=false;this.busy=false;
 }
 async stop(){
  if(this.closed)return;
  this.closed=true;this.cancel(this.timer);
  // Transport closure is the terminal gate, not a browser instruction.
  await this.closeTransport();
 }
 arm(){
  this.cancel(this.timer);
  this.timer=this.schedule(()=>{void this.tick().catch(()=>this.stop());},Math.max(0,Math.min(5000,this.deadline-this.clock()-(this.watchdog&&!this.pausedEarly?750:0))));
 }
 async tick(){
  if(this.closed||this.busy)return;
  this.busy=true;
  try{
   if(!this.connected()){await this.stop();return;}
   const expired=this.clock()>=this.deadline;
   if(this.watchdog&&this.armedDeadline&&!expired&&this.deadline-this.clock()<=750){
    await Promise.all(this.consumers().map(c=>c.pause()));
    if(this.closed)return;
    await this.watchdog.clear(this.sessionId,this.armedDeadline);
    this.armedDeadline=0;this.pausedEarly=true;
    this.arm();return;
   }
   if(expired){
    // Freeze forwarding before contacting billing, including on first use.
    // If the SFU fails to acknowledge pause, close its transports instead.
    // The real adapter still needs a process-level hard deadline watchdog.
    const pauseGuard=this.schedule(()=>{void this.stop();},500);
    try{await Promise.all(this.consumers().map(c=>c.pause()));}
    finally{this.cancel(pauseGuard);}
    if(this.closed)return;
    if(!this.connected()){await this.stop();return;}
    if(this.watchdog&&this.armedDeadline){await this.watchdog.clear(this.sessionId,this.armedDeadline);this.armedDeadline=0;}
   }
   const index=this.minute+(expired?1:0);
   // At the deadline pause regardless of a slow in-flight permission check.
   const guard=!expired?this.schedule(()=>{void this.stop();},Math.max(0,this.deadline-this.clock())):null;
   let deadline;
   try{deadline=await this.authorize({sessionId:this.sessionId,userIds:this.userIds,minute:index});}
   finally{if(guard!==null)this.cancel(guard);}
   if(this.closed)return;
   if(!deadline||deadline<=this.clock()||!this.connected()||(!expired&&deadline!==this.deadline)){
    await this.stop();return;
   }
   this.deadline=deadline;this.minute=index;
   if(expired){
    if(this.watchdog){
     this.armedDeadline=deadline;
     await this.watchdog.arm(this.sessionId,deadline);
     if(this.closed||deadline-this.clock()<=750){await this.stop();return;}
    }
    this.pausedEarly=false;
    // Arm a deadline guard before enabling media; a slow resume cannot
    // extend the lease. Never attach an unpaused Consumer.
    this.timer=this.schedule(()=>{void this.stop();},Math.max(0,deadline-this.clock()));
    await Promise.all(this.consumers().map(c=>c.resume()));
   }
   if(!this.closed)this.arm();
  }catch{await this.stop();}
  finally{this.busy=false;}
 }
}
