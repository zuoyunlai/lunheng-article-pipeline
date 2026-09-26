#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ci_config.py — CI 判据与测试依赖真源的机械锁（v2.12.62 后补，教训 #430）

背景（2026-09-19 实测，v2.12.62 发版后发现）：
  `ci-test.yml` 的「跑权限口径 + 流程图真源测试」步骤**连续 30 次失败**、跨 3 天、
  覆盖 10+ 个版本发布。根因两条，各自独立且都可机械检出：
    ① **测试依赖真源缺项**：`test_flow_check.py` 等在 collection 阶段 `import yaml`，
       而 `ci-test.yml` 的安装步骤只装 `tests/requirements-test.txt` —— 该文件当时
       并未声明 pyyaml（pyyaml 只在 requirements.txt 里）。
    ② **CI 跑子集 ≠ 本地全量**：该 job 只跑 3 个文件 ⇒ 此后新增的测试（本批的
       test_bulk_ratchet.py / test_gate_h_reverse_diff.py …）**永不进 CI 判据**。
  更隐蔽的是：同一份代码在 `quality.yml`（装两份 requirements + 跑全量）下是**绿的**
  ⇒ **绿灯幻觉**：红的那条没人点开，发版照走。

本文件把上面两条钉成不变量（任一违反即红）：
  A. `tests/*.py` 顶层导入的第三方模块 ⇒ 必须声明在 `tests/requirements-test.txt`
     （测试依赖**自己声明齐**，不靠另一份文件兜底）。
  B. 同一包若两份 requirements 都声明 ⇒ 版本必须一致（防两份锁定文件漂移）。
  C. `ci-test.yml` 的安装步骤必须**两份全装**（与 quality.yml / 门 N 口径一致）。
  D. `ci-test.yml` 必须包含跑**全量** `tests/` 的步骤（子集不构成 CI 判据）。
  E. workflow 里引用的 `scripts/<name>` 必须真实存在（防「workflow 调已删脚本」）。
F. workflow 的仓库内路径过滤器必须真实存在（防目录重组后 PR 不触发 CI）。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
WORKFLOWS = ROOT / ".github" / "workflows"
REQ_MAIN = ROOT / "requirements.txt"
REQ_TEST = ROOT / "tests" / "requirements-test.txt"
CI_TEST = WORKFLOWS / "ci-test.yml"

# 允许出现在 tests/ 但不必进 requirements 的名字：本仓脚本模块 / 测试自带 helper
_LOCAL_MODULE_HINTS = ("conftest",)

# **导入名 ≠ 分发包名** 的映射（本缺陷的隐蔽处之一：`import yaml` 对应 PyPI 包 `pyyaml`，
#   直接拿 import 名去 requirements 里找会「找不到」或反向漏判）。需要时在此登记。
_IMPORT_TO_DIST = {
    "yaml": "pyyaml",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "yaml_": "pyyaml",
}


def _declared(path: Path) -> dict:
    """requirements 文件 → {包名小写: 版本串}；注释与空行忽略，未锁定版本直接报错。"""
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        assert "==" in line, f"{path.name} 存在未锁定版本的依赖：{raw!r}（门 N 同口径）"
        name, ver = line.split("==", 1)
        out[name.strip().lower().replace("_", "-")] = ver.strip()
    return out


def _third_party_imports() -> set:
    """tests/*.py 顶层 import 的第三方模块名（排除标准库与本仓本地模块）。"""
    stdlib = set(sys.stdlib_module_names)
    local = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    local |= {p.stem for p in TESTS.glob("*.py")}
    local |= set(_LOCAL_MODULE_HINTS)
    found = set()
    pat = re.compile(r"^(?:import\s+([A-Za-z_][\w.]*)|from\s+([A-Za-z_][\w.]*)\s+import\s)", re.M)
    for f in sorted(TESTS.glob("*.py")):
        for m in pat.finditer(f.read_text(encoding="utf-8")):
            mod = (m.group(1) or m.group(2)).split(".")[0]
            if mod in stdlib or mod in local or mod.startswith("_"):
                continue
            found.add(mod)
    return found


def test_a_test_deps_declared_in_test_requirements():
    """A：tests/ 顶层导入的第三方模块必须声明在 tests/requirements-test.txt。

    即本次 CI 事故的直接根因（`import yaml` 而该文件未声明 pyyaml，
    而某个 CI job 只装这一份文件 ⇒ collection error）。
    """
    declared = _declared(REQ_TEST)
    missing = []
    for mod in sorted(_third_party_imports()):
        dist = _IMPORT_TO_DIST.get(mod, mod).lower().replace("_", "-")
        if dist not in declared:
            missing.append(f"{mod}（分发包 {dist}）")
    assert not missing, (
        f"tests/requirements-test.txt 未声明测试实际导入的第三方模块：{missing} —— "
        f"只装本文件的 CI job 会在 collection 阶段直接报 ModuleNotFoundError（教训 #430）")


def test_b_two_requirement_files_agree_on_versions():
    """B：两份锁定文件对同一包必须给出同一版本（防漂移成两份真相）。"""
    main, test = _declared(REQ_MAIN), _declared(REQ_TEST)
    drift = {k: (main[k], test[k]) for k in set(main) & set(test) if main[k] != test[k]}
    assert not drift, f"两份 requirements 版本不一致（漂移）：{drift}"


def test_c_ci_test_installs_both_requirement_files():
    """C：ci-test.yml 的 CI job 必须两份 requirements 全装（与 quality.yml / 门 N 对齐）。"""
    text = CI_TEST.read_text(encoding="utf-8")
    assert "tests/requirements-test.txt" in text, "ci-test.yml 未安装测试依赖"
    assert "requirements.txt" in text.replace("tests/requirements-test.txt", ""), (
        "ci-test.yml 只装测试依赖、未装 requirements.txt —— 运行时依赖面在 CI 中缺失（教训 #430 根因之一）")


def test_d_ci_test_runs_full_suite():
    """D：ci-test.yml 必须跑**全量** tests/（子集步不构成 CI 判据）。"""
    text = CI_TEST.read_text(encoding="utf-8")
    assert re.search(r"pytest\s+tests/\s", text) or "pytest tests/ -q" in text, (
        "ci-test.yml 未跑全量 tests/ —— 新增测试永不进 CI 判据（教训 #430 根因之二）")


def test_g_ci_runs_path_canonical_suite():
    """G：路径边界判据必须被 CI 执行，而不是仅靠手动脚本。"""
    text = CI_TEST.read_text(encoding="utf-8")
    assert "scripts/test-path-canonical.sh" in text


def test_h_quality_runs_changelog_check():
    """H：quality workflow 与 make all 同样执行 changelog 完整性检查。"""
    text = (WORKFLOWS / "quality.yml").read_text(encoding="utf-8")
    assert "scripts/changelog-check.py --check" in text


def test_i_changelog_workflow_watches_references():
    """I：引用真源变更必须触发 changelog 相关检查。"""
    text = (WORKFLOWS / "changelog-check.yml").read_text(encoding="utf-8")
    assert "'references/**'" in text


def test_e_workflow_script_references_exist():
    """E：workflow 里引用的 scripts/<name> 必须真实存在（防静默调用已删脚本）。"""
    missing = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        # 负向后顾：排除 `.../skill-creator/scripts/quick_validate.py` 这类**外部路径**
        #   （官方校验器住在 npm 全局目录，不是本仓脚本）。
        for name in sorted(set(re.findall(r"(?<![/\w])scripts/([A-Za-z0-9_.-]+\.(?:sh|py))",
                                         wf.read_text(encoding="utf-8")))):
            if not (ROOT / "scripts" / name).is_file():
                missing.append(f"{wf.name} → scripts/{name}")
    assert not missing, f"workflow 引用了不存在的脚本：{missing}"


def test_f_workflow_path_filters_exist():
    """F：workflow 的 paths 过滤器不能引用目录重组前已删除的路径。"""
    missing = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        # 只检查仓库内明确的相对路径；排除 glob 的尾部通配和 actions/ 等外部引用。
        for raw in re.findall(r"^\s*-\s*['\"]([^'\"]+)['\"]\s*$", text, re.M):
            path = raw.rstrip("*")
            if not path or path.startswith(("http://", "https://", ".github/")):
                continue
            if "**" in raw or "*" in raw:
                # 取第一个 glob 段之前的静态祖先目录，而不是对完整 glob
                # 调 Path.exists()（例如 references/**/*.md 的 parent 不是 references）。
                static_parts = []
                for part in Path(raw).parts:
                    if "*" in part or "?" in part or "[" in part:
                        break
                    static_parts.append(part)
                parent = Path(*static_parts) if static_parts else Path(".")
                if not (ROOT / parent).exists():
                    missing.append(f"{wf.name} → {raw}")
            elif (ROOT / path).exists() is False:
                # 仅把看起来像仓库路径的条目纳入检查，避免误判 action 参数。
                if "/" in path or path.endswith((".md", ".yml", ".yaml", ".py", ".sh")):
                    missing.append(f"{wf.name} → {raw}")
    assert not missing, f"workflow paths 引用了不存在的仓库路径：{missing}"
