#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_e1_evidence_objects.py — E1 证据对象与主张—证据链基础层一致性门（E1-2）

背景（AI4Scholar 启发·第一层修订方案，2026-09-22；实施 2026-09-24）：
  E1-0 落地三份基础资产（对象真源 + 证据登记模板 + 主张—证据映射模板），
  E1-1 在 T1/T3/T4/T7/T8 角色卡与派发话术中加入指针。本测试锁死四件事：

  ① 枚举无漂移：真源中 support_type / relation / snippet_kind / review_status
     枚举块逐字可解析，且模板 YAML 示例只用合法枚举值（防第二真源）；
  ② 路径一致：凡提及 E1 登记的活文档统一用 `research/evidence-register.md`
     与 `analysis/主张—证据映射.md`，并指回唯一真源（防各文件自造路径）；
  ③ 注册完整：三份新资产必须同时进 sync-version.sh 受管清单与净化包 manifest；
  ④ 边界保留：`full_text: unavailable` / `abstract_only` 示例必须原样保留；
     反向证据不得静默删除（模板含反向证据字段）；不得新增 G18 门编号。

  反向注入：在 tmp 副本上注入非法枚举值 / direct↔thematic 错配 ⇒ 校验器必须红
  （真源零写入，镜像 test_link_check 的副本变异风格，教训 #333 同族）。
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRUTH = ROOT / "references" / "_shared" / "真源" / "evidence-object-model.md"
REG_TMPL = ROOT / "references" / "templates" / "evidence-register-template.md"
MAP_TMPL = ROOT / "references" / "templates" / "claim-evidence-map-template.md"
SYNC = ROOT / "scripts" / "sync-version.sh"
PKG_MANIFEST = ROOT / "scripts" / ".pkg-manifest.txt"

REGISTER_PATH = "research/evidence-register.md"
MAP_PATH = "analysis/主张—证据映射.md"

# 触及 E1 的活文档面（角色卡 + 派发 + 模板 + 索引/词汇表）；
# 每个文件必须同时含「登记路径」与「真源指针」，缺一即半修（教训 #327/#336/#353）。
E1_WIRED_FILES = (
    "references/agents/01-文献检索-literature-scout.md",
    "references/agents/03-案例检索-case-scout.md",
    "references/agents/04-分析-analyst.md",
    "references/agents/07-审计-auditor.md",
    "references/agents/08-终检-final-inspector.md",
    "references/dispatch/T1-文献检索.md",
    "references/dispatch/T3-案例检索.md",
    "references/dispatch/T4-分析.md",
    "references/dispatch/T7-审计.md",
    "references/dispatch/T8-终检.md",
    "references/templates/交接报告-template.md",
    "references/templates/文献卡-template.md",
    "references/_shared/真源/glossary-core.md",
    "references/_shared/真源/asset-index.md",
)

SUPPORT_TYPES = {"direct", "indirect", "thematic", "counter_evidence", "identity_only"}
RELATIONS = {"directly_supports", "indirectly_supports", "contextualizes",
             "qualifies", "contradicts", "insufficient"}
SNIPPET_KINDS = {"title", "abstract", "body", "methods", "results",
                 "discussion", "conclusion", "metadata_only"}
REVIEW_STATUSES = {"unreviewed", "needs_human_review", "reviewed", "rejected"}


# --------------------------------------------------------------------------
# 工具：枚举块解析 + 模板 YAML 示例校验器（判据真源 = 本模块，机械可执行）
# --------------------------------------------------------------------------

def parse_enum_block(text: str, header: str) -> set:
    """从真源文本抽取 ```text 枚举块（以 header 行开头）内的合法值集合。"""
    m = re.search(rf"{re.escape(header)}[^`]*?```text\n(.*?)```", text, re.S)
    if not m:
        m = re.search(rf"{re.escape(header)}\s*```\n(.*?)```", text, re.S)
    assert m, f"真源缺枚举块：{header}"
    values = set(m.group(1).split())
    values = {v.strip("|") for v in values if v.strip("|")}
    return values


def yaml_enum_violations(text: str) -> list:
    """对文档中全部 YAML 块做枚举值核验，返回违规 (行内容, 原因) 列表。"""
    bad = []
    for block in re.findall(r"```yaml\n(.*?)```", text, re.S):
        for line in block.splitlines():
            line = line.strip()
            m = re.match(r"^(\w[\w.]*):\s*(\S+)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip("\"'")
            if key == "support_type" and val not in SUPPORT_TYPES:
                bad.append((line, f"support_type 非法值：{val}"))
            elif key == "relation" and val not in RELATIONS:
                bad.append((line, f"relation 非法值：{val}"))
            elif key == "snippet_kind" and val not in SNIPPET_KINDS:
                bad.append((line, f"snippet_kind 非法值：{val}"))
            elif key == "review_status" and val not in REVIEW_STATUSES:
                bad.append((line, f"review_status 非法值：{val}"))
    return bad


def direct_thematic_mismatch(text: str) -> list:
    """direct/thematic/indirect 错配核验（机械可判形态）：
    - support_type ∈ {indirect, thematic, identity_only} 的片段被映射 directly_supports ⇒ 命中
      （间接/主题/身份证据不得写成直接支持——方案 §十二「排序分数冒充证据强度」同族风险）
    - support_type=direct 的片段被映射 contextualizes/insufficient ⇒ 命中
    运行期语义判定归 T7；此处只锁登记表内可机械判定的形态。"""
    snippets = {}  # evidence_id -> support_type
    for block in re.findall(r"```yaml\n(.*?)```", text, re.S):
        em = re.search(r"^evidence_id:\s*(\S+)", block, re.M)
        sm = re.search(r"^support_type:\s*(\S+)", block, re.M)
        if em and sm:
            snippets[em.group(1)] = sm.group(1).strip("\"'")
    hits = []
    for block in re.findall(r"```yaml\n(.*?)```", text, re.S):
        cm = re.search(r"^evidence_id:\s*(\S+)", block, re.M)
        rm = re.search(r"^relation:\s*(\S+)", block, re.M)
        if not (cm and rm):
            continue
        ev, rel = cm.group(1), rm.group(1).strip("\"'")
        st = snippets.get(ev)
        if st is None:
            continue
        if st == "direct" and rel in ("contextualizes", "insufficient"):
            hits.append(f"{ev}: support_type=direct 却 relation={rel}")
        if st in ("indirect", "thematic", "identity_only") and rel == "directly_supports":
            hits.append(f"{ev}: support_type={st} 却 relation=directly_supports")
    return hits


# --------------------------------------------------------------------------
# ① 存在性 + 枚举无漂移
# --------------------------------------------------------------------------

def test_e1_assets_exist_and_stamped():
    for p in (TRUTH, REG_TMPL, MAP_TMPL):
        assert p.is_file(), f"缺 E1 基础资产：{p}"
        head = p.read_text(encoding="utf-8").split("\n", 3)
        assert any(l.startswith("> 版本：v") for l in head[:4]), \
            f"{p.name} 缺版本戳（须列入 sync-version.sh 受管清单）"


def test_truth_source_enum_blocks_match_normative_sets():
    text = TRUTH.read_text(encoding="utf-8")
    assert parse_enum_block(text, "`snippet_kind` 枚举") == SNIPPET_KINDS
    assert parse_enum_block(text, "`support_type` 枚举") == SUPPORT_TYPES
    assert parse_enum_block(text, "`relation` 枚举") == RELATIONS
    assert parse_enum_block(text, "`review_status` 枚举") == REVIEW_STATUSES


def test_templates_only_use_legal_enum_values():
    for p in (REG_TMPL, MAP_TMPL, TRUTH):
        bad = yaml_enum_violations(p.read_text(encoding="utf-8"))
        assert not bad, f"{p.name} YAML 示例含非法枚举：{bad}"


# --------------------------------------------------------------------------
# ② 路径与指针一致性（防半修：改一处、漏同源处）
# --------------------------------------------------------------------------

def test_wired_files_carry_register_path_and_truth_pointer():
    for rel in E1_WIRED_FILES:
        p = ROOT / rel
        assert p.is_file(), f"E1 接线清单指向不存在的文件：{rel}"
        text = p.read_text(encoding="utf-8")
        assert "evidence-object-model.md" in text, f"{rel} 缺唯一真源指针"
        if not rel.endswith(("glossary-core.md", "asset-index.md",
                             "文献卡-template.md")):
            assert REGISTER_PATH in text or "evidence-register" in text, \
                f"{rel} 缺登记表路径 {REGISTER_PATH}"


def test_e1_wiring_list_has_no_ghost_files():
    """接线清单本身不得漂移：每条都真实存在（防清单失效后静默通过，教训 #427）。"""
    ghosts = [rel for rel in E1_WIRED_FILES if not (ROOT / rel).is_file()]
    assert not ghosts, f"E1 接线清单含幽灵文件：{ghosts}"


# --------------------------------------------------------------------------
# ③ 注册完整：sync-version + 净化包 manifest + 索引
# --------------------------------------------------------------------------

def test_sync_version_manages_e1_assets():
    text = SYNC.read_text(encoding="utf-8")
    for rel in ("_shared/真源/evidence-object-model.md",
                "templates/evidence-register-template.md",
                "templates/claim-evidence-map-template.md"):
        assert rel in text, f"sync-version.sh 未纳管 E1 资产：{rel}"


def test_pkg_manifest_includes_e1_assets():
    text = PKG_MANIFEST.read_text(encoding="utf-8")
    for rel in ("references/_shared/真源/evidence-object-model.md",
                "references/templates/evidence-register-template.md",
                "references/templates/claim-evidence-map-template.md"):
        assert rel in text, f"净化包 manifest 缺 E1 资产：{rel}"


def test_asset_index_lists_e1_layer():
    text = (ROOT / "references/_shared/真源/asset-index.md").read_text(encoding="utf-8")
    assert "evidence-object-model.md" in text
    assert "evidence-register-template.md" in text
    assert "claim-evidence-map-template.md" in text


# --------------------------------------------------------------------------
# ④ 边界保留：unavailable / abstract_only / 反向证据 / 不新增 G18
# --------------------------------------------------------------------------

def test_unavailable_and_abstract_only_boundaries_preserved():
    reg = REG_TMPL.read_text(encoding="utf-8")
    assert "full_text: unavailable" in reg, "模板示例不得把全文可得性写成 available"
    assert "access_basis: abstract_only" in reg, "摘要级访问边界必须保留示例"
    truth = TRUTH.read_text(encoding="utf-8")
    for must in ("full_text: unavailable` 必须保留",
                 "不得编造定位信息",
                 "不得静默删除"):
        assert must in truth, f"真源缺边界条款：{must}"


def test_counter_evidence_survives_in_templates():
    reg = REG_TMPL.read_text(encoding="utf-8")
    assert "counter_evidence" in reg or "反向证据" in reg, "登记模板必须保留反向证据位"


def test_no_new_g18_gate_added():
    """方案明确：第一阶段不新增 G 门编号（复用 G15，T7 抽验不建 G18）。
    否定语境（「不新增 G18」「禁新增 G18」）是合规声明，不计入。"""
    hits = []
    negation = re.compile(r"不新增|禁新增|禁止新增|不立即新增")
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT)
        if any(part in (".git", "outputs", "reports", "memory", "__pycache__",
                        ".pytest_cache", "archive") for part in rel.parts):
            continue
        if ".bak." in p.name:
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if re.search(r"G\s*18", line) and not negation.search(line):
                hits.append(f"{rel}: {line.strip()}")
    assert not hits, f"出现 G18 字样（第一阶段禁新增 G 门）：{hits}"


# --------------------------------------------------------------------------
# ⑤ 反向注入（tmp 副本变异 ⇒ 必须红；真源零写入）
# --------------------------------------------------------------------------

def _inject(tmp_path: Path, src: Path, needle: str, replacement: str) -> Path:
    dst = tmp_path / src.name
    text = src.read_text(encoding="utf-8")
    assert needle in text, f"注入点不存在于 {src.name}：{needle}"
    dst.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    return dst


def test_injected_illegal_enum_is_caught(tmp_path):
    """注入 relation: proves_conclusively（非法枚举）⇒ yaml_enum_violations 必须报红。"""
    dst = _inject(tmp_path, REG_TMPL, "relation: indirectly_supports",
                  "relation: proves_conclusively")
    bad = yaml_enum_violations(dst.read_text(encoding="utf-8"))
    assert bad and any("proves_conclusively" in b[0] for b in bad), \
        f"非法 relation 枚举未被检出（校验器永真）：{bad}"


def test_injected_direct_relation_for_indirect_snippet_is_caught(tmp_path):
    """把登记表的 indirectly_supports 改成 directly_supports（E-001 实为
    abstract/indirect）⇒ 错配核验必须命中（间接证据不得写成直接支持）。"""
    reg_text = REG_TMPL.read_text(encoding="utf-8")
    assert not direct_thematic_mismatch(reg_text), "真源模板不应预存错配"
    dst = _inject(tmp_path, REG_TMPL, "relation: indirectly_supports",
                  "relation: directly_supports")
    hits = direct_thematic_mismatch(dst.read_text(encoding="utf-8"))
    assert hits and "indirect" in hits[0], f"indirect→direct 错配未被检出：{hits}"


def test_validator_flags_mismatch_pair_in_synthetic_register(tmp_path):
    """合成登记表：E-002 声称 thematic 却被 directly_supports ⇒ 错配核验必须命中。"""
    synthetic = tmp_path / "evidence-register.md"
    synthetic.write_text(
        "# 登记表\n```yaml\nrecord_type: fulltext_snippet\n"
        "evidence_id: E-002\nsupport_type: thematic\n```\n"
        "```yaml\nrecord_type: claim_evidence_link\n"
        "evidence_id: E-002\nrelation: directly_supports\n```\n",
        encoding="utf-8")
    hits = direct_thematic_mismatch(synthetic.read_text(encoding="utf-8"))
    assert hits and "thematic" in hits[0], f"direct/thematic 错配未被检出：{hits}"


def test_truth_source_untouched_by_injection(tmp_path):
    """护栏：注入只写 tmp 副本，真源 sha256 前后一致。"""
    import hashlib
    before = hashlib.sha256(REG_TMPL.read_bytes()).hexdigest()
    _inject(tmp_path, REG_TMPL, "relation: indirectly_supports",
            "relation: directly_supports")
    after = hashlib.sha256(REG_TMPL.read_bytes()).hexdigest()
    assert before == after, "真源被测试污染"
