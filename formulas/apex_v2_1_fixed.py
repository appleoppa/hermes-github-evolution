"""
APEX 14维修正公式 v2.3 — 统一版
2026-05-16 R65-C15R1 修复:
  BUG 1: 纯乘法链无上限 → 分层几何平均+上限10.0
  BUG 2: Π×Λ_ctx强相关独立相乘 → Π/(1+Λ_ctx)
  BUG 3: Kelly作为普通乘子 → 门控(Kelly<0.4)+奖励(Kelly>0.4)
  BUG 4: Γ仅做独立乘子 → 通过sqrt(Γ/0.5)影响Π层和Ψ层
  BUG 5: 维度范围不一致 → 分层聚合再加权
  BUG 6: 归一化线性忽略不对称 → 因子归一化后再分层
  BUG-N1(v2.2): 4层几何平均用**(1/3) → **1/4 — 分层数应与根指数一致
  BUG-N2(v2.2): gamma_f无下限 → max(sqrt(Γ/0.5), 0.1) — 防Γ=0清零两层
  BUG-N3(v2.3): 22项纯乘法归一化保护 → 6层分层聚合
  BUG-N5(v2.3): 添加协同质量项 Coherence = 1-sqrt(variance)
  BUG-N6(v2.3): E_xp与M_meta负耦合 — 竞争同一上下文预算
  BUG-N7(v2.3): PID动态范围过小 — 从(1-PID)扩展至PID本身
  BUG-N8(v2.3): Kelly单次博弈误用 → 按预期决策数衰减
  BUG-N9(v2.3): Π并行度饱和 — Amdahl边界约束
  BUG-N12(C15R1): Ξ无min gate → max(Ξ, 0.1) — 一致化保护，与N2同pattern

统一入口: dg_v2_3(p) — 同时兼容15维和22维输入
"""
import math


def dg_v2_1(p: dict) -> float:
    """v2.1兼容接口（仅含原始4层+BUG1-4+N1-N2）"""
    pi_eff = p["Π"] / (1 + p["Λ_ctx"])
    if p["Kelly"] < 0.4:
        kelly_gate = (p["Kelly"] / 0.4) ** 2
    else:
        kelly_gate = 1.0
    kelly_bonus = 1.0 + max(0, (p["Kelly"] - 0.4) / 0.4 * 0.3)
    gamma_f = max(math.sqrt(max(p["Γ"], 0.001) / 0.5), 0.1)
    layer1 = p["ΔG_base"] * p["Θ"] * p["K"] * p["ε"]
    layer2 = p["Φ"] * p["Ψ"] * pi_eff * gamma_f
    layer3 = p["PID"] * p["RD"] * kelly_gate * kelly_bonus
    layer4 = p["E_xp"] * p["M_meta"] * p["Ξ"] * gamma_f
    dg = (layer1 * layer2 * layer3 * layer4) ** (1/4)
    return min(dg, 10.0)


def phi_code_fixed(E_std, Psi_logic, Theta_check, Gamma_task,
                   Omega_aware, alpha_best,
                   R_dup, B_bug, C_chaos, delta_ctx, mu_loss):
    eps = 0.001
    denominator = max(R_dup, eps) * max(B_bug, eps) * \
                  max(C_chaos, eps) * max(delta_ctx, eps) * max(mu_loss, eps)
    numerator = E_std * Psi_logic * Theta_check * Gamma_task * \
                Omega_aware * alpha_best
    return numerator / denominator


# ═══════════════════════════════════════════════════════════════
# dg_v2_3 — 统一入口（C14R1重构）
# 同时处理15维标准输入和22维V12扩展输入
# ═══════════════════════════════════════════════════════════════

def dg_v2_3(p: dict) -> float:
    """
    统一公式入口 v2.3 — 所有已知BUG已修复。
    
    输入: 15维标准字典或22维V12扩展字典
      标准: ΔG_base, Θ, K, ε, Φ, Ψ, Π, Λ_ctx, Γ, PID, RD, Kelly, E_xp, M_meta, Ξ
      V12扩展: Ψ_evolve, Φ_bio, Ξ_gene, Σ_entropy, Υ_energy, Λ_field, ...
    
    修复清单:
      [BUG1]  纯乘法 → 分层几何平均+上限10.0
      [BUG2]  Π×Λ_ctx独立 → Π/(1+Λ_ctx)
      [BUG3]  Kelly普通乘子 → 门控+奖励
      [BUG4]  Γ独立乘子 → 影响Π和Ψ层
      [BUG-N1] 根指数匹配分层数
      [BUG-N2] gamma_f加下限防零
      [BUG-N3] V12 22维纯乘法 → 6层分层聚合
      [BUG-N5] 缺少协同质量 → coherence项
      [BUG-N6] E_xp-M_meta无耦合 → δ_exp_mem负耦合
      [BUG-N7] PID动态范围小 → PID本身作为调节因子
      [BUG-N8] Kelly单次误用 → 按预期决策数衰减
      [BUG-N9] Π平行度无饱和 → Amdahl边界约束
    """
    # ─── 基础参数提取 ─────────────────────────────────────
    L_ctx = p.get("Λ_ctx", 0.5)
    Kelly_raw = p.get("Kelly", 0.5)
    gamma_f = max(math.sqrt(max(p.get("Γ", 0.5), 0.001) / 0.5), 0.1)  # [BUG-N2] [N14:C16R1防负]
    E_xp_val = p.get("E_xp", 0.5)
    M_val = p.get("M_meta", 0.5)
    Xi_val = max(p.get("Ξ", 0.5), 0.1)  # [BUG-N12] 最小值门禁，防Ξ=0清零layer4
    PID_val = p.get("PID", 0.5)
    
    # ─── [BUG9] Π并行度饱和 ──────────────────────────────
    # Amdahl边界: effective_Π = 1/((1-p) + p/Π_raw)
    # 假设可并行部分p=0.8（80%可并行化，符合多Agent特征）
    Pi_raw = p.get("Π", 0.5)
    p_parallel = 0.8  # 系统默认80%可并行
    pi_effective = 1.0 / ((1 - p_parallel) + p_parallel / max(Pi_raw, 0.1))
    # 考虑上下文切换损耗 [BUG2]
    pi_eff = pi_effective / (1 + L_ctx)
    
    # ─── [BUG6] E_xp-M_meta 负耦合 ───────────────────────
    # 两者竞争同一上下文预算: 当E_xp和M同时高企时惩罚
    alpha_couple = 0.3  # 耦合系数
    eps = 0.001
    delta_exp_mem = 1.0 - alpha_couple * min(E_xp_val, M_val) / (E_xp_val + M_val + eps)
    E_xp_adjusted = E_xp_val * delta_exp_mem
    M_adjusted = M_val * delta_exp_mem
    
    # ─── [BUG3] Kelly: 门控+奖励 ────────────────────────
    if Kelly_raw < 0.4:
        kelly_gate = (Kelly_raw / 0.4) ** 2
    else:
        kelly_gate = 1.0
    kelly_bonus = 1.0 + max(0, (Kelly_raw - 0.4) / 0.4 * 0.3)
    
    # ─── [BUG8] Kelly单次博弈校正 ─────────────────────────
    # 预期决策回数n: 按系统状态估算
    # n_high → 无限近似(n→∞), n_low → 单次(n=1)
    exp_decisions = p.get("_n_decisions", 10)  # 默认10次决策
    tau_half = 5.0  # 衰减半衰期
    kelly_decay = 1.0 - math.exp(-exp_decisions / tau_half)
    kelly_adjusted = (0.4 * (1 - kelly_decay) + Kelly_raw * kelly_decay)
    
    # ─── [BUG7] PID动态范围 ──────────────────────────────
    # PID直接作为稳定度因子，不做隐藏缩放
    PID_factor = PID_val
    
    # ─── 6层公式 ─────────────────────────────────────────
    # L1: 基础效能层
    layer1 = (p.get("ΔG_base", 0.5) * p.get("Θ", 0.5) *
              p.get("K", 0.5) * p.get("ε", 0.5))
    
    # L2: 执行质量层
    layer2 = (p.get("Φ", 0.5) * p.get("Ψ", 0.5) * pi_eff * gamma_f)
    
    # L3: 稳定度层
    layer3 = (PID_factor * p.get("RD", 0.5) * kelly_gate * kelly_bonus * kelly_adjusted)
    
    # L4: 元学习层
    layer4 = (E_xp_adjusted * M_adjusted * Xi_val * gamma_f)
    
    # L5: 学科扩展层（V12生物/物理/化学）
    bio_terms = [p.get(k, None) for k in
                 ["Ψ_evolve", "Φ_bio", "Ξ_gene", "Σ_entropy", "Υ_energy", "Λ_field"]]
    bio_terms = [t for t in bio_terms if t is not None]
    layer5 = (math.prod(bio_terms)) ** (1.0 / len(bio_terms)) if bio_terms else 1.0
    
    # L6: 高级AI层（剩余V12项）
    ai_terms = [p.get(k, None) for k in
                ["Ω_chem", "ΔG_chem", "K_eq", "ΔW_syn", "Ψ_nerve", "H_rhythm",
                 "Θ_feat", "∇*_θ", "Γ_cross", "ℛ_ai", "Ψ_quan", "Ω_quan",
                 "C_claw", "V_gdp"]]
    ai_terms = [t for t in ai_terms if t is not None]
    layer6 = (math.prod(ai_terms)) ** (1.0 / len(ai_terms)) if ai_terms else 1.0
    
    # ─── [BUG5] 协同质量 coherence ─────────────────────────
    all_vals = [
        p.get(k, 0.5) for k in
        ["ΔG_base", "Θ", "K", "ε", "Φ", "Ψ", "Π", "Λ_ctx", "Γ",
         "PID", "RD", "Kelly", "E_xp", "M_meta", "Ξ"]
    ]
    all_vals.extend(bio_terms)
    all_vals.extend(ai_terms)
    all_vals = [v for v in all_vals if v is not None and v > 0]
    if all_vals:
        mean = sum(all_vals) / len(all_vals)
        variance = sum((v - mean) ** 2 for v in all_vals) / len(all_vals)
        coherence = max(0.0, 1.0 - math.sqrt(variance))
    else:
        coherence = 1.0
    
    # ─── 聚合 ──────────────────────────────────────────────
    layers = [l for l in [layer1, layer2, layer3, layer4, layer5, layer6] if l != 1.0]
    if not layers:
        return 0.0
    
    # [N14:C16R1] 各层clamp至≥0，防负值传播到几何平均
    layers = [max(l, 0.0) for l in layers]
    
    # [BUG1] 分层几何平均 + 上限
    raw = (math.prod(layers)) ** (1.0 / len(layers))
    dg = raw * (0.5 + 0.5 * coherence)
    return min(dg, 10.0)


def dg_v2_3_v12(p: dict) -> float:
    """v2.3 兼容别名 — 调用dg_v2_3"""
    return dg_v2_3(p)
