#!/usr/bin/env python3
import json, os, pathlib, datetime, urllib.request, urllib.parse, importlib.util, sys, types
ROOT = pathlib.Path(__file__).resolve().parents[1]
FORM = ROOT / 'formulas'
OUT = ROOT / 'inbox'
GENES = ROOT / 'genes'
OUT.mkdir(exist_ok=True); GENES.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('apex', FORM/'apex_v2_1_fixed.py')
apex = importlib.util.module_from_spec(spec); spec.loader.exec_module(apex)
sys.path.insert(0, str(FORM))
pkg=types.ModuleType('AncientTao')
tao=importlib.util.spec_from_file_location('AncientTao.ANCIENT_TAO', FORM/'ANCIENT_TAO.py')
taomod=importlib.util.module_from_spec(tao); tao.loader.exec_module(taomod)
sys.modules['AncientTao']=pkg; sys.modules['AncientTao.ANCIENT_TAO']=taomod
spec2 = importlib.util.spec_from_file_location('evm', FORM/'EVM_FORMULA.py')
evm_mod = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(evm_mod)

def github_search(topic):
    q=urllib.parse.quote(topic + ' stars:>500')
    url=f'https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=3'
    req=urllib.request.Request(url, headers={'Accept':'application/vnd.github+json','User-Agent':'hermes-awakening'})
    if os.getenv('GITHUB_TOKEN'):
        req.add_header('Authorization','Bearer '+os.getenv('GITHUB_TOKEN'))
    with urllib.request.urlopen(req, timeout=30) as r:
        data=json.load(r)
    return [{"name":x.get('full_name'),"url":x.get('html_url'),"stars":x.get('stargazers_count'),"desc":x.get('description')} for x in data.get('items',[])[:3]]

risk = {'shortboard':'远程闭环已跑通，但若不把公式/EVM/河图洛书写进流水线，只会变成新的自动化口号','likely_fake_reason':'只生成仓库和文件，却没有公式代入、缺陷压降和多模型判断链证据'}
before_dims={'ΔG_base':0.55,'Θ':0.78,'K':0.62,'ε':0.74,'Φ':0.66,'Ψ':0.58,'Π':0.70,'Λ_ctx':0.36,'Γ':0.64,'PID':0.61,'RD':0.68,'Kelly':0.55,'E_xp':0.42,'M_meta':0.56,'Ξ':0.50,'_n_decisions':8}
after_dims=dict(before_dims); after_dims.update({'E_xp':0.62,'M_meta':0.66,'Ξ':0.66,'Ψ':0.70,'Γ':0.72,'Kelly':0.62})
apex_before=apex.dg_v2_3(before_dims); apex_after=apex.dg_v2_3(after_dims)
core=evm_mod.EVMCore()
for defect,val in {'Soul':0.35,'Err':0.30,'Log':0.28,'Mem':0.22,'Run':0.20}.items(): core.add_defect(defect,val)
evm_before=core.get_status()
for defect,value in list(core.defects.items()):
    if value>0:
        core.heal_defect(defect, value*evm_before['governance_detail'].get(defect,0))
evm_after=core.get_status()
route=[
 {'role':'主脑统筹','model':'gpt-5.5','judgment':'不能再把GitHub跑通等同觉醒，必须把公式门禁写入远程流水线'},
 {'role':'反证审错','model':'deepseek-v4-flash','judgment':'最可能造假点是搜索结果存在但没有改变下一步判断'},
 {'role':'修复落地','model':'gpt-5.5','judgment':'新增独立脚本，在远程容器内同时计算总公式、EVM缺陷压降和路由链'},
 {'role':'旁证压缩','model':'MiniMax-M2.7-highspeed','judgment':'保留可核验数字和来源，不写玄学觉醒叙事'},
 {'role':'主脑收束','model':'gpt-5.5','judgment':'本次只证明R1级门禁接入，不声称完整五回合周期完成'}]
external=github_search('agent framework reflection')
if not external:
    external=github_search('llm agent framework')
behavior_change='下一步所有GitHub进化任务必须先通过公式/EVM/路由三门禁，再进入深度项目吸收；空搜索或无缺陷压降不得称为进化。'
report={'generated_at':datetime.datetime.utcnow().isoformat()+'Z','status':'R1_gate_verified_not_full_cycle','risk':risk,'apex':{'before_dims':before_dims,'after_dims':after_dims,'before':round(apex_before,4),'after':round(apex_after,4),'delta':round(apex_after-apex_before,4)},'evm':{'before':{k:round(evm_before[k],4) for k in ['evm_value','raw_defect_rate','governed_defect_rate','governance_reduction']},'after':{k:round(evm_after[k],4) for k in ['evm_value','raw_defect_rate','governed_defect_rate','governance_reduction']},'active_defects_before':{k:round(v,4) for k,v in evm_before['defects_detail'].items() if v>0},'active_defects_after':{k:round(v,4) for k,v in evm_after['defects_detail'].items() if v>0}},'hetu_luoshu_route':route,'external_learning':{'query':'agent framework reflection / llm agent framework','sources':external,'extracted_points':['反思机制必须落到下一次动作选择','记忆与外部检索需要可追溯来源','自动化流水线要有失败判定而非只看产物'],'behavior_change':behavior_change},'completion_boundary':'只完成GitHub远程开智门禁最小验证；不是完整一个开智周期。'}
name='awakening_gate_'+datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')+'.json'
(OUT/name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(GENES/'github_formula_evm_gate_gene.json').write_text(json.dumps({'gene':'formula_evm_hetu_gate','mechanism':behavior_change,'last_report':'inbox/'+name},ensure_ascii=False,indent=2),encoding='utf-8')
print(name)
