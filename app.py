'use strict';
/* PRO QUANT ENGINE V1.5.4-PRO — deterministic, strict, single-file */
(function(root){
const finite=(x,n)=>{if(typeof x!=='number'||!Number.isFinite(x))throw Error(`[INPUT_VALIDATION_ERROR] ${n} must be finite.`);return x;};
const positive=(x,n)=>{finite(x,n);if(x<=0)throw Error(`[INPUT_VALIDATION_ERROR] ${n} must be > 0.`);return x;};
const nonnegative=(x,n)=>{finite(x,n);if(x<0)throw Error(`[INPUT_VALIDATION_ERROR] ${n} must be >= 0.`);return x;};
const logFactorial=n=>{if(!Number.isSafeInteger(n)||n<0)throw Error('Invalid factorial input');let x=n+1,z=x-1,c=[676.5203681218851,-1259.1392167224028,771.3234287776531,-176.6150291621406,12.507343278686905,-.13857109526572012,9.984369578019572e-6,1.5056327351493116e-7],y=.99999999999980993;for(let i=0;i<c.length;i++)y+=c[i]/(z+i+1);let t=z+c.length-.5;return .5*Math.log(2*Math.PI)+(z+.5)*Math.log(t)-t+Math.log(y);};
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0), normInf=a=>Math.max(0,...a.map(Math.abs));

function solve(A0,b0){
 let A=A0.map(r=>r.slice()),b=b0.slice(),n=b.length;
 if(A.length!==n||A.some(r=>r.length!==n))throw Error('Linear system dimension mismatch');
 for(let k=0;k<n;k++){
  let p=k;
  for(let i=k+1;i<n;i++)if(Math.abs(A[i][k])>Math.abs(A[p][k]))p=i;
  [A[k],A[p]]=[A[p],A[k]];[b[k],b[p]]=[b[p],b[k]];
  let q=A[k][k];if(!Number.isFinite(q)||Math.abs(q)<1e-14)throw Error('Singular Hessian');
  for(let j=k;j<n;j++)A[k][j]/=q;b[k]/=q;
  for(let i=0;i<n;i++)if(i!==k){let f=A[i][k];for(let j=k;j<n;j++)A[i][j]-=f*A[k][j];b[i]-=f*b[k];}
 }
 return b;
}
function cholesky2(S){
 if(!Array.isArray(S)||S.length!==2||S.some(r=>!Array.isArray(r)||r.length!==2))throw Error('Sigma must be 2x2');
 let a=positive(S[0][0],'Sigma00'),b=finite(S[0][1],'Sigma01'),c=finite(S[1][0],'Sigma10'),d=positive(S[1][1],'Sigma11');
 if(Math.abs(b-c)>1e-12)throw Error('Sigma must be symmetric');
 let det=a*d-b*b;if(det<=1e-14)throw Error('Sigma must be positive definite');
 return {inv:[[d/det,-b/det],[-b/det,a/det]],logDet:Math.log(det)};
}

class StrictJointGaussianMAP{
 constructor({teams,matches,priorSigma,priorMean=[0,0],timeDecayLambda=.005,baselinePrior={mean:0,sd:2},homeAdvantagePrior={mean:0,sd:1},maxIterations=300,gradientTolerance=1e-7,stepTolerance=1e-8,objectiveTolerance=1e-10,maxAbsLinearPredictor=20}={}){
  if(!Array.isArray(teams)||teams.length<2||teams.some(t=>typeof t!=='string'||!t.trim())||new Set(teams).size!==teams.length)throw Error('Invalid unique team list');
  this.teams=teams.slice();this.idx=new Map(teams.map((t,i)=>[t,i]));this.lambda=nonnegative(timeDecayLambda,'timeDecayLambda');
  if(!Array.isArray(matches)||!matches.length)throw Error('Matches required');
  this.matches=matches.map((m,i)=>{
   if(!m||typeof m!=='object')throw Error(`Invalid match ${i}`);
   let hi=this.idx.get(m.homeTeam),ai=this.idx.get(m.awayTeam);
   if(hi===undefined||ai===undefined||hi===ai)throw Error(`Unknown or identical teams at match ${i}`);
   for(let k of ['homeGoals','awayGoals'])if(!Number.isSafeInteger(m[k])||m[k]<0||m[k]>30)throw Error(`Invalid ${k} at match ${i}`);
   let td=nonnegative(m.timeDelta,`matches[${i}].timeDelta`),w=Math.exp(-this.lambda*td);
   if(!Number.isFinite(w)||w<=0)throw Error(`Invalid weight at match ${i}`);
   return Object.freeze({hi,ai,homeTeam:m.homeTeam,awayTeam:m.awayTeam,homeGoals:m.homeGoals,awayGoals:m.awayGoals,neutralVenue:m.neutralVenue===true,timeDelta:td,weight:w});
  });
  this.sigma=cholesky2(priorSigma);
  if(!Array.isArray(priorMean)||priorMean.length!==2)throw Error('priorMean must have 2 values');
  this.pm=priorMean.map((x,i)=>finite(x,`priorMean${i}`));
  this.bp=this._prior(baselinePrior,'baselinePrior');this.hp=this._prior(homeAdvantagePrior,'homeAdvantagePrior');
  this.maxIterations=positive(maxIterations,'maxIterations');
  if(!Number.isSafeInteger(maxIterations))throw Error('maxIterations must be integer');
  this.gt=positive(gradientTolerance,'gradientTolerance');
  this.st=positive(stepTolerance,'stepTolerance');
  this.ot=positive(objectiveTolerance,'objectiveTolerance');
  this.maxEta=positive(maxAbsLinearPredictor,'maxAbsLinearPredictor');
 }
 _prior(p,n){if(!p||typeof p!=='object')throw Error(`${n} required`);return {mean:finite(p.mean,n+'.mean'),sd:positive(p.sd,n+'.sd')};}
 get dimension(){return 2*this.teams.length+2;}
 initialParameters(){
  let p=Array(this.dimension).fill(0);
  for(let i=0;i<this.teams.length;i++){p[2*i]=this.pm[0];p[2*i+1]=this.pm[1];}
  p[this.dimension-2]=this.bp.mean;p[this.dimension-1]=this.hp.mean;return p;
 }
 evaluate(p,derivatives=true){
  if(!Array.isArray(p)||p.length!==this.dimension||p.some(x=>typeof x!=='number'||!Number.isFinite(x)))throw Error('Invalid parameter vector');
  let n=this.dimension,g=derivatives?Array(n).fill(0):null,H=derivatives?Array.from({length:n},()=>Array(n).fill(0)):null,obj=0,L=n-2,hi=n-1;
  for(const m of this.matches){
   let ah=2*m.hi,ch=ah+1,aa=2*m.ai,ca=aa+1;
   let eH=p[L]+(m.neutralVenue?0:p[hi])+p[ah]+p[ca],eA=p[L]+p[aa]+p[ch];
   for(const [y,e,ids] of [[m.homeGoals,eH,m.neutralVenue?[L,ah,ca]:[L,hi,ah,ca]],[m.awayGoals,eA,[L,aa,ch]]]){
    if(Math.abs(e)>this.maxEta)throw Error('Linear predictor safety bound exceeded');
    let mu=Math.exp(e);obj+=m.weight*(y*e-mu-logFactorial(y));
    if(derivatives){let r=m.weight*(y-mu);for(let i of ids)g[i]+=r;for(let i of ids)for(let j of ids)H[i][j]-=m.weight*mu;}
   }
  }
  let P=this.sigma.inv,ln=-Math.log(2*Math.PI)-.5*this.sigma.logDet;
  for(let t=0;t<this.teams.length;t++){
   let i=2*t,j=i+1,da=p[i]-this.pm[0],dc=p[j]-this.pm[1],qa=P[0][0]*da+P[0][1]*dc,qc=P[1][0]*da+P[1][1]*dc;
   obj+=ln-.5*(da*qa+dc*qc);
   if(derivatives){g[i]-=qa;g[j]-=qc;H[i][i]-=P[0][0];H[i][j]-=P[0][1];H[j][i]-=P[1][0];H[j][j]-=P[1][1];}
  }
  for(let [i,pr] of [[L,this.bp],[hi,this.hp]]){
   let d=p[i]-pr.mean;obj+=-Math.log(pr.sd*Math.sqrt(2*Math.PI))-.5*(d/pr.sd)**2;
   if(derivatives){g[i]-=d/pr.sd**2;H[i][i]-=1/pr.sd**2;}
  }
  return derivatives?{objective:obj,gradient:g,hessian:H}:{objective:obj};
 }
 optimize(start=this.initialParameters()){
  if(!Array.isArray(start)||start.length!==this.dimension||start.some(x=>typeof x!=='number'||!Number.isFinite(x)))throw Error('Invalid MAP start');
  let x=start.slice(),cur=this.evaluate(x),damp=1e-8,converged=false,reason='MAX_ITERATIONS',it=0,lastStep=Infinity,lastChange=Infinity;
  for(;it<this.maxIterations;it++){
   let gn=normInf(cur.gradient);
   if(gn<=this.gt&&lastStep<=this.st&&lastChange<=this.ot){converged=true;reason='ALL_TOLERANCES_MET';break;}
   let accepted=false,step,trialX;
   for(let a=0;a<24&&!accepted;a++){
    let A=cur.hessian.map((r,i)=>r.map((v,j)=>-v+(i===j?damp:0)));
    try{step=solve(A,cur.gradient);}catch(_){damp*=10;continue;}
    let gain=dot(cur.gradient,step);if(!(gain>0)){damp*=10;continue;}
    for(let ls=0,alpha=1;ls<45;ls++,alpha*=.5){
     let z=x.map((v,i)=>v+alpha*step[i]);
     try{let ev=this.evaluate(z,false);if(ev.objective>=cur.objective+1e-4*alpha*gain){trialX=z;lastStep=alpha*normInf(step);lastChange=Math.abs(ev.objective-cur.objective);accepted=true;break;}}catch(_){}
    }
    if(!accepted)damp*=10;else damp=Math.max(1e-12,damp*.3);
   }
   if(!accepted){reason='LINE_SEARCH_OR_CURVATURE_FAILURE';break;}
   x=trialX;cur=this.evaluate(x,true);
  }
  let f=this.evaluate(x,true),gn=normInf(f.gradient);
  if(!converged&&gn<=this.gt&&lastStep<=this.st&&lastChange<=this.ot){converged=true;reason='ALL_TOLERANCES_MET';}
  return Object.freeze({converged,stopReason:reason,iterations:it,parameters:Object.freeze(x),objective:f.objective,finalGradientNorm:gn,lastStepNorm:lastStep,lastObjectiveChange:lastChange,teams:Object.freeze(Object.fromEntries(this.teams.map((t,i)=>[t,Object.freeze({attack:x[2*i],concession:x[2*i+1]})]))),baselineLog:x[this.dimension-2],homeAdvantageLog:x[this.dimension-1]});
 }
 predict(homeTeam,awayTeam,{neutralVenue=false,parameters}={}){
  let hi=this.idx.get(homeTeam),ai=this.idx.get(awayTeam);
  if(hi===undefined||ai===undefined||hi===ai)throw Error('Unknown or identical prediction teams');
  if(!Array.isArray(parameters)||parameters.length!==this.dimension||parameters.some(x=>typeof x!=='number'||!Number.isFinite(x)))throw Error('Fitted parameters required');
  let n=this.dimension,L=parameters[n-2],h=parameters[n-1],eH=L+(neutralVenue?0:h)+parameters[2*hi]+parameters[2*ai+1],eA=L+parameters[2*ai]+parameters[2*hi+1];
  if(Math.abs(eH)>this.maxEta||Math.abs(eA)>this.maxEta)throw Error('Prediction eta bound exceeded');
  return Object.freeze({homeTeam,awayTeam,homeLambda:Math.exp(eH),awayLambda:Math.exp(eA)});
 }
}

function tau(h,a,lh,la,rho){
 let t=1;
 if(h===0&&a===0)t=1-lh*la*rho;
 else if(h===0&&a===1)t=1+lh*rho;
 else if(h===1&&a===0)t=1+la*rho;
 else if(h===1&&a===1)t=1-rho;
 if(!(t>0)||!Number.isFinite(t))throw Error('Non-positive Dixon-Coles tau');
 return t;
}

function estimateRho(engine,params,{rhoMin=-.15,rhoMax=.15,tolerance=1e-8,maxIterations=1000}={}){
 if(!(rhoMin<rhoMax)||rhoMin<-.15||rhoMax>.15||!Number.isFinite(rhoMin)||!Number.isFinite(rhoMax))throw Error('Invalid rho interval');
 positive(tolerance,'rho tolerance');
 if(!Number.isSafeInteger(maxIterations)||maxIterations<1)throw Error('Invalid rho maxIterations');
 let rows=engine.matches.map(m=>{
  let p=engine.predict(m.homeTeam,m.awayTeam,{neutralVenue:m.neutralVenue,parameters:params});
  return {h:m.homeGoals,a:m.awayGoals,lh:p.homeLambda,la:p.awayLambda,w:m.weight};
 }).filter(r=>r.h<=1&&r.a<=1);
 if(!rows.length)throw Error('Insufficient low-score observations for rho');
 let lo=rhoMin,hi=rhoMax;
 for(let r of rows){
  if(r.h===0&&r.a===0)hi=Math.min(hi,(1-1e-12)/(r.lh*r.la));
  if(r.h===0&&r.a===1)lo=Math.max(lo,(-1+1e-12)/r.lh);
  if(r.h===1&&r.a===0)lo=Math.max(lo,(-1+1e-12)/r.la);
  if(r.h===1&&r.a===1)hi=Math.min(hi,1-1e-12);
 }
 if(!(lo<hi))throw Error('No valid rho interval');
 const ll=rho=>{
  let s=0;
  for(let r of rows){
   let t=tau(r.h,r.a,r.lh,r.la,rho);
   s+=r.w*(r.h*Math.log(r.lh)-r.lh-logFactorial(r.h)+r.a*Math.log(r.la)-r.la-logFactorial(r.a)+Math.log(t));
  }
  return s;
 };
 let a=lo,b=hi,gr=(Math.sqrt(5)-1)/2,c=b-gr*(b-a),d=a+gr*(b-a),fc=ll(c),fd=ll(d),it=0;
 while(it<maxIterations&&b-a>tolerance){
  if(fc>fd){b=d;d=c;fd=fc;c=b-gr*(b-a);fc=ll(c);}
  else{a=c;c=d;fc=fd;d=a+gr*(b-a);fd=ll(d);}
  it++;
 }
 let err=b-a,conv=err<=tolerance,candidates=[lo,hi,a,b,(a+b)/2,0].filter(x=>x>=lo&&x<=hi),best=candidates[0],bestLL=ll(best);
 for(let x of candidates.slice(1)){let v=ll(x);if(v>bestLL){best=x;bestLL=v;}}
 return Object.freeze({rho:best,converged:conv,accepted:conv,iterations:it,finalError:err,tolerance,logLikelihood:bestLL,atBoundary:Math.abs(best-lo)<tolerance*2||Math.abs(best-hi)<tolerance*2,interval:{min:a,max:b},method:'CONDITIONAL_MLE_GIVEN_MAP_LAMBDAS'});
}

function predictMarkets(lh,la,rho,{tailTolerance=1e-10,maxGoals=100}={}){
 positive(lh,'homeLambda');positive(la,'awayLambda');finite(rho,'rho');
 if(rho<-.15||rho>.15)throw Error('rho outside [-0.15,0.15]');
 positive(tailTolerance,'tailTolerance');if(tailTolerance>=1)throw Error('tailTolerance must be < 1');
 if(!Number.isSafeInteger(maxGoals)||maxGoals<1||maxGoals>500)throw Error('maxGoals must be integer 1..500');
 let n=Math.max(10,Math.ceil(Math.max(lh,la)+10*Math.sqrt(Math.max(lh,la)+1)+10));n=Math.min(n,maxGoals);
 let ph,pa,base,tail;
 for(;;){
  ph=Array(n+1);pa=Array(n+1);ph[0]=Math.exp(-lh);pa[0]=Math.exp(-la);
  for(let k=1;k<=n;k++){ph[k]=ph[k-1]*lh/k;pa[k]=pa[k-1]*la/k;}
  base=ph.reduce((s,x)=>s+x,0)*pa.reduce((s,x)=>s+x,0);tail=Math.max(0,1-base);
  if(tail<=tailTolerance)break;
  if(n>=maxGoals)throw Error(`CRITICAL_TAIL_MASS_ERROR: residual tail ${tail} exceeds ${tailTolerance} at maxGoals=${maxGoals}`);
  n=Math.min(maxGoals,Math.max(n+10,Math.ceil(n*1.5)));
 }
 let sums={home:0,draw:0,away:0,over25:0,under25:0,bttsYes:0,bttsNo:0},total=0;
 for(let h=0;h<=n;h++)for(let a=0;a<=n;a++){
  let q=ph[h]*pa[a]*tau(h,a,lh,la,rho);total+=q;
  if(h>a)sums.home+=q;else if(h===a)sums.draw+=q;else sums.away+=q;
  if(h+a>2)sums.over25+=q;else sums.under25+=q;
  if(h>0&&a>0)sums.bttsYes+=q;else sums.bttsNo+=q;
 }
 if(!(total>0)||Math.abs(total-1)>Math.max(1e-8,tailTolerance*20))throw Error(`Probability mass invariant failed: ${total}`);
 let p=Object.fromEntries(Object.entries(sums).map(([k,v])=>[k,v/total]));
 for(let [k,v] of Object.entries(p))if(!Number.isFinite(v)||v<0||v>1)throw Error(`Invalid probability ${k}`);
 for(let s of [[p.home,p.draw,p.away],[p.over25,p.under25],[p.bttsYes,p.bttsNo]])if(Math.abs(s.reduce((x,y)=>x+y,0)-1)>1e-10)throw Error('Market probability sum invariant failed');
 return Object.freeze({probabilities:Object.freeze(p),rho,homeLambda:lh,awayLambda:la,maxGoalsUsed:n,rawBaseMass:base,tailMassLoss:tail,rawDCTotalMass:total});
}

function calculateEV(p,o){
 if(!Number.isFinite(p)||p<0||p>1)throw Error('Invalid probability');
 if(!Number.isFinite(o)||o<=1)throw Error('Decimal odds must be >1');
 return p*o-1;
}
function kelly(p,o,{fraction=.25,bankroll=100,cap=.02}={}){
 calculateEV(p,o);positive(bankroll,'bankroll');
 if(!Number.isFinite(fraction)||fraction<=0||fraction>1)throw Error('Invalid Kelly fraction');
 if(!Number.isFinite(cap)||cap<=0||cap>1)throw Error('Invalid stake cap');
 let ev=calculateEV(p,o),full=ev/(o-1);
 if(ev<=0||full<=0)return Object.freeze({hasEdge:false,ev,fullKellyFraction:Math.max(0,full),recommendedFraction:0,recommendedStake:0});
 let f=Math.min(full*fraction,cap);
 return Object.freeze({hasEdge:true,ev,fullKellyFraction:full,recommendedFraction:f,recommendedStake:bankroll*f});
}
function removeOverround(odds){
 if(!Array.isArray(odds)||odds.length<2||odds.some(o=>!Number.isFinite(o)||o<=1))throw Error('A complete valid odds set is required for de-vig');
 let raw=odds.map(o=>1/o),sum=raw.reduce((a,b)=>a+b,0);
 return Object.freeze({overround:sum-1,fairProbabilities:Object.freeze(raw.map(x=>x/sum))});
}

function pipeline({engine,homeTeam,awayTeam,neutralVenue=false,odds,fitOverride=null,bankroll=100,fraction=.25,stakeCap=.02,tailTolerance=1e-10,minEdge=.03,minProbability=.60,modelConfidence=null,dataQuality=null,oddsTimestamp=null,asOfTimestamp=null}){
 let out={fit:null,fitAccepted:false,rho:null,rhoAccepted:false,markets:null,marketsAccepted:false,bestCandidate:null,qualifiedBet:null,finalApproved:false,finalPrediction:null,errors:[]};
 try{
  let fit=fitOverride||engine.optimize();out.fit=fit;
  out.fitAccepted=fit.converged===true&&Number.isFinite(fit.objective)&&Number.isFinite(fit.finalGradientNorm)&&fit.finalGradientNorm<=engine.gt&&Number.isFinite(fit.lastStepNorm)&&fit.lastStepNorm<=engine.st&&Number.isFinite(fit.lastObjectiveChange)&&fit.lastObjectiveChange<=engine.ot;
  if(!Array.isArray(fit.parameters)||fit.parameters.length!==engine.dimension||fit.parameters.some(x=>!Number.isFinite(x)))throw Error('Invalid fitted MAP parameters');
  if(!out.fitAccepted)throw Error(`MAP_NOT_CONVERGED:${fit.stopReason}`);
 }catch(e){out.errors.push({stage:'MAP',message:e.message});return Object.freeze(out);}
 try{out.rho=estimateRho(engine,out.fit.parameters);out.rhoAccepted=out.rho.accepted&&out.rho.converged;}
 catch(e){out.errors.push({stage:'RHO',message:e.message});return Object.freeze(out);}
 try{
  let pred=engine.predict(homeTeam,awayTeam,{neutralVenue,parameters:out.fit.parameters});
  out.markets=predictMarkets(pred.homeLambda,pred.awayLambda,out.rho.rho,{tailTolerance});out.marketsAccepted=true;
 }catch(e){out.errors.push({stage:'MARKETS',message:e.message});return Object.freeze(out);}
 try{
  if(!odds||typeof odds!=='object'||Array.isArray(odds))throw Error('Odds map required: marketKey -> decimal odds');
  if(modelConfidence===null||!Number.isFinite(modelConfidence)||modelConfidence<0||modelConfidence>1)throw Error('Explicit calibrated modelConfidence in [0,1] required');
  if(dataQuality===null||!Number.isFinite(dataQuality)||dataQuality<0||dataQuality>1)throw Error('Explicit dataQuality in [0,1] required');
  if(!oddsTimestamp||!asOfTimestamp||!Number.isFinite(Date.parse(oddsTimestamp))||!Number.isFinite(Date.parse(asOfTimestamp)))throw Error('Valid oddsTimestamp and asOfTimestamp required');
  let age=Date.parse(asOfTimestamp)-Date.parse(oddsTimestamp);
  if(age<0||age>15*60*1000)throw Error('Odds stale or timestamp is in the future (15-minute limit)');
  let fairByKey={};
  for(let [keys] of [[['home','draw','away']],[['over25','under25']],[['bttsYes','bttsNo']]]){
   if(keys.every(k=>Object.prototype.hasOwnProperty.call(odds,k))){
    let fair=removeOverround(keys.map(k=>odds[k])).fairProbabilities;
    keys.forEach((k,i)=>fairByKey[k]=fair[i]);
   }
  }
  let candidates=[];
  for(let [key,o] of Object.entries(odds)){
   let p=out.markets.probabilities[key];if(p===undefined)continue;
   let ev=calculateEV(p,o),marketFairProbability=fairByKey[key]??(1/o),edge=p-marketFairProbability;
   let k0=kelly(p,o,{fraction,bankroll,cap:stakeCap});
   let status=ev>0&&edge>=minEdge&&p>=minProbability&&modelConfidence>=.62&&dataQuality>=.70?'QUALIFIED_BET':'LEAN';
   let k=status==='QUALIFIED_BET'?k0:Object.freeze({...k0,recommendedFraction:0,recommendedStake:0,stakeAuthorized:false});
   candidates.push({market:key,probability:p,odds:o,fairOdds:1/p,impliedProbability:1/o,marketFairProbability,edge,ev,evPercent:ev*100,modelConfidence,dataQuality,kelly:k,status});
  }
  if(!candidates.length)throw Error('No supported market odds supplied');
  candidates.sort((a,b)=>b.ev-a.ev);out.bestCandidate=Object.freeze(candidates[0]);
  out.qualifiedBet=Object.freeze(candidates.filter(c=>c.status==='QUALIFIED_BET').sort((a,b)=>b.ev-a.ev)[0]||null);
  out.finalApproved=!!out.qualifiedBet&&out.fitAccepted&&out.rhoAccepted&&out.marketsAccepted;
  if(out.finalApproved)out.finalPrediction=out.qualifiedBet;
  else out.finalPrediction=Object.freeze({...out.bestCandidate,status:'NO_BET',reason:out.bestCandidate.ev<=0?'NON_POSITIVE_EV':'QUALIFICATION_THRESHOLDS_NOT_MET',stake:0});
 }catch(e){out.errors.push({stage:'BET_QUALIFICATION',message:e.message});}
 return Object.freeze(out);
}

function runProfessionalTestSuite(){
 let tests=[];
 let test=(name,fn)=>{try{fn();tests.push({name,passed:true});}catch(e){tests.push({name,passed:false,error:e.message});}};
 let throws=(fn,s)=>{let ok=false;try{fn();}catch(e){ok=e.message.includes(s);}if(!ok)throw Error('Expected rejection '+s);};
 let close=(a,b,t=1e-8)=>{if(!Number.isFinite(a)||Math.abs(a-b)>t)throw Error(`${a} != ${b}`);};
 const base={teams:['A','B'],matches:[
  {homeTeam:'A',awayTeam:'B',homeGoals:0,awayGoals:0,timeDelta:1},
  {homeTeam:'B',awayTeam:'A',homeGoals:1,awayGoals:0,timeDelta:2},
  {homeTeam:'A',awayTeam:'B',homeGoals:1,awayGoals:1,timeDelta:3},
  {homeTeam:'B',awayTeam:'A',homeGoals:0,awayGoals:1,timeDelta:4}
 ],priorSigma:[[.15,.04],[.04,.12]]};
 let e=new StrictJointGaussianMAP(base);

 test('GATE 1 Strict input validation',()=>{
  throws(()=>new StrictJointGaussianMAP({...base,matches:[{...base.matches[0],timeDelta:undefined}]}),'timeDelta');
  throws(()=>new StrictJointGaussianMAP({...base,matches:[{...base.matches[0],homeTeam:'X'}]}),'Unknown');
  throws(()=>new StrictJointGaussianMAP({...base,matches:[{...base.matches[0],homeGoals:NaN}]}),'homeGoals');
  throws(()=>new StrictJointGaussianMAP({...base,priorSigma:[[1,2],[2,1]]}),'positive definite');
 });
 test('GATE 2 Rho conditional MLE diagnostics',()=>{
  let f=e.optimize();if(!f.converged)throw Error('MAP did not converge in fixture');
  let r=estimateRho(e,f.parameters,{tolerance:1e-8,maxIterations:1000});
  if(!r.converged||!Number.isFinite(r.rho)||r.method!=='CONDITIONAL_MLE_GIVEN_MAP_LAMBDAS')throw Error('Rho diagnostics invalid');
  let q=estimateRho(e,f.parameters,{tolerance:1e-30,maxIterations:1});
  if(q.accepted)throw Error('Forced rho non-convergence accepted');
 });
 test('GATE 3 MAP convergence honesty',()=>{
  let f=e.optimize();if(typeof f.converged!=='boolean'||!Number.isFinite(f.finalGradientNorm))throw Error('Missing diagnostics');
  let f2=new StrictJointGaussianMAP({...base,maxIterations:1}).optimize();
  if(f2.converged&&f2.iterations>1)throw Error('Invalid convergence report');
 });
 test('GATE 4 Dynamic tail mass and strict cap',()=>{
  let m=predictMarkets(2,2,0,{tailTolerance:1e-10,maxGoals:100});
  if(m.tailMassLoss>1e-10)throw Error('Tail mass too large');
  throws(()=>predictMarkets(8,8,0,{tailTolerance:1e-12,maxGoals:5}),'CRITICAL_TAIL_MASS_ERROR');
 });
 test('GATE 5 EV and Kelly no negative stake',()=>{
  let k=kelly(.4,2);if(k.recommendedStake!==0||k.hasEdge)throw Error('Negative EV received stake');
  let p=kelly(.7,2,{bankroll:100,fraction:.25,cap:.02});
  if(p.recommendedStake<=0||p.recommendedStake>2)throw Error('Kelly cap failure');
  throws(()=>calculateEV(1.1,2),'Invalid probability');
 });
 test('GATE 6 Regression reference values',()=>{
  let p=predictMarkets(1,1,0,{tailTolerance:1e-10}).probabilities;
  close(p.home,.34574583872316467);close(p.draw,.30850832255367105);close(p.away,.34574583872316467);
  close(p.over25,.3233235838169369);close(p.under25,.6766764161830636);
  close(p.bttsYes,.3995764008937283);close(p.bttsNo,.600423599106272);
 });
 test('GATE 7 Probability and de-vig invariants',()=>{
  let p=predictMarkets(1.2,1,.02).probabilities;
  close(p.home+p.draw+p.away,1);close(p.over25+p.under25,1);close(p.bttsYes+p.bttsNo,1);
  let d=removeOverround([2,3,4]);close(d.fairProbabilities.reduce((a,b)=>a+b,0),1);
  if(d.overround<=0)throw Error('Expected overround');
 });
 test('GATE 8 Integration: no bet without edge, fresh odds and explicit quality',()=>{
  let f=e.optimize(),failed={...f,converged:false,stopReason:'FORCED_FAILURE'};
  let blocked=pipeline({engine:e,homeTeam:'A',awayTeam:'B',odds:{away:2.5},modelConfidence:.9,dataQuality:.9,oddsTimestamp:new Date().toISOString(),asOfTimestamp:new Date().toISOString(),fitOverride:failed});
  if(blocked.finalApproved||blocked.finalPrediction!==null)throw Error('Failed MAP produced a prediction');
  let r=pipeline({engine:e,homeTeam:'A',awayTeam:'B',odds:{away:1.01},modelConfidence:.9,dataQuality:.9,oddsTimestamp:new Date().toISOString(),asOfTimestamp:new Date().toISOString(),fitOverride:f});
  if(r.finalApproved||!r.finalPrediction||r.finalPrediction.stake!==0)throw Error('Unqualified bet passed');
  let stale=pipeline({engine:e,homeTeam:'A',awayTeam:'B',odds:{away:2.5},modelConfidence:.9,dataQuality:.9,oddsTimestamp:'2020-01-01T00:00:00Z',asOfTimestamp:new Date().toISOString(),fitOverride:f});
  if(stale.finalApproved)throw Error('Stale odds accepted');
 });
 let passed=tests.filter(x=>x.passed).length;
 return Object.freeze({version:'1.5.4-PRO',passed,total:tests.length,success:passed===tests.length,results:Object.freeze(tests)});
}

const api=Object.freeze({
 StrictJointGaussianMAP,
 estimateDixonColesRhoMLE:estimateRho,
 predictMarkets,
 calculateEV,
 calculateKellyStake:kelly,
 removeOverround,
 runPredictionPipeline:pipeline,
 runProfessionalTestSuite
});
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.PRO_QUANT_ENGINE_V1_5_4=api;
})(typeof globalThis!=='undefined'?globalThis:this);

if(typeof require!=='undefined'&&require.main===module){
 let r=module.exports.runProfessionalTestSuite();
 console.log(JSON.stringify(r,null,2));
 if(!r.success)process.exitCode=1;
}
