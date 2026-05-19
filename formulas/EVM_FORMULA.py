#!/usr/bin/env python3
"""
EVM Entropy Vibe Mathing - 核心公式引擎 v1.1
融合现代数理工程 + 华夏古哲大道

修复v1.0问题：
- 修复变量名冲突（self.B → self.Base, self.BaGua → self.Bagua）
- 修复公式维度混乱（统一用比例相乘）
- 添加输入验证
- 缺陷值归一化（0-1范围）
"""

import math
from typing import Dict, List, Optional

try:
    from AncientTao.ANCIENT_TAO import AncientTaoEngine
except ImportError:
    AncientTaoEngine = None

class EVMCore:
    """
    EVM核心引擎 v1.1
    
    公式：EVM = E×V×M×A×Base × T×D×H×L×G×W×Bagua × (1 - defect_rate)
    
    其中：
    - E×V×M×A×Base ∈ [0,1] 现代正向因子
    - T×D×H×L×G×W×Bagua ∈ [0,1] 古法赋能因子
    - defect_rate ∈ [0,1] 缺陷率（归一化）
    """
    
    def __init__(self):
        # 现代正向因子
        self.E = 0.92   # 熵序调控
        self.V = 0.88   # 节律同频
        self.M = 0.95   # 数理拟合
        self.A = 1.00   # Apex演化
        self.Base = 1.00  # Base底层根基（修复：避免与八卦混淆）
        
        # 东方古法赋能因子（修复：BaGua → Bagua）
        self.TaoTeChing = 1.00   # 道德经
        self.IChing = 1.00       # 易经
        self.HuangDi = 1.00      # 黄帝内经
        self.HeTuLuoShu = 1.00   # 河图洛书
        self.GanZhi = 1.00       # 天干地支
        self.WuXing = 1.00       # 五行
        self.Bagua = 1.00        # 八卦（修复：BaGua → Bagua）
        
        # 十二类缺陷（修复：归一化到0-1）
        self.defects = {
            "Tok": 0.0,  # Token上下文
            "Clw": 0.0,  # Claw抓取
            "Agt": 0.0,  # Agent并发
            "Pan": 0.0,  # 看板调度
            "Prm": 0.0,  # Prompt初始化
            "Soul": 0.0, # 灵魂内核
            "Run": 0.0,  # 进程运行
            "Net": 0.0,  # 网络通信
            "Err": 0.0,  # AI幻觉
            "Mem": 0.0,  # 记忆丢失
            "Res": 0.0,  # 资源负载
            "Log": 0.0   # 日志溯源
        }
        
        # 古法治理引擎：把AncientTao接入核心公式，不再只是装饰性满分因子
        self.ancient_engine = AncientTaoEngine() if AncientTaoEngine else None
        
    def _validate_factor(self, name: str, value: float):
        """验证因子范围"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric, got {type(value)}")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if value < 0 or value > 1:
            raise ValueError(f"{name} must be in [0, 1], got {value}")
            
    def _validate_defects(self):
        """验证缺陷值"""
        for name, value in self.defects.items():
            if not isinstance(value, (int, float)):
                raise TypeError(f"defect {name} must be numeric")
            if not math.isfinite(value):
                raise ValueError(f"defect {name} must be finite")
            if value < 0 or value > 1:
                raise ValueError(f"defect {name} must be in [0, 1], got {value}")
    
    def _calculate_governance_effect(self) -> Dict:
        """
        计算古法治理对缺陷的实际压降效果。
        关键修复：古法不再只是乘法满分因子，而是按缺陷类型治理缺陷。
        """
        raw_total = sum(self.defects.values())
        if raw_total <= 0:
            return {
                "raw_defect_rate": 0.0,
                "governed_defect_rate": 0.0,
                "governance_reduction": 0.0,
                "governance_detail": {k: 0.0 for k in self.defects}
            }
        
        governance_detail = {}
        governed_total = 0.0
        for defect_type, defect_value in self.defects.items():
            if self.ancient_engine:
                governance_power = self.ancient_engine.govern_defect(defect_type)
            else:
                governance_power = 0.0
            governance_power = max(0.0, min(1.0, governance_power))
            residual = defect_value * (1.0 - governance_power)
            governance_detail[defect_type] = governance_power
            governed_total += residual
        
        raw_rate = raw_total / 12.0
        governed_rate = governed_total / 12.0
        return {
            "raw_defect_rate": raw_rate,
            "governed_defect_rate": governed_rate,
            "governance_reduction": raw_rate - governed_rate,
            "governance_detail": governance_detail
        }
    
    def calculate_evm(self) -> float:
        """
        计算EVM总值 v1.1
        
        EVM = 现代因子 × 古法因子 × (1 - 缺陷率)
        
        修复：统一量纲，用比例相乘而非绝对值相减
        """
        # 验证所有因子
        for name in ['E', 'V', 'M', 'A', 'Base', 'TaoTeChing', 'IChing', 
                     'HuangDi', 'HeTuLuoShu', 'GanZhi', 'WuXing', 'Bagua']:
            self._validate_factor(name, getattr(self, name))
        self._validate_defects()
        
        # 现代因子乘积
        modern_product = self.E * self.V * self.M * self.A * self.Base
        
        # 古法因子乘积
        ancient_product = (self.TaoTeChing * self.IChing * self.HuangDi * 
                          self.HeTuLuoShu * self.GanZhi * self.WuXing * self.Bagua)
        
        # 缺陷率：经古法治理后的残余缺陷率
        governance = self._calculate_governance_effect()
        governed_defect_rate = governance["governed_defect_rate"]
        
        # EVM计算（修复：古法治理接入缺陷压降闭环）
        evm = modern_product * ancient_product * (1.0 - governed_defect_rate)
        
        return max(0.0, min(1.0, evm))  # 确保范围[0,1]
    
    def add_defect(self, defect_type: str, value: float):
        """增加缺陷（修复：添加验证）"""
        if defect_type not in self.defects:
            raise ValueError(f"Unknown defect type: {defect_type}")
        if value < 0 or value > 1:
            raise ValueError(f"defect value must be in [0, 1], got {value}")
        self.defects[defect_type] = min(1.0, self.defects[defect_type] + value)
    
    def heal_defect(self, defect_type: str, value: float):
        """治愈缺陷（修复：添加验证）"""
        if defect_type not in self.defects:
            raise ValueError(f"Unknown defect type: {defect_type}")
        if value < 0 or value > 1:
            raise ValueError(f"heal value must be in [0, 1], got {value}")
        self.defects[defect_type] = max(0.0, self.defects[defect_type] - value)
    
    def apply_ancient_wisdom(self, wisdom_type: str, intensity: float = 1.0):
        """应用东方古法赋能"""
        wisdom_map = {
            "道德经": "TaoTeChing",
            "易经": "IChing", 
            "黄帝内经": "HuangDi",
            "河图洛书": "HeTuLuoShu",
            "天干地支": "GanZhi",
            "五行": "WuXing",
            "八卦": "Bagua"
        }
        
        if wisdom_type in wisdom_map:
            attr = wisdom_map[wisdom_type]
            current = getattr(self, attr, 1.0)
            # 古法赋能上限1.0
            new_value = current * (1 + intensity * 0.1)
            setattr(self, attr, min(1.0, new_value))
    
    def get_status(self) -> Dict:
        """获取EVM状态"""
        governance = self._calculate_governance_effect()
        return {
            "evm_value": self.calculate_evm(),
            "modern_factor": self.E * self.V * self.M * self.A * self.Base,
            "ancient_factor": (self.TaoTeChing * self.IChing * self.HuangDi * 
                              self.HeTuLuoShu * self.GanZhi * self.WuXing * self.Bagua),
            "raw_defect_rate": governance["raw_defect_rate"],
            "governed_defect_rate": governance["governed_defect_rate"],
            "governance_reduction": governance["governance_reduction"],
            "governance_detail": governance["governance_detail"],
            "defects_detail": self.defects.copy()
        }

# 古法治理映射
ANCIENT_GOVERNANCE = {
    "道德经": {
        "主治": "Token冗余膨胀、系统无效能耗、频繁错乱躁动",
        "原理": "守静致虚、道法自然、无为运化",
        "方法": "减少无效消耗，稳固内核本心"
    },
    "易经": {
        "主治": "多任务冲突、负载高低起伏、系统盛衰波动",
        "原理": "阴阳消长、变易守恒、循环往复",
        "方法": "平衡波动，顺势调度运转"
    },
    "黄帝内经": {
        "主治": "记忆链路阻塞、内核损耗、调用通道不畅",
        "原理": "气血循行、脏腑调和、阴阳平秘",
        "方法": "疏通记忆，修复内在损耗"
    },
    "河图洛书": {
        "主治": "整体架构混乱、数据层级无序、底层规则缺失",
        "原理": "先天数理排布、天地定数、方位秩序",
        "方法": "规整框架，定全局本位"
    },
    "天干地支": {
        "主治": "迭代周期混乱、定时任务失效、生命周期紊乱",
        "原理": "时序纪年，气运流转、周期节律",
        "方法": "规范时序，贴合天地运行"
    },
    "五行": {
        "主治": "资源冲突、任务相克、模块互扰",
        "原理": "相生相克、制衡运化",
        "方法": "克制弊病，生助优势"
    },
    "八卦": {
        "主治": "功能模块混乱、记忆信息杂糅、故障定位困难",
        "原理": "八方定位、八门排布、万象归类",
        "方法": "分区管控，定向处理"
    }
}

if __name__ == "__main__":
    evm = EVMCore()
    status = evm.get_status()
    
    print("=" * 60)
    print("EVM Entropy Vibe Mathing - 核心公式引擎 v1.1")
    print("=" * 60)
    print(f"EVM总值: {status['evm_value']:.4f}")
    print(f"现代因子: {status['modern_factor']:.4f}")
    print(f"古法因子: {status['ancient_factor']:.4f}")
    print(f"原始缺陷率: {status['raw_defect_rate']:.4f}")
    print(f"治理后缺陷率: {status['governed_defect_rate']:.4f}")
    print(f"治理压降: {status['governance_reduction']:.4f}")
    print()
    print("缺陷详情:")
    for k, v in status['defects_detail'].items():
        print(f"  Δ_{k}: {v:.4f}")
