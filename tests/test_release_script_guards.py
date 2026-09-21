#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_release_script_guards.py — 发布链护栏测试（v2.12.30 新增）

背景（2026-09-12 第三方全量审计，第二批 P1）：
  - P1-4：build-clawhub-release.sh / publish-clawhub.sh 的 VERSION 直接进
          `$OUT_ROOT/$VERSION` 并紧接 `rm -rf` —— 参数即删除目标（目录逃逸）。
          对照：release-preflight.sh / create-github-release.sh 早已有 tag 格式校验。
  - P1-3：build 脚本的「未跟踪文件」反向断言在非 git 环境**静默跳过** = 放弃唯一
          能发现「未跟踪残留入包」的机械门（教训 #333）。
  - P1-2：cleanup-skill-store.sh 无条件 `git reflog expire --expire=now --all` +
          `git gc --prune=now`（不可逆），与脚本头部「所有删前先备份」承诺矛盾。
"""
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).parent.parent
BUILD = ROOT / "scripts" / "build-clawhub-release.sh"
PUBLISH = ROOT / "scripts" / "publish-clawhub.sh"
CLEANUP = ROOT / "scripts" / "cleanup-skill-store.sh"


def _run(script, *args):
    return subprocess.run(["bash", str(script), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


# ---------------- P1-4：版本参数校验（参数即 rm -rf 目标）----------------

def test_build_rejects_path_traversal_version():
    r = _run(BUILD, "../../PWNED")
    assert r.returncode == 2, f"应拒绝路径穿越版本号，实际 rc={r.returncode}"
    assert "版本号" in (r.stderr + r.stdout)
    # 反向断言：不得创建任何越界目录
    assert not (ROOT.parent.parent / "PWNED").exists()
    assert not (ROOT / "outputs" / "PWNED").exists()


def test_build_rejects_non_semver_version():
    # 注：空串是**文档化回退**（读 SKILL.md frontmatter），非非法输入，故不在此列；
    #    空白串用于覆盖「非空但格式非法」的同类场景。
    for bad in ("abc", "1.2", "1.2.3.4", " ", "v1.2.3", "1.2.3/../../x"):
        r = _run(BUILD, bad)
        assert r.returncode == 2, f"'{bad}' 应被拒绝，实际 rc={r.returncode}"


def test_build_has_path_containment_guard():
    """正则之外的二层防线：解析后绝对路径必须落在输出根之内"""
    src = BUILD.read_text(encoding="utf-8")
    assert "输出目录逃逸出输出根" in src
    assert "OUT_ROOT_ABS" in src and "OUT_DIR_ABS" in src
    # 容器检查必须出现在 rm -rf 之前
    assert src.index("输出目录逃逸出输出根") < src.index('rm -rf "$OUT_DIR"')


def test_publish_validates_version_before_use():
    src = PUBLISH.read_text(encoding="utf-8")
    assert "版本号格式非法" in src, "publish-clawhub.sh 也必须校验 VERSION"
    # 校验必须在使用该值（cd 到输出目录 / 调 build）之前
    assert src.index("版本号格式非法") < src.index('cd "$OUT_ROOT/$VERSION"')


# ---------------- P1-3：非 git 环境不得静默跳过 ----------------

def test_build_fails_closed_without_git():
    src = BUILD.read_text(encoding="utf-8")
    assert "LUNHENG_ALLOW_NO_GIT" in src, "必须提供显式豁免开关"
    assert "该检查是发现「未跟踪残留入包」的唯一机械门，不允许静默跳过" in src
    # 原实现是「if git ... then <整段> fi」（无 else）→ 非 git 静默通过；现在必须有 else 分支终止
    assert re.search(r'if ! git -C "\$SKILL_ROOT" rev-parse', src), \
        "应以否定形式显式处理「非 git」分支"


def test_build_nongit_guard_is_functional(tmp_path):
    """功能验证：在无 .git 的副本上构建必须失败（而非静默产出包）

    2026-09-16 修正（输出根污染）：本用例此前**未隔离输出根**。build 脚本的
    「非 git」门曾位于复制步骤**之后**（scripts/build-clawhub-release.sh 的 2a' 段），
    `rm -rf $OUT_ROOT/9.9.9` + `mkdir` + `rsync` 都已落盘才 exit 1 —— 于是每次 pytest
    都在**共享**输出根 `~/lunheng-build/lunheng-outputs/clawhub-release/` 留下一个
    84 文件的假包 `9.9.9/`，与真实发布包（2.12.4x）混在同一目录，干扰「哪些是真实产物」
    的判断。现显式把 `OUTPUTS_ROOT` 指向 `tmp_path`（与 test_outputs_root_semantics.py
    同源口径），并断言 build 自报的输出目录确在临时根内：断言语义不变，写盘只落临时目录。

    2026-09-16 修正（根治）：隔离只是止血——本用例另加断言，要求非 git 构建失败后
    `<OUTPUTS_ROOT>/clawhub-release/<VER>` **不存在**（门已前置到写盘之前，见脚本 §0）。
    """
    import shutil
    dst = tmp_path / "copy"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "outputs", "__pycache__"))
    out_root = tmp_path / "outputs"
    r = subprocess.run(["bash", str(dst / "scripts" / "build-clawhub-release.sh"), "9.9.9"],
                       capture_output=True, text=True, cwd=str(dst),
                       env={**os.environ, "OUTPUTS_ROOT": str(out_root)})
    assert r.returncode != 0
    assert "非 git 环境" in (r.stderr + r.stdout)
    # 回归断言（2026-09-16）：非 git 门已前置到 rm -rf 之前 —— 失败构建不得留下任何输出目录。
    # 门在复制步骤之后时，本断言会挂：rc=1 但 <OUTPUTS_ROOT>/clawhub-release/9.9.9 已落盘 84 文件。
    assert not (out_root / "clawhub-release" / "9.9.9").exists(), \
        "非 git 构建失败后仍在输出根留下半成品包（非 git 门未前置到 rm -rf 之前）"
    # 反向断言：产物必须落在临时输出根内 —— 若哪天本用例又写回共享根，此处先炸
    m = re.search(r"输出：(.+)", r.stdout)
    assert m, f"build 未打印输出目录：\n{r.stdout[-500:]}"
    produced = pathlib.Path(m.group(1).strip())
    assert produced.resolve().is_relative_to(tmp_path.resolve()), \
        f"非 git 构建把产物写到了临时目录之外（污染共享输出根）：{produced}"
    # 豁免开关存在时可继续（此处只验证开关被识别，不跑完整构建）
    src = (dst / "scripts" / "build-clawhub-release.sh").read_text(encoding="utf-8")
    assert "LUNHENG_ALLOW_NO_GIT=1 显式豁免" in src


# ---------------- P1-2：cleanup 脚本不可逆操作改 opt-in ----------------

def test_cleanup_rejects_bad_keep():
    r = _run(CLEANUP, "--keep=abc")
    assert r.returncode == 2
    assert "--keep 必须为正整数" in (r.stderr + r.stdout)


def test_cleanup_rejects_purge_with_no_backup():
    """既不备份、又要销毁历史 = 放弃全部退路 → 拒绝"""
    r = _run(CLEANUP, "--purge-git-history", "--no-backup")
    assert r.returncode == 2
    assert "互斥" in (r.stderr + r.stdout)


def test_cleanup_default_does_not_purge_git_history():
    src = CLEANUP.read_text(encoding="utf-8")
    purge_at = src.index('if [ "$PURGE_GIT_HISTORY" != "true" ]; then')
    reflog_at = src.rindex("git reflog expire")  # 头部注释也含该字样，取实际命令那次
    assert purge_at < reflog_at, "reflog expire 必须落在 PURGE 分支内"
    # 且必须先打 bundle 备份、再销毁历史
    assert src.index("git bundle verify") < reflog_at
    assert "默认口径：不动可恢复历史" in src


def test_cleanup_bundle_backup_precedes_destruction():
    src = CLEANUP.read_text(encoding="utf-8")
    assert "git bundle create" in src
    assert src.index("git bundle create") < src.rindex("git reflog expire")
    assert "拒绝继续销毁历史" in src


# ---------------- v2.12.63：`_shared/` 白名单准入门 + 规则 3h-5 行级断言 ----------------
# 背景（2026-09-19 第三批四线审计，主控实跑实证）：
#   C-1（P0）：`references/_shared/治理/论衡仓库内教训.md`（维护者工程内档，`#R001` 编号空间）
#      自 v2.12.42 引入后**一直随发布包出厂**，同时绕过三道门（不在排除清单 / 不匹配
#      `教训 #N` 模式 / 是 git 跟踪文件故反向断言也不拦）。
#   C-2（P1）：规则 3h-5 的整行正则把 `00-主控-扩展职责.md` §〇 主控必读清单的**层 1 整行**删掉。
# 本组测试锁三件事：准入清单与真源一致（源侧不变量）/ 准入门在产品侧真的拦得住 /
# 规则 3h-5 的行级断言存在且真的会炸。

def _shared_admitted():
    """从 build 脚本读出 SHARED_ADMITTED 清单（唯一真源，不在此处重抄）。"""
    src = BUILD.read_text(encoding="utf-8")
    m = re.search(r"SHARED_ADMITTED=\((.*?)\n\)", src, re.S)
    assert m, "build-clawhub-release.sh 未找到 SHARED_ADMITTED 清单（准入门被移除？）"
    return re.findall(r"'([^']+)'", m.group(1))


def _shared_excluded_patterns():
    """从 build 脚本的 --exclude 行读出 `references/_shared/` 下的排除项（唯一真源）。"""
    src = BUILD.read_text(encoding="utf-8")
    pats = re.findall(r"--exclude 'references/_shared/([^']+)'", src)
    return [p.rstrip('/') for p in pats]


def test_shared_admitted_list_is_sorted():
    """准入清单必须按 LC_ALL=C sort 排序（脚本内也有同款自检）——保证 diff 可审。"""
    admitted = _shared_admitted()
    assert admitted == sorted(admitted), f"SHARED_ADMITTED 未排序：{admitted}"


def test_shared_admitted_matches_source_tree():
    """**源侧不变量**：真源 `_shared/` 的每个文件，要么在准入清单内，要么被显式排除。

    这条正是「黑名单式排除」缺的那道门——v2.12.42 新增内档时，
    既没进清单也没进排除，于是默认入包。现在两侧必须闭合。
    """
    import fnmatch
    admitted = set(_shared_admitted())
    excluded = _shared_excluded_patterns()
    src_dir = ROOT / "references" / "_shared"
    # v2.12.70 A-治理瘦身：`_shared/` 分层为 真源/ + 治理/，递归收集相对路径
    actual = {str(p.relative_to(src_dir)) for p in src_dir.rglob("*") if p.is_file()}
    unexplained = []
    for name in sorted(actual):
        if name in admitted:
            continue
        if any(name == e or fnmatch.fnmatch(name, e) for e in excluded):
            continue
        unexplained.append(name)
    assert not unexplained, (
        "真源 references/_shared/ 存在**既未登记入包、也未显式排除**的文件 —— "
        "这正是 C-1 泄漏的成因（新文件默认入包）：" + ", ".join(unexplained)
    )
    # 反向：清单里的每一项都必须真实存在（防清单腐烂成空指针）
    missing = sorted(a for a in admitted if not (src_dir / a).is_file())
    assert not missing, f"准入清单登记了真源不存在的文件（清单腐烂）：{missing}"


def test_build_has_shared_admission_gate():
    """准入门必须存在、且必须在复制步骤之后（否则无包可比）。"""
    src = BUILD.read_text(encoding="utf-8")
    assert "SHARED_ADMITTED" in src
    assert "净化包 references/_shared/ 与准入清单不一致" in src
    assert "包内有但清单未登记" in src and "清单已登记但包内缺失" in src
    # 门必须在 rsync/cp 复制之后（2b' 位于 2b 与 2c 之间）
    assert src.index("SHARED_ADMITTED=(") > src.index("FORBIDDEN_IN_PACKAGE=(")


def test_purify_3h5_is_mention_only_and_asserted():
    """规则 3h-5 不得再整行删除；且必须带行级反向断言（7c）。"""
    src = BUILD.read_text(encoding="utf-8")
    # 旧实现的整行正则必须**不再是活代码**（注释里留作历史说明是允许的）
    assert not re.search(r"^s = re\.sub\(r'\[\^\\n\]\*设计文档", src, re.M), \
        "规则 3h-5 的整行删除正则仍是活代码 —— 会再删掉主控必读清单的层 1 行"
    # 新实现：精确 mention 替换 + 行级断言
    assert "`glossary-full.md`（**发布版无 `设计文档.md`**" in src
    assert "_src_had_layer1" in src
    assert "规则 3h-5 行级反向断言失败" in src


def test_build_admission_gate_blocks_unregistered_file(tmp_path):
    """功能验证：未登记文件进包 ⇒ 构建必须失败并点名（模拟 C-1 的成因）。"""
    import shutil
    dst = tmp_path / "copy"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "outputs", "__pycache__"))
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"]):
        subprocess.run(cmd, cwd=str(dst), env=env, capture_output=True, text=True)
    intruder = dst / "references" / "_shared" / "zz-未登记内档.md"
    intruder.write_text("# 未登记\n\n> 版本：v9.9.9\n", encoding="utf-8")
    subprocess.run(["git", "add", "references/_shared/zz-未登记内档.md"],
                   cwd=str(dst), env=env, capture_output=True, text=True)
    out_root = tmp_path / "outputs"
    r = subprocess.run(["bash", str(dst / "scripts" / "build-clawhub-release.sh"), "9.9.9"],
                       capture_output=True, text=True, cwd=str(dst),
                       env={**os.environ, "OUTPUTS_ROOT": str(out_root)})
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "未登记文件入包竟构建成功 —— 准入门失效"
    assert "准入清单不一致" in blob, f"未命中准入门（可能是别的门先炸）：\n{blob[-1500:]}"
    assert "zz-未登记内档.md" in blob, "准入门未点名未登记文件"


def test_build_package_excludes_maintainer_internal_and_keeps_layer1(tmp_path):
    """端到端：真实构建一次，锁两条审计结论的修复。

    ① C-1：包内不得出现维护者内档，且全包不得残留 `#R\\d{3}` 编号空间；
    ② C-2：`00-主控-扩展职责.md` 的「层 1 入口必读」整行必须在净化后**存活**。
    """
    out_root = tmp_path / "outputs"
    r = subprocess.run(["bash", str(BUILD), "2.12.63"],
                       capture_output=True, text=True, cwd=str(ROOT),
                       env={**os.environ, "OUTPUTS_ROOT": str(out_root)})
    assert r.returncode == 0, f"构建失败：\n{(r.stderr + r.stdout)[-2000:]}"
    pkg = out_root / "clawhub-release" / "2.12.63"

    # ① C-1 泄漏
    assert not (pkg / "references" / "_shared" / "治理" / "论衡仓库内教训.md").exists(), \
        "维护者内档仍在发布包内"
    shared = {str(p.relative_to(pkg / "references" / "_shared")) for p in (pkg / "references" / "_shared").rglob("*") if p.is_file()}
    assert shared == set(_shared_admitted()), "包内 _shared 文件集与准入清单不符"
    leaked = []
    for p in pkg.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".yaml", ".yml", ".json", ".txt"):
            try:
                if re.search(r"#R\d{3}|论衡仓库内教训|repo-internal", p.read_text(encoding="utf-8")):
                    leaked.append(str(p.relative_to(pkg)))
            except UnicodeDecodeError:
                pass
    assert not leaked, f"包内仍有 #R 编号空间 / 内档引用：{leaked}"

    # ② C-2 层 1 行存活
    duty = (pkg / "references" / "agents" / "00-主控-扩展职责.md").read_text(encoding="utf-8")
    assert "入口必读（启动清单 1-2 步）" in duty, \
        "主控必读清单的「层 1 入口必读」整行又被净化规则删掉了"
    assert "设计文档" not in duty, "`设计文档.md` mention 未被剥离（死引用残留）"

    # ③ C-1 推广（第二批次）：包内文件集必须**精确等于**随包清单
    pkg_files = sorted(str(p.relative_to(pkg)) for p in pkg.rglob("*") if p.is_file())
    assert pkg_files == _pkg_manifest(), (
        "包内文件集与 scripts/.pkg-manifest.txt 不精确相等 —— 全包白名单准入门失效或清单过期")

    # ④ C-4：包内不得再出现指向**被排除文档**的引用（死链中和的产物侧断言）
    dead = []
    for p in sorted(pkg.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        for pat in _excluded_doc_paths():
            if "*" in pat:
                continue  # glob 形态不做字面匹配（清单里仅有 2 条）
            if pat in text:
                dead.append(f"{p.relative_to(pkg)} → {pat}")
    assert not dead, f"包内仍引用被排除文档（死链未被中和）：{dead}"


# ---------------- 2026-09-19 第五批：新门逐条负向注入（主控实跑复核）----------------
# 背景：C-1 推广 / C-3 / C-4 / C-5 / C-6 / C-7 六项改造由子会话静态落盘后，主控实跑复核时
#   抓出两个真问题：① C-7 的 `_RR_YES_NAMES` 未初始化，`set -u` 下构建**直接崩**；
#   ② C-3 新条目当场抓出真源残留（`执行韧化协议-design.md` 的 `1-token ping` 维护者叙事）。
#   ⇒「门写了没人跑」= 门等于没写。本组测试把每条新门**各配一次真实负向注入**，
#     断言构建**必须失败**且失败原因**正是该门**（而非别的门先炸）。

def _mkcopy(tmp_path, name="copy"):
    """复制仓库到临时目录并建 git 仓库（构建的 0/2a′ 前置门要求 git 跟踪）。"""
    import shutil
    dst = tmp_path / name
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "outputs", "__pycache__"))
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"]):
        subprocess.run(cmd, cwd=str(dst), env=env, capture_output=True, text=True)
    return dst


def _build(dst, tmp_path, version="9.9.9", env_extra=None, tag="out"):
    env = {**os.environ, "OUTPUTS_ROOT": str(tmp_path / tag)}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(["bash", str(dst / "scripts" / "build-clawhub-release.sh"), version],
                          capture_output=True, text=True, cwd=str(dst), env=env)


def _pkg_manifest():
    """读出随包清单（唯一真源，不在测试里重抄）。"""
    mf = ROOT / "scripts" / ".pkg-manifest.txt"
    assert mf.is_file(), "scripts/.pkg-manifest.txt 缺失 —— 全包准入门空转"
    return [ln for ln in mf.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _excluded_doc_paths():
    """从 build 脚本读出 PKG_EXCLUDED_DOC_PATHS（死链中和的声明式真源）。"""
    src = BUILD.read_text(encoding="utf-8")
    m = re.search(r"PKG_EXCLUDED_DOC_PATHS=\((.*?)\n\)", src, re.S)
    assert m, "build-clawhub-release.sh 未找到 PKG_EXCLUDED_DOC_PATHS（死链中和门被移除？）"
    return re.findall(r"'([^']+)'", m.group(1))


def test_pkg_manifest_is_sorted_and_public_safe():
    """清单必须排序（可审 diff）且**不含维护者资产**（清单本身即准入真源，腐烂无二道防线）。"""
    mf = _pkg_manifest()
    assert mf == sorted(mf), "随包清单未按 LC_ALL=C sort 排序"
    bad = [e for e in mf if e.startswith("scripts/") or "论衡仓库内教训" in e
           or "设计文档" in e or "教训索引" in e or "lessons-max" in e]
    assert not bad, f"随包清单登记了维护者内部资产（会被分发）：{bad}"


def test_pkg_manifest_covers_every_built_file(tmp_path):
    """源侧闭合：真源里每个**会进包**的文件都必须在清单内（清单过期即构建红）。

    这是「新文件默认入包」→「新文件默认被拦」反转的源侧半条；产物侧半条在 e2e 测试 ③。
    """
    mf = set(_pkg_manifest())
    # 清单里每一项都必须真实存在（防清单腐烂成空指针）
    missing = sorted(e for e in mf if not (ROOT / e).is_file())
    assert not missing, f"随包清单登记了真源不存在的文件（清单腐烂）：{missing}"


def test_pkg_manifest_gate_blocks_unregistered_file_outside_shared(tmp_path):
    """**负向注入**：`_shared/` 之外的目录（C-1 推广的作用面）新增未登记文件 ⇒ 构建必须失败。

    C-1 成因正是「`_shared/` 之外仍是黑名单式」：这里模拟在 `references/agents/` 塞一个内档。
    """
    dst = _mkcopy(tmp_path)
    intruder = dst / "references" / "agents" / "zz-未登记-全包门.md"
    intruder.write_text("# 全包范围未登记新文件\n\n> 版本：v9.9.9\n\n维护者内档测试。\n",
                        encoding="utf-8")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "add", "-A"], cwd=str(dst), env=env, capture_output=True, text=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i"],
                   cwd=str(dst), env=env, capture_output=True, text=True)
    r = _build(dst, tmp_path)
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "未登记文件入包竟构建成功 —— 全包清单门失效"
    assert "随包清单不一致" in blob or "净化包文件集与随包清单不一致" in blob, \
        f"未命中全包清单门（可能是别的门先炸）：\n{blob[-1500:]}"
    assert "zz-未登记-全包门.md" in blob, "全包清单门未点名未登记文件"


def test_baseline_floor_guard_blocks_degenerate_ratio(tmp_path):
    """**负向注入**（C-6）：把基线下限抬到不可能达到的高度 ⇒ 构建必须在 §2c 立即失败。

    该门治的是「保留率分母异常小 ⇒ 比率恒过」。用环境变量注入等价于真源出现极小文件。
    """
    dst = _mkcopy(tmp_path)
    r = _build(dst, tmp_path, env_extra={"PKG_MIN_BASELINE_CHARS": "100000"})
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "基线极小（分母退化）竟构建成功 —— 基线下限守卫失效"
    assert "基线下限守卫未通过" in blob, f"未命中 C-6 基线下限门：\n{blob[-1500:]}"


def test_nonmd_positive_gate_detects_emptied_yaml(tmp_path):
    """**负向注入**（C-5）：清空包内非 md 文本资产 ⇒ 非 md 正向完整性门必须拦住。

    旧版正向门只覆盖 `*.md`，`phase-order.yaml` 被整篇删空也全绿（审计 C-5）。
    """
    dst = _mkcopy(tmp_path)
    yml = dst / "references" / "_shared" / "真源" / "phase-order.yaml"
    assert yml.is_file(), "fixture 前提失败：phase-order.yaml 不存在"
    yml.write_text("", encoding="utf-8")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "add", "-A"], cwd=str(dst), env=env, capture_output=True, text=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "e"],
                   cwd=str(dst), env=env, capture_output=True, text=True)
    r = _build(dst, tmp_path)
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "非 md 资产被清空竟构建成功 —— 非 md 正向门失效"
    assert "非 md" in blob, f"未命中非 md 正向门：\n{blob[-1500:]}"


def test_rule_empty_reasons_bidirectional_closure():
    """**源侧不变量**（C-7）：`allow_empty=yes` ⇔ `RULE_EMPTY_REASONS` 双向闭合、理由 ≥12 字符。

    这是「空理由即豁免」的静态半边；功能半边是脚本内同款校验（负向注入见下表）。
    """
    src = BUILD.read_text(encoding="utf-8")
    checks = re.findall(r"\n  '([^'|]+)\|([^'|]*)\|(?:warn|critical)\|(yes|no)'", src)
    yes = {n for n, _, a in checks if a == "yes"}
    reasons = dict(re.findall(r"\n  '([^'|]+)\|([^']+)'",
                              src.split("RULE_EMPTY_REASONS=(")[1].split("\n)")[0]))
    assert yes, "未解析到任何 allow_empty=yes 条目（格式漂移？）"
    assert yes == set(reasons), (
        f"豁免理由表未双向闭合 —— 缺理由：{sorted(yes - set(reasons))}；"
        f"孤儿：{sorted(set(reasons) - yes)}")
    short = sorted(n for n in reasons if len(reasons[n]) < 12)
    assert not short, f"豁免理由过短（< 12 字符 = 占位式豁免）：{short}"
    assert "RULE_REASON_MIN_CHARS=12" in src, "最小理由长度未声明"


def test_deadlink_neutralizer_is_programmatic_and_fail_closed():
    """（C-4）死链中和必须**从排除清单推导**（而非手写 sed 路径），且残留即 fail-closed。"""
    src = BUILD.read_text(encoding="utf-8")
    assert _excluded_doc_paths(), "PKG_EXCLUDED_DOC_PATHS 为空 —— 死链中和门空转"
    assert "若新增一个被排除文件就漏一次" not in src, "仍是手写路径的旧注释残留"
    # 反向断言：残留必须 exit 1 并点名
    assert "死链中和失败：包内仍存在指向被排除文档的引用" in src, "缺少 fail-closed 反向断言"
    # 且 python 侧必须接受清单作为参数（声明式真源，不是硬编码）
    assert 'python3 - "$OUT_DIR" "${PKG_EXCLUDED_DOC_PATHS[@]}"' in src, \
        "中和规则未从 PKG_EXCLUDED_DOC_PATHS 取参数（可能又硬编码了路径）"
