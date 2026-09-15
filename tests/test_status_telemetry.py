#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_status_telemetry.py — 遥测收容四面一致性（v2.12.40，回应 ClawHub 扫描 T09）

背景：ClawHub 扫描（v2.12.39）判定 `suspicious`，唯一未闭合 unexpected 项 = T09——
  「在项目 status 文件里保留 session 标识符与账号/模型可用性遥测，**收容不足
  （without enough containment）**」。v2.12.39 的「遥测分级」只做到「不进交付说明」，
  未处理 status.md 自身的暴露面。

本测试锁死「收容四条」在四处（协议真源 / status 模板 / 归档 SOP / 交付说明）不漂移：
  ① 仅留 status.md　② 归档排除　③ 分享前脱敏　④ 保留期

设计原则（对齐教训 #177 / #334）：
  - 只验证「规则定义的结构一致性」，不依赖真实 LLM 调用；
  - **必中样本**：脱敏规则必须给出**可执行口径**（截断位数 / 哈希位数），
    只写「须脱敏」而无口径 = 不可执行，判失败。
"""
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
PROTOCOL = ROOT / "references" / "_shared" / "关键协议.md"
STATUS_TPL = ROOT / "references" / "templates" / "status-template.md"
ARCHIVE = ROOT / "references" / "_shared" / "project-archive-sop.md"
DELIVERABLES = ROOT / "references" / "deliverables.md"


def _read(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


def test_protocol_defines_telemetry_containment():
    """真源：关键协议须定义「遥测收容」四条"""
    t = _read(PROTOCOL)
    assert "遥测收容" in t, "关键协议缺 §遥测收容"
    assert "遥测收容不足" in t, "缺扫描来源标注（收容不足）"
    for kw in ("仅留", "归档排除", "分享前脱敏", "保留期"):
        assert kw in t, f"收容四条缺：{kw}"
    # 运行期遥测的界定必须点名这两类标识符
    assert "sessionKey" in t and "session id" in t, "缺会话标识符界定"


def test_status_template_carries_sensitivity_label():
    """status.md 模板：头部须有敏感标注 + 归档排除/脱敏指针"""
    t = _read(STATUS_TPL)
    assert "含运行期遥测" in t, "status 模板缺敏感标注"
    assert "敏感文件" in t, "缺「按敏感文件处理」口径"
    assert "status.redacted.md" in t, "缺脱敏副本名（归档排除的落地形态）"
    assert "归档" in t, "缺归档排除指针"


def test_archive_sop_excludes_status_md():
    """归档 SOP：默认排除 status.md，只留脱敏副本"""
    t = _read(ARCHIVE)
    assert "status.redacted.md" in t, "归档 SOP 缺脱敏副本名"
    assert "排除" in t and "status.md" in t, "归档 SOP 未声明排除 status.md"
    assert "脱敏" in t, "归档 SOP 缺脱敏要求"


def test_redaction_rule_has_executable_spec():
    """必中样本（教训 #334）：脱敏必须给可执行口径，不能只写「须脱敏」"""
    for path, name in ((PROTOCOL, "关键协议"), (STATUS_TPL, "status 模板"),
                       (ARCHIVE, "归档 SOP"), (DELIVERABLES, "交付说明")):
        t = _read(path)
        assert "前 8" in t, f"{name} 缺截断口径（前 8 字符）"
    t = _read(PROTOCOL)
    assert "哈希前 12" in t, "关键协议缺哈希备选口径"


def test_single_controller_l1_disclosure_is_declared():
    """单主控降级必须把 L1 独立性风险传递到交付说明，而不是只停留在 status 模板。"""
    status = _read(STATUS_TPL)
    deliverables = _read(DELIVERABLES)
    assert "单主控 L1 披露" in status, "status 模板缺单主控 L1 披露字段"
    assert "无法独立复核" in status, "status 模板缺 L1 风险文字"
    assert "单主控" in deliverables and "无法独立复核" in deliverables, \
        "交付说明真源缺单主控 L1 风险披露要求"


def test_deliverables_still_forbids_transcription():
    """回归：v2.12.39「禁止转录进交付说明」不得被 v2.12.40 收容改动覆盖掉"""
    t = _read(DELIVERABLES)
    assert "不得转录进" in t, "交付说明的转录禁止被破坏"
    assert "遥测分级" in t and "遥测收容" in t, "交付说明须同时承载分级与收容两段"
    # 交付说明侧不得出现具体遥测数值字段（成本指标仅 token/时长/模型组合）
    assert "不含宿主可见余额" in t, "成本指标字段的排除口径丢失"


def test_all_four_surfaces_agree_on_same_rule():
    """改 A 漏 B 防线：四处措辞必须指向同一套（脱敏副本名 + 档位符号）"""
    for path, name in ((PROTOCOL, "关键协议"), (STATUS_TPL, "status 模板"),
                       (ARCHIVE, "归档 SOP"), (DELIVERABLES, "交付说明")):
        t = _read(path)
        assert "status.redacted.md" in t, f"{name} 缺统一脱敏副本名"
        assert "✅/⚠️/❌" in t or "✅ / ⚠️ / ❌" in t, f"{name} 缺档位符号口径"


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  ✗ {fn.__name__}")
            traceback.print_exc()
    print(f"{len(fns) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
