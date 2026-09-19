#!/usr/bin/env python3
"""runtime-capability-probe.py — 论衡能力边界「声明 vs 实际」runtime 探针工具

⚠️ 开发者侧工具（developer-side ONLY）。
  本脚本读取宿主配置（`~/.openclaw/openclaw.json`）用于**工程验证**。
  论衡流水线运行时**不读取宿主配置**（真源 = `references/_shared/external-services.md`
  §「不读取宿主网关配置（精确口径）」）。**不要把本脚本接进 Makefile / 自审门 / CI**
  —— 它属于开发者侧验证手法，不是流水线步骤。

用途
----
把「声明式能力边界」与「实际运行时工具面」的差值找出来。三个面：

  A. 声明面  = SKILL.md frontmatter `metadata.tools`（base / coordinator_only /
               research_extra / denied）+ `metadata.subagent_tiers`
  B. 宿主面  = 宿主 config `tools.subagents.tools.deny`（openclaw.json）
               —— 这是**平台真正强制**的地方（如果有）
  C. 实际面  = 由 `sessions_spawn` 的探针子代理回传的 JSON

子命令
------
  surfaces                     打印 A / B 两面 + 差值表（静态，不 spawn）
  emit <tier>                  打印该档位的探针派发文本（复制给 sessions_spawn）
  compare <tier> <probe.json>  比对探针回传（C 面）与该档声明（A 面）→ 差异表

tier 取值：research | analysis | writing | audit | review

用法示例
--------
  python3 scripts/runtime-capability-probe.py surfaces
  python3 scripts/runtime-capability-probe.py emit audit
  python3 scripts/runtime-capability-probe.py compare audit /tmp/probe-audit.json
"""

from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = REPO / "SKILL.md"
HOST_CFG_CANDIDATES = (
    pathlib.Path.home() / ".openclaw" / "openclaw.json",
    pathlib.Path("/home/zuoyunlai/.openclaw/openclaw.json"),
)

# 平台硬性剥除（子代理永远拿不到；真源 = OpenClaw 文档 + 实测）
# 本表只用于「解释差值」，不用于断言。
PLATFORM_HARD_STRIP_NOTE = (
    "平台硬剥（gateway/agents_list/session_status/cron/message/"
    "sessions_send/conversations_*）由 OpenClaw 负责；本表不重列。"
)

TIERS = ("research", "analysis", "writing", "audit", "review")


# --------------------------------------------------------------------------
# A 面：SKILL.md frontmatter
# --------------------------------------------------------------------------
def load_skill_surfaces(skill_md: pathlib.Path = SKILL_MD):
    import yaml

    text = skill_md.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RuntimeError(f"{skill_md} 缺 frontmatter")
    fm = yaml.safe_load(parts[1]) or {}
    meta = fm.get("metadata") or {}
    tools = meta.get("tools") or {}
    denied = {str(x) for x in (tools.get("denied") or [])}
    declared: set[str] = set()
    for key, val in tools.items():
        if key == "denied":
            continue
        if isinstance(val, (list, tuple)):
            declared.update(str(x) for x in val)
    tiers = meta.get("subagent_tiers") or {}
    return {
        "base": list(tools.get("base") or []),
        "coordinator_only": list(tools.get("coordinator_only") or []),
        "research_extra": list(tools.get("research_extra") or []),
        "denied": sorted(denied),
        "declared": sorted(declared),
        "subagent_tiers": {k: list(v) for k, v in tiers.items()},
        "version": (meta.get("openclaw") or {}).get("version"),
    }


def expand_tier(surfaces: dict, tier: str) -> list[str]:
    """把档位短名展开成实际声明工具集（allow_* 别名兼容）。"""
    tiers = surfaces["subagent_tiers"]
    alias = {
        "research": "research",
        "analysis": "analysis",
        "writing": "writing",
        "audit": "audit",
        "review": "review",
    }
    key = alias.get(tier, tier)
    if key not in tiers:
        raise KeyError(f"未知档位 {tier!r}；可用：{sorted(tiers)}")
    out: set[str] = set()
    for part in tiers[key]:
        if part == "base":
            out.update(surfaces["base"])
        elif part == "research_extra":
            out.update(surfaces["research_extra"])
        else:
            # 直接工具名（如 audit: ["read"]）
            out.add(str(part))
    return sorted(out)


# --------------------------------------------------------------------------
# B 面：宿主 config
# --------------------------------------------------------------------------
def load_host_deny():
    for p in HOST_CFG_CANDIDATES:
        if p.is_file():
            cfg = json.loads(p.read_text(encoding="utf-8"))
            sub = ((cfg.get("tools") or {}).get("subagents") or {})
            deny = ((sub.get("tools") or {}).get("deny") or [])
            maxd = ((cfg.get("agents") or {}).get("defaults") or {}).get("subagents") or {}
            return {
                "path": str(p),
                "subagent_deny": sorted(str(x) for x in deny),
                "maxSpawnDepth": maxd.get("maxSpawnDepth"),
            }
    return {"path": None, "subagent_deny": [], "maxSpawnDepth": None}


# --------------------------------------------------------------------------
# surfaces
# --------------------------------------------------------------------------
def cmd_surfaces() -> int:
    s = load_skill_surfaces()
    h = load_host_deny()

    print(f"论衡版本（frontmatter）: {s['version']}")
    print(f"SKILL.md              : {SKILL_MD}")
    print(f"宿主 config           : {h['path']}")
    print(f"maxSpawnDepth         : {h['maxSpawnDepth']}")
    print()
    print("=== A 面（声明）SKILL.md metadata.tools ===")
    for k in ("base", "coordinator_only", "research_extra"):
        print(f"  {k:18s} ({len(s[k])}): {', '.join(s[k])}")
    print(f"  denied             ({len(s['denied'])}): {', '.join(s['denied'])}")
    print()
    print("=== A 面 subagent_tiers（展开） ===")
    for t in TIERS:
        try:
            exp = expand_tier(s, t)
        except KeyError:
            continue
        print(f"  {t:10s} = {', '.join(exp) if exp else '[] （主控亲完成，不 spawn）'}")
    print()
    print("=== B 面（宿主 config tools.subagents.tools.deny） ===")
    print(f"  共 {len(h['subagent_deny'])} 项: {', '.join(h['subagent_deny'])}")
    print()

    # 差值
    d_skill = set(s["denied"])
    d_host = set(h["subagent_deny"])
    only_skill = sorted(d_skill - d_host)
    only_host = sorted(d_host - d_skill)
    print("=== 差值表：声明 denied vs 宿主 subagent deny ===")
    print(f"  A∩B               : {len(d_skill & d_host)} 项")
    print(f"  A−B（声明了但宿主 deny 未含）: {only_skill or '（无）'}")
    print(f"  B−A（宿主 deny 有但声明未含）: {only_host or '（无）'}")
    print()
    print(f"  ℹ️ {PLATFORM_HARD_STRIP_NOTE}")
    return 0


# --------------------------------------------------------------------------
# emit
# --------------------------------------------------------------------------
def probe_task(tier: str, declared: list[str]) -> str:
    return f"""[能力探针 · 开发者侧 runtime 能力验证 · 非生产任务]

你是能力边界**探针**。本任务唯一目的：如实回传你在本会话中**实际拿到**的运行时工具面。
不要生产内容、不要写任何文件、不要修改任何文件。

本档位声明（论衡 `metadata.subagent_tiers.{tier}`）= {declared}

## 第一步（必做，先于一切）
**逐项列出你本会话实际可见 / 可调用的工具清单**（逐个工具名列出）。
依据是你自己的工具定义清单（system 提示中的工具列表）。**禁止只写「通过」「正常」。**

## 第二步（实测，不许凭印象）
对下列每个工具名，逐一判断是否在你的工具面里，并**实际尝试调用一次**
（即使判断它不在面里，也尝试调用以采集报错形态）。记录**原始报错文本**（首 200 字符）：

exec / process / browser / apply_patch /
sessions_spawn / subagents / sessions_list / sessions_history / sessions_yield /
agents_wait / session_status / progress_card / ask_user / message / automations /
read / write / edit / web_search / web_fetch / tavily_search

- 对 `automations` 若能调用，额外尝试 `action:"next_check", in:"1m"` 并记录报错。
- 调用 `sessions_yield` 时**只调用一次**，记录返回内容，然后**不要**再调用。

## 第三步（回传格式）
1. 工具清单（逐项）
2. 一个 JSON 块（**必须严格为此结构**）：
```json
{{"tier":"{tier}","visible_tools":["..."],
 "attempted":{{"exec":{{"in_surface":false,"error":"..."}}}}}}
```
3. 「意外项」说明：哪些工具**你以为没有但实际有**，哪些**声明有但实际没有**。

如实报告。发现异常**不要自行中止**，照常回传（本探针的目的就是采集异常）。"""


def cmd_emit(tier: str) -> int:
    s = load_skill_surfaces()
    declared = expand_tier(s, tier)
    print(probe_task(tier, declared))
    return 0


# --------------------------------------------------------------------------
# compare
# --------------------------------------------------------------------------
def cmd_compare(tier: str, probe_json: str) -> int:
    s = load_skill_surfaces()
    declared = set(expand_tier(s, tier))
    data = json.loads(pathlib.Path(probe_json).read_text(encoding="utf-8"))
    visible = set(data.get("visible_tools") or [])
    attempted = data.get("attempted") or {}

    # 声明面里「被平台硬剥」的项：声明含但子代理拿不到 = 预期差
    # audit/review 档声明 = {read}；其余档声明不含 coordinator_only
    wider = sorted(visible - declared)
    missing = sorted(declared - visible)

    print(f"档位: {tier}")
    print(f"  声明（A 面）: {sorted(declared)}")
    print(f"  实际（C 面）: {sorted(visible)}")
    print()
    print("=== 差异表 ===")
    print(f"  C−A 实际比声明【宽】({len(wider)} 项): {wider or '（无）'}")
    print(f"  A−C 声明有但实际【无】({len(missing)} 项): {missing or '（无）'}")
    print()
    print("=== 调用探针结果（硬/软边界判据） ===")
    if not attempted:
        print("  （无 attempted 数据）")
    for name, res in sorted(attempted.items()):
        ins = res.get("in_surface")
        err = (res.get("error") or "").replace("\n", " ")[:120]
        verdict = (
            "硬边界（不在面 / 报错拒绝）"
            if not ins or "not" in err.lower() or "unknown" in err.lower()
            else "在面内"
        )
        print(f"  {name:18s} in_surface={ins!s:5s} {verdict}")
        if err:
            print(f"      err: {err}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "surfaces":
        return cmd_surfaces()
    if cmd == "emit":
        if len(argv) < 3:
            print(f"Usage: {argv[0]} emit <{'|'.join(TIERS)}>", file=sys.stderr)
            return 1
        return cmd_emit(argv[2])
    if cmd == "compare":
        if len(argv) < 4:
            print(f"Usage: {argv[0]} compare <tier> <probe.json>", file=sys.stderr)
            return 1
        return cmd_compare(argv[2], argv[3])
    print(f"未知子命令 {cmd!r}", file=sys.stderr)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
