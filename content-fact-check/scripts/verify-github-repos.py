#!/usr/bin/env python3
"""
批量验证 GitHub 仓库的存在性、star 数和描述。

用法：
    python verify-github-repos.py repos.txt
    python verify-github-repos.py owner1/repo1 owner2/repo2

输入格式（repos.txt，每行一个）：
    anthropics/skills
    addyosmani/agent-skills

输出：表格格式，包含仓库名、star 数、描述、状态。

环境变量：
    GITHUB_TOKEN — 可选，设置后可避免 API 限速（未认证 60 次/小时，认证 5000 次/小时）
"""

import json
import os
import sys
import urllib.request
import urllib.error


def fetch_repo(owner_repo: str, token: str | None = None) -> dict:
    url = f"https://api.github.com/repos/{owner_repo}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "content-fact-check-skill")
    if token:
        req.add_header("Authorization", f"token {token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {
                "repo": owner_repo,
                "stars": data.get("stargazers_count", 0),
                "description": (data.get("description") or "")[:80],
                "archived": data.get("archived", False),
                "status": "OK",
            }
    except urllib.error.HTTPError as e:
        return {
            "repo": owner_repo,
            "stars": 0,
            "description": "",
            "archived": False,
            "status": f"HTTP {e.code}" if e.code != 404 else "NOT FOUND",
        }
    except Exception as e:
        return {
            "repo": owner_repo,
            "stars": 0,
            "description": "",
            "archived": False,
            "status": f"ERROR: {e}",
        }


def format_stars(count: int) -> str:
    if count >= 1000:
        return f"{count / 1000:.0f}k+" if count >= 10000 else f"{count / 1000:.1f}k+"
    return str(count)


def main():
    repos: list[str] = []
    token = os.environ.get("GITHUB_TOKEN")

    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            with open(arg, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "/" in line:
                        repos.append(line)
        elif "/" in arg:
            repos.append(arg)

    if not repos:
        print("Usage: python verify-github-repos.py repos.txt")
        print("       python verify-github-repos.py owner/repo [owner/repo ...]")
        sys.exit(1)

    print(f"{'Repo':<45} {'Stars':>8} {'Status':<12} Description")
    print("-" * 100)

    all_ok = True
    for repo in repos:
        result = fetch_repo(repo, token)
        stars_str = format_stars(result["stars"]) if result["status"] == "OK" else "-"
        archived_tag = " [ARCHIVED]" if result["archived"] else ""
        status_icon = "[OK]" if result["status"] == "OK" else "[!!]"

        print(
            f"{status_icon} {result['repo']:<42} {stars_str:>8} {result['status']:<12} "
            f"{result['description']}{archived_tag}"
        )

        if result["status"] != "OK":
            all_ok = False

    print("-" * 100)
    print(f"Total: {len(repos)} repos, {'all OK' if all_ok else 'some issues found'}")

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
