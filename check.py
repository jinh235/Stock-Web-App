# -*- coding: utf-8 -*-
"""
푸시 전 점검 스크립트.

GitHub에 푸시하기 전에 VS Code 터미널에서 아래 한 줄을 실행하세요.

    python check.py

점검하는 것:
  1. 문법 오류: 모든 .py 파일이 파이썬 문법에 맞는지
  2. 함수/변수 누락: 한 파일이 다른 파일에서 불러오는(from ... import ...) 이름이
     실제로 그 파일에 들어있는지
     (없으면 배포 후 앱이 ImportError로 멈춥니다. 가계부 앱에서 쓰던 점검을 그대로 가져왔습니다.)

문제가 없으면 "모든 점검 통과"가, 있으면 어느 파일 몇 번째 줄인지가 표시됩니다.
이 파일은 앱 실행과는 상관이 없어서 GitHub에 같이 올라가도 괜찮습니다.
"""
import ast
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def defined_names(tree):
    """파일 맨 바깥(들여쓰기 없는 곳)에서 만들어지는 이름들을 모읍니다.
    함수(def), 클래스(class), 변수(=), 그리고 그 파일이 import해온 이름까지 포함합니다."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.For, ast.With, ast.If, ast.Try)):
            # 예: config.py의 "for _cats in ...:" 처럼 맨 바깥 반복문 안에서 만든 이름
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    names.add(sub.id)
    return names


def main():
    py_files = sorted(PROJECT_DIR.glob("*.py"))
    local_modules = {p.stem for p in py_files}
    trees = {}
    problems = []

    # 1. 문법 점검
    for path in py_files:
        try:
            source = path.read_text(encoding="utf-8")
            trees[path.stem] = ast.parse(source, filename=path.name)
        except SyntaxError as e:
            problems.append(f"[문법 오류] {path.name} {e.lineno}번째 줄: {e.msg}")
        except UnicodeDecodeError:
            problems.append(f"[인코딩 오류] {path.name}: UTF-8로 저장되어 있지 않습니다.")

    # 2. 불러오는 이름이 실제로 있는지 점검
    names_by_module = {mod: defined_names(tree) for mod, tree in trees.items()}
    for mod, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module not in local_modules:
                continue
            if node.module not in names_by_module:
                continue  # 그 파일 자체에 문법 오류가 있어 위에서 이미 보고됨
            for alias in node.names:
                if alias.name == "*":
                    continue
                if alias.name not in names_by_module[node.module]:
                    problems.append(
                        f"[누락] {mod}.py {node.lineno}번째 줄에서 {node.module}.py의 "
                        f"'{alias.name}'을(를) 불러오는데, {node.module}.py에 그런 이름이 없습니다."
                    )

    print(f"점검한 파일: {', '.join(p.name for p in py_files)}")
    if problems:
        print()
        for p in problems:
            print(p)
        print()
        print(f"문제 {len(problems)}건 발견 - 고친 뒤에 푸시하세요.")
        sys.exit(1)

    print("모든 점검 통과 - 푸시해도 됩니다.")


if __name__ == "__main__":
    main()
