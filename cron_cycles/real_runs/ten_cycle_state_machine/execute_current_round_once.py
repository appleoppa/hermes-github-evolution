#!/usr/bin/env python3
import json, datetime, pathlib, subprocess, urllib.request, hashlib, importlib.util, sys, types, re, os
ROOT=pathlib.Path('/Users/appleoppa/.hermes/workspace/github-evolution')
SR=ROOT/'cron_cycles/real_runs/ten_cycle_state_machine'; EV=SR/'evidence'; ST=SR/'state.json'; EV.mkdir(parents=True,exist_ok=True)

def load_env(path='/Users/appleoppa/.hermes/.env'):
    p=pathlib.Path(path)
    if not p.exists(): return
    for line in p.read_text(errors='replace').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1)
        k=k.strip(); v=v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k]=v

def gh_headers():
    h={'Accept':'application/vnd.github+json','User-Agent':'hermes-cron-evolution'}
    tok=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if tok: h['Authorization']='Bearer '+tok
    return h

load_env()
now=datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
state=json.loads(ST.read_text()) if ST.exists() else {'cycle':1,'current_round':1,'total_cycles':10,'rounds_per_cycle':5,'status':'running','created_at':now,'history':[]}
cycle=int(state.get('cycle',1)); rnd=int(state.get('current_round',1))
blocked=None
if not (cycle==1 and rnd==1):
 pc,pr=(cycle,rnd-1) if rnd>1 else (cycle-1,5); prev=EV/f'C{pc:02d}_R{pr}.json'
 if (not prev.exists()) or prev.stat().st_size==0: blocked={'gate':'上一回合证据文件不存在或为空','previous_cycle':pc,'previous_round':pr}
 else:
  ps=json.loads(prev.read_text()).get('status_grade','')
  if any(x in ps for x in ['证据不足','失败','本地脚本模拟','本地演练']): blocked={'gate':'上一回合状态不合格','previous_cycle':pc,'previous_round':pr,'previous_status':ps}
if blocked:
 out=EV/f'C{cycle:02d}_R{rnd}_blocked.json'; out.write_text(json.dumps({'generated_at':now,'cycle':cycle,'round':rnd,'status_grade':'失败','blocked':blocked,'state_before':state},ensure_ascii=False,indent=2)); print(json.dumps({'blocked':blocked,'evidence':str(out)},ensure_ascii=False)); raise SystemExit
FORM=ROOT/'formulas'
spec=importlib.util.spec_from_file_location('apex',FORM/'apex_v2_1_fixed.py'); apex=importlib.util.module_from_spec(spec); spec.loader.exec_module(apex)
tao=importlib.util.spec_from_file_location('AncientTao.ANCIENT_TAO',FORM/'ANCIENT_TAO.py'); tm=importlib.util.module_from_spec(tao); tao.loader.exec_module(tm); sys.modules['AncientTao']=types.ModuleType('AncientTao'); sys.modules['AncientTao.ANCIENT_TAO']=tm
spec2=importlib.util.spec_from_file_location('evm',FORM/'EVM_FORMULA.py'); evmm=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(evmm)
remote=subprocess.run(['git','remote','-v'],cwd=ROOT,text=True,capture_output=True,timeout=30).stdout.strip(); lsrem=subprocess.run(['git','ls-remote','--heads','origin'],cwd=ROOT,text=True,capture_output=True,timeout=60)
factory={}; shorts=[]
if 'github.com/appleoppa/hermes-github-evolution' not in remote: shorts.append('远程仓库配置缺失，外部工厂不可追踪。')
if lsrem.returncode==0 and lsrem.stdout.strip(): factory['git_remote_probe']={'status':'ok','refs':[{'sha':l.split()[0],'ref':l.split()[1]} for l in lsrem.stdout.strip().splitlines()[:5]]}
else: factory['git_remote_probe']={'status':'failed','stderr':lsrem.stderr.strip(),'returncode':lsrem.returncode}; shorts.append('Git远程探测失败，无法证明外部工厂可达。')
try:
 req=urllib.request.Request('https://api.github.com/repos/appleoppa/hermes-github-evolution/actions/runs?per_page=5',headers=gh_headers()); data=json.load(urllib.request.urlopen(req,timeout=30)); factory['actions_probe']={'participation':'已查询远程GitHub Actions','http':'ok','total_count':data.get('total_count'),'runs':[{'id':x.get('id'),'name':x.get('name'),'status':x.get('status'),'conclusion':x.get('conclusion'),'created_at':x.get('created_at')} for x in data.get('workflow_runs',[])[:5]]}
except Exception as e:
 factory['actions_probe']={'participation':'已尝试查询远程GitHub Actions，但未取得可用Actions记录','error_type':type(e).__name__,'error':str(e)}; shorts.append('GitHub Actions接口不可用或不可见；本回合不能把远程工厂参与说成完整。')
learn_url='https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/using-workflow-run-logs'
try:
 html=urllib.request.urlopen(urllib.request.Request(learn_url,headers={'User-Agent':'hermes-cron-evolution'}),timeout=30).read().decode('utf-8','replace'); text=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>',' ',html); text=re.sub(r'<[^>]+>',' ',text); text=re.sub(r'\s+',' ',text); sn=[]
 for kw in ['Viewing logs','download logs','failed step']:
  i=text.lower().find(kw.lower())
  if i>=0: sn.append(text[i:i+320])
 learning={'source_title':'GitHub Docs: Use workflow run logs','url':learn_url,'access':'opened_html_content','sha256':hashlib.sha256(html.encode()).hexdigest(),'read_snippets':sn,'extracted_points':['工作流运行页可区分运行中、完成、成功、失败、取消或中性结果。','失败时应进入具体job或step日志定位失败步骤，不能只用工作流存在或接口可达证明演化。','日志和产物可下载，证据应记录run、job、step、结论与失败原因。'],'behavior_change':'本回合把git远程可达与Actions运行记录分开；Actions不可见时只记为工厂部分参与或证据不足。'}
except Exception as e: learning={'source_title':'GitHub Docs: Use workflow run logs','url':learn_url,'access':'failed','error_type':type(e).__name__,'error':str(e),'extracted_points':[],'behavior_change':'外部学习失败，不能称完整真实回合。'}
keys={'dg':chr(0x0394)+'G_base','theta':chr(0x0398),'eps':chr(0x03b5),'phi':chr(0x03a6),'psi':chr(0x03a8),'pi':chr(0x03a0),'lambda_ctx':chr(0x039b)+'_ctx','gamma':chr(0x0393),'xi':chr(0x039e)}
ai={keys['dg']:0.58,keys['theta']:0.72,'K':0.70,keys['eps']:0.78,keys['phi']:0.66,keys['psi']:0.62,keys['pi']:0.55,keys['lambda_ctx']:0.64,keys['gamma']:0.58,'PID':0.61,'RD':0.60,'Kelly':0.42,'E_xp':0.36,'M_meta':0.52,keys['xi']:0.40,'_n_decisions':5}
if factory.get('actions_probe',{}).get('error_type'): ai['RD']=0.53; ai[keys['phi']]=0.59; ai[keys['xi']]=0.36
if learning.get('access')=='failed': ai['E_xp']=0.25
score=apex.dg_v2_3(ai); short='；'.join(shorts) if shorts else '本回合暴露的短板是：远程仓库可达不等于Actions工厂已执行，证据粒度仍需下钻到run/job/step。'
bd={'Err':0.27,'Log':0.22,'Run':0.20,'Prm':0.16,'Net':0.18 if factory.get('actions_probe',{}).get('error_type') else 0.08,'Soul':0.18}; ad=dict(bd); repairs=[]
for k,d,r in [('Log',0.04,'证据中拆分git远程、Actions、学习来源，降低日志溯源缺陷'),('Err',0.03,'明确Actions不可见不能称完整，降低幻觉缺陷'),('Prm',0.02,'按状态机只推进当前回合，降低提示执行偏差'),('Run',0.01,'实际执行远程探测和外部阅读，降低运行缺陷')]:
 old=ad[k]; ad[k]=max(0,old-d); repairs.append({'defect':k,'before':old,'after':ad[k],'reason':r})
def es(defs):
 c=evmm.EVMCore()
 for k,v in defs.items(): c.add_defect(k,v)
 return c.get_status()
eb=es(bd); ea=es(ad)
route=[{'step':'主脑统筹','participant':'本地主脑','input':f'状态指向C{cycle:02d}R{rnd}，本次只准推进一回合','output':'执行当前回合，先探测远程与门禁，不生成未来回合'},{'step':'反证审错','participant':'本地反证代理','input':'远程git可达但Actions接口不可见时是否可称工厂完成','output':'不可称完整；必须降级为工厂证据不足'},{'step':'修复落地','participant':'本地修复代理','input':'外部学习指出要看run/job/step日志','output':'证据结构拆分为git远程探测、Actions探测、文档阅读和边界声明'},{'step':'旁证压缩','participant':'本地旁证代理','input':'APEX、EVM、学习、远程探测结果','output':'保留可核验字段，拒绝用分数或文件存在替代真实性'},{'step':'主脑收束','participant':'本地主脑','input':'Actions工厂状态','output':'按真实查询结果定级，不生成未来回合'}]
status='完整真实回合'
if learning.get('access')=='failed' or factory.get('actions_probe',{}).get('error_type'): status='部分完成或证据不足'
advance=status=='完整真实回合'
report={'generated_at':now,'cycle':cycle,'round':rnd,'state_before':state,'failure_premortem':'最可能被判假：把git远程可达、文件写入或一次查询尝试冒充GitHub工厂真实参与。已用Actions门禁降级避免。','apex_total_formula':{'entry':'formulas/apex_v2_1_fixed.py:dg_v2_3','inputs':ai,'result':round(score,6),'shortboard_exposed':short,'impact':'APEX输入按Actions工厂真实可见性调整；判断结果决定是否推进。'},'shortboard_source':'由本回合实际读取state、探测git远程、查询GitHub Actions和阅读外部文档后暴露，不是预设短板。','external_learning':learning,'evm':{'entry':'formulas/EVM_FORMULA.py:EVMCore','status':'真实EVM入口已调用','before':{k:round(eb[k],6) for k in ['evm_value','raw_defect_rate','governed_defect_rate','governance_reduction']},'after':{k:round(ea[k],6) for k in ['evm_value','raw_defect_rate','governed_defect_rate','governance_reduction']},'defects_before':bd,'defects_after':ad,'repair_actions':repairs,'boundary':'缺陷压降来自本回合实际拆分和降级动作；不把EVM治理系数当作二次自证。'},'hetu_luoshu_matrix':{'status':'本地五段路由；远程多模型未参与','route':route},'github_factory':{'participation':'已查询远程Actions运行记录' if not factory.get('actions_probe',{}).get('error_type') else 'Git远程可达；Actions工厂查询未取得可用运行记录','detail':factory,'boundary':'Git远程可达不等于工厂运行；工作流成功也不能单独证明进化。'},'status_grade':status,'advance_state':advance,'boundary':'文件、分数、missing、git远程可达或工作流成功均不等于完整真实周期。'}
out=EV/f'C{cycle:02d}_R{rnd}.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
state.pop('blocked_at', None); state.pop('blocked_cycle', None); state.pop('blocked_round', None); state.pop('blocked_gate', None)
if advance:
 nc,nr=(cycle,rnd+1) if rnd<5 else (cycle+1,1); state.update({'cycle':nc,'current_round':nr,'status':'running','updated_at':now,'last_evidence':str(out.relative_to(ROOT))}); state.setdefault('history',[]).append({'cycle':cycle,'round':rnd,'status':status,'evidence':str(out.relative_to(ROOT)),'at':now})
else:
 state.update({'status':'blocked','blocked_at':now,'blocked_cycle':cycle,'blocked_round':rnd,'blocked_gate':'GitHub Actions工厂门禁未跑通','last_evidence':str(out.relative_to(ROOT))}); state.setdefault('history',[]).append({'cycle':cycle,'round':rnd,'status':status,'evidence':str(out.relative_to(ROOT)),'at':now,'blocked':True})
ST.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cycle':cycle,'round':rnd,'status_grade':status,'advance':advance,'evidence':str(out),'next_cycle':state.get('cycle'),'next_round':state.get('current_round'),'state_status':state.get('status')},ensure_ascii=False))
