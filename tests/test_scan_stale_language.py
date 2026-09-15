#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_scan_stale_language.py — 扫描器反复抓到的两类「stale 语言」机械门（v2.12.42 新增）

背景（2026-09-15 扫描核对，v2.12.41 实测）：
  A. G14 迁移收尾漏 5 处 —— 手工 grep 模式太窄（`Phase 0 显式勾选|同批并行|not_enabled`），
     asset-index / glossary / 投稿就绪检查表等派生文件仍在说「默认不启用；Phase 0 勾选启用」，
     SkillSpector 连续三版判 Intent-Code Divergence（97/95/95%）。
  B. 模型探测语言残留 —— 预算闸门/1-token ping 删除后，任何「派发前预检」表述都可能复活被
     实测否决或被裁决删除的机制。

本门锁死两类 stale 模式在可见面（SKILL.md + README + QUICKSTART + references/，排除
教训索引/设计文档/历史沿革注）零残留。教训：清扫必须配机械门，手工模式必然漏。
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent

# 可见面 = 净化包会携带的文件（与门 Q 同口径：排除教训索引 / 设计文档 / archive / CHANGELOG）
EXCLUDE_PARTS = ("教训索引", "设计文档", "/archive/", "lessons-max.snapshot")
EXCLUDE_NAMES = {"CHANGELOG.md"}


def _visible_files():
    for p in [ROOT / "SKILL.md", ROOT / "README.md", ROOT / "QUICKSTART.md"]:
        yield p
    for p in (ROOT / "references").rglob("*.md"):
        s = str(p)
        if any(x in s for x in EXCLUDE_PARTS) or p.name in EXCLUDE_NAMES:
            continue
        yield p


def _stale_g14_hits(text: str):
    """G14 已迁 Phase 4.4 前置、目标语言客观适用、只审一次 —— 旧可选/旧位置语言即 stale。"""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if "G14" not in line and "中文 AI 痕迹" not in line:
            continue
        # 豁免：历史沿革注 / 迁移说明 / 明确的「已删/不再是/取消可选」定案句
        if re.search(r"已删|已废|不再是|取消可选|迁至|迁出|已移除|v2\.12\.4|定案|整体作废|历史", line):
            continue
        # stale 模式 ①：可选/勾选/默认关闭 类
        #   豁免「Warning 预授权」——那是 Warning 处置预授权（A/B/C 选项），非闸门启用开关
        if "预授权" in line:
            pass
        elif re.search(r"G14[^。]*?(勾选|默认不启用|默认关闭)|（勾选[^）]*G14|(可选[^。]*G14 闸)", line):
            hits.append((i, "旧可选语言", line.strip()[:90]))
        # stale 模式 ②：旧位置/旧轮次（Phase 3.6 同批 / 修订 2 轮）
        #   豁免：含新位置标记（4.4 前置/已解耦/单独运行/只处理 T6/只审一次）或迁移说明（迁）的对照句
        if re.search(r"G14[^。]*?(Phase 3\.6|同批并行)|同批并行[^。]*G14", line):
            if not re.search(r"迁|4\.4 前置|已解耦|单独运行|只处理 T6|只审一次", line):
                hits.append((i, "旧位置语言", line.strip()[:90]))
    return hits


def _stale_probe_hits(text: str):
    """v2.12.42 裁决：全删派发前探测 —— 预算闸门/1-token ping/余额预检语言即 stale。"""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"已删|取代|不再|v2\.12\.42|原预算闸门|历史", line):
            continue
        if re.search(r"1-token ping", line):
            hits.append((i, "1-token ping 残留", line.strip()[:90]))
        if re.search(r"预算闸门", line) and not re.search(r"删|取代|不再", line):
            hits.append((i, "预算闸门复活", line.strip()[:90]))
        if re.search(r"派发[^。]*?(余额|配额)[^。]*?(预检|确认|检查)|宿主可见余额", line) \
                and not re.search(r"不[^。]*采集|不再", line):
            hits.append((i, "派发前余额预检复活", line.strip()[:90]))
    return hits


def test_no_stale_g14_language():
    bad = []
    for p in _visible_files():
        bad += [(f"{p.relative_to(ROOT)}:{ln}", kind, frag)
                for ln, kind, frag in _stale_g14_hits(p.read_text(encoding="utf-8"))]
    assert not bad, "G14 stale 语言残留（v2.12.42 收尾后应零残留）:\n" + \
        "\n".join(f"  {loc} [{kind}] {frag}" for loc, kind, frag in bad[:10])


def test_no_stale_probe_language():
    bad = []
    for p in _visible_files():
        bad += [(f"{p.relative_to(ROOT)}:{ln}", kind, frag)
                for ln, kind, frag in _stale_probe_hits(p.read_text(encoding="utf-8"))]
    assert not bad, "探测/预算闸门 stale 语言残留（v2.12.42 全删后应零残留）:\n" + \
        "\n".join(f"  {loc} [{kind}] {frag}" for loc, kind, frag in bad[:10])


def test_memory_reading_truly_removed():
    """checkpoint-card 模板不得再教主控读记忆（v2.12.35 已删记忆支持；2026-09-15 扫描 AIG T05 实证残留）。"""
    t = (ROOT / "references" / "templates" / "checkpoint-card-template.md").read_text(encoding="utf-8")
    assert "主控读记忆" not in t, "checkpoint-card 仍含「主控读记忆」（已删能力，安全发现）"
    assert "记忆读取" not in t, "checkpoint-card 仍把「记忆读取」列为可选服务（已删能力）"


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ✓ {fn.__name__}")
        except Exception:
            failed += 1; print(f"  ✗ {fn.__name__}"); traceback.print_exc()
    print(f"{len(fns) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
