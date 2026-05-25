#!/usr/bin/env python3
"""
Auto-discovery script for awesome-agent-everything.
Searches GitHub for new awesome-agent repositories and updates data/repos.yml & README.md.
"""

import os
import re
import sys
import yaml
import requests
from datetime import datetime, timezone

# GitHub API setup
GH_TOKEN = os.environ.get("GH_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
}
if GH_TOKEN:
    HEADERS["Authorization"] = f"token {GH_TOKEN}"

REPOS_FILE = "data/repos.yml"
README_FILE = "README.md"

# Search keywords for discovering new repos
SEARCH_QUERIES = [
    "awesome agent",
    "awesome ai-agent",
    "awesome llm-agent",
    "awesome autonomous-agent",
    "awesome agent-framework",
    "awesome agent-skills",
    "awesome agent-tools",
    "awesome agent-papers",
    "awesome mcp",
    "awesome harness agent",
    "awesome code-agents",
    "awesome agentic",
    "awesome coding-agent",
    "awesome agent-security",
    "awesome agent-safety",
    "awesome multi-agent",
    "awesome agent-eval",
    "awesome agent-workflow",
    "awesome agent-memory",
    "awesome agent-planning",
]

# Category classification rules
CATEGORY_RULES = [
    (["framework", "platform", "sdk"], "frameworks"),
    (["paper", "research", "survey", "arxiv"], "papers"),
    (["skill", "prompt", "system-prompt", "hook"], "skills"),
    (["tool", "infrastructure", "app", "memory"], "tools"),
    (["mcp", "model-context-protocol", "mcp-server"], "mcp"),
    (["harness", "engineering", "context-engineering", "observability"], "harness"),
    (["coding", "code-agent", "dev", "ide", "cursor", "copilot", "codex"], "coding"),
    (["security", "safety", "guardrail", "red-team"], "safety"),
    (["multi-agent", "collaboration", "swarm", "orchestrat"], "multi-agent"),
    (["eval", "benchmark", "testing", "evaluate"], "evaluation"),
    (["domain", "finance", "medical", "legal", "n8n", "automation-template"], "domain"),
    (["ui", "design", "interface", "gui", "browser-agent", "web-agent"], "ui"),
    (["workflow", "automation", "orchestration", "pipeline"], "workflow"),
    (["reasoning", "planning", "strawberry", "o1"], "reasoning"),
    (["ranking", "aggregator", "meta", "index", "compiled"], "meta"),
]


def classify_category(name, description):
    """Classify a repo into a category based on its name and description."""
    text = f"{name} {description}".lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "tools"  # default


def load_existing_repos():
    """Load existing repos from repos.yml."""
    if not os.path.exists(REPOS_FILE):
        return {}
    with open(REPOS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    repos = data.get("repos", [])
    return {r["repo"]: r for r in repos}


def search_github_repos(query, max_pages=3):
    """Search GitHub for repositories matching the query."""
    results = []
    for page in range(1, max_pages + 1):
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
            "page": page,
        }
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break
                for item in items:
                    results.append({
                        "repo": f"{item['owner']['login']}/{item['name']}",
                        "stars": item["stargazers_count"],
                        "description": item.get("description", "") or "",
                        "language": item.get("language", "") or "",
                        "topics": item.get("topics", []),
                        "updated_at": item.get("updated_at", ""),
                    })
                if len(data.get("items", [])) < 30:
                    break
            elif resp.status_code == 403:
                print(f"  ⚠️ Rate limited. Waiting...")
                import time
                time.sleep(60)
                continue
            else:
                print(f"  ⚠️ API error: {resp.status_code}")
                break
        except Exception as e:
            print(f"  ⚠️ Request failed: {e}")
            break
    return results


def is_awesome_agent_repo(repo_info):
    """Check if a repo is genuinely an awesome-agent related repository."""
    name = repo_info["repo"].lower()
    desc = repo_info["description"].lower()
    topics = [t.lower() for t in repo_info.get("topics", [])]
    
    combined = f"{name} {desc} {' '.join(topics)}"
    
    # Must have "awesome" in name or description
    if "awesome" not in combined:
        return False
    
    # Must be related to agents / AI
    agent_keywords = [
        "agent", "agents", "agentic", "llm", "ai", "mcp",
        "skill", "harness", "autonomous", "copilot", "codex",
        "claude-code", "cursor", "coding-agent", "code-agent",
    ]
    if not any(kw in combined for kw in agent_keywords):
        return False
    
    return True


def extract_tags(repo_info):
    """Extract relevant tags from repo info."""
    tags = set()
    name = repo_info["repo"].lower()
    desc = repo_info["description"].lower()
    topics = [t.lower() for t in repo_info.get("topics", [])]
    combined = f"{name} {desc} {' '.join(topics)}"
    
    tag_keywords = {
        "skills": ["skill", "skills"],
        "frameworks": ["framework"],
        "mcp": ["mcp", "model-context-protocol"],
        "harness": ["harness"],
        "coding": ["coding", "code-agent"],
        "security": ["security", "safety"],
        "multi-agent": ["multi-agent", "collaboration"],
        "research": ["paper", "research", "arxiv"],
        "chinese": ["中文", "chinese"],
    }
    
    for tag, keywords in tag_keywords.items():
        if any(kw in combined for kw in keywords):
            tags.add(tag)
    
    return sorted(tags)


def update_repos_yml(existing_repos, new_repos):
    """Update repos.yml with new discoveries."""
    # Load full YAML structure
    if os.path.exists(REPOS_FILE):
        with open(REPOS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = {"repos": [], "search_keywords": [], "category_rules": []}
    
    added = 0
    for repo_info in new_repos:
        repo_name = repo_info["repo"]
        if repo_name in existing_repos:
            continue
        if not is_awesome_agent_repo(repo_info):
            continue
        
        category = classify_category(repo_name, repo_info["description"])
        tags = extract_tags(repo_info)
        
        entry = {
            "repo": repo_name,
            "category": category,
            "tags": tags if tags else ["auto-discovered"],
            "stars": repo_info.get("stars", 0),
        }
        
        data["repos"].append(entry)
        existing_repos[repo_name] = entry
        added += 1
        print(f"  ✅ Added: {repo_name} ({repo_info.get('stars', '?')}⭐) → {category}")
    
    if added > 0:
        with open(REPOS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"\n📊 Total new repos added: {added}")
    else:
        print("\n📊 No new repos to add.")
    
    return added


def generate_readme(existing_repos):
    """Regenerate README.md from repos.yml data."""
    # Category display config
    category_config = {
        "frameworks": ("🌟 Agent Frameworks & Platforms / Agent 框架与平台", "frameworks"),
        "papers": ("🧠 Agent Research & Papers / Agent 论文与研究", "papers"),
        "skills": ("⚡ Agent Skills & Prompts / Agent 技能与提示词", "skills"),
        "tools": ("🔧 Agent Tools & Infrastructure / Agent 工具与基础设施", "tools"),
        "mcp": ("🌐 MCP (Model Context Protocol) / 模型上下文协议", "mcp"),
        "harness": ("🏗️ Agent Harness & Engineering / Agent Harness 工程", "harness"),
        "coding": ("💻 Coding Agents & Dev Tools / 编程 Agent 与开发工具", "coding"),
        "safety": ("🔒 Agent Safety & Security / Agent 安全", "safety"),
        "multi-agent": ("🤖 Multi-Agent Systems / 多 Agent 系统", "multi-agent"),
        "evaluation": ("📊 Agent Evaluation & Benchmarking / Agent 评估与基准", "evaluation"),
        "domain": ("🎯 Domain-Specific Agents / 领域特定 Agent", "domain"),
        "ui": ("📱 Agent UI & Interaction / Agent 界面与交互", "ui"),
        "workflow": ("🔄 Agent Workflow & Automation / Agent 工作流与自动化", "workflow"),
        "reasoning": ("📚 LLM Reasoning & Planning / LLM 推理与规划", "reasoning"),
        "meta": ("🗂️ Meta-Indexes & Aggregators / 元索引与聚合器", "meta"),
    }
    
    # Group repos by category
    by_category = {}
    for repo_name, info in existing_repos.items():
        cat = info.get("category", "tools")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((repo_name, info))
    
    # Sort each category by stars (desc)
    for cat in by_category:
        by_category[cat].sort(key=lambda x: x[1].get("stars", 0), reverse=True)
    
    # Build README sections
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    sections = []
    for cat_key, (title, anchor) in category_config.items():
        repos = by_category.get(cat_key, [])
        section = f"\n## {title}\n\n| Repository | ⭐ Stars | Description |\n|---|---|---|\n"
        
        if repos:
            for repo_name, info in repos:
                stars = info.get("stars", "—")
                desc = info.get("description", "")
                if not desc:
                    desc = "—"
                # Truncate long descriptions
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                section += f"| [{repo_name}](https://github.com/{repo_name}) | {stars} | {desc} |\n"
        else:
            section += "| *Coming soon — auto-discovered via CI* | — | |\n"
        
        sections.append(section)
    
    # Read current README and update
    with open(README_FILE, "r", encoding="utf-8") as f:
        readme = f.read()
    
    # Update last-updated date
    readme = re.sub(
        r'<!-- LAST_UPDATED -->.*?<!-- /LAST_UPDATED -->',
        f'<!-- LAST_UPDATED -->{today}<!-- /LAST_UPDATED -->',
        readme
    )
    
    # Replace category sections
    # Find the first section marker and replace everything after it
    section_pattern = r'(## 🌟 Agent Frameworks.*?)(## 🤝 Contributing.*)'
    match = re.search(section_pattern, readme, re.DOTALL)
    if match:
        new_body = "\n".join(sections) + "\n\n"
        readme = readme[:match.start()] + new_body + match.group(2)
    
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(readme)
    
    print(f"📝 README.md updated with {len(existing_repos)} repos across {len(by_category)} categories")


def fetch_repo_details(repo_name):
    """Fetch star count and description for a single repo."""
    url = f"https://api.github.com/repos/{repo_name}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "stars": data.get("stargazers_count", 0),
                "description": data.get("description", "") or "",
                "topics": data.get("topics", []),
            }
    except Exception as e:
        print(f"  ⚠️ Failed to fetch {repo_name}: {e}")
    return None


def update_existing_stars(existing_repos):
    """Update star counts for existing repos."""
    updated = 0
    for repo_name, info in existing_repos.items():
        details = fetch_repo_details(repo_name)
        if details:
            old_stars = info.get("stars", 0)
            new_stars = details["stars"]
            if old_stars != new_stars:
                info["stars"] = new_stars
                # Update description if missing
                if not info.get("description") and details["description"]:
                    info["description"] = details["description"]
                updated += 1
                print(f"  📈 {repo_name}: {old_stars} → {new_stars} ⭐")
    return updated


def main():
    print("🔍 awesome-agent-everything auto-updater")
    print("=" * 50)
    
    # Load existing repos
    existing = load_existing_repos()
    print(f"📋 Loaded {len(existing)} existing repos")
    
    # Update star counts for existing repos
    print("\n📈 Updating star counts...")
    stars_updated = update_existing_stars(existing)
    print(f"  Updated {stars_updated} star counts")
    
    # Search for new repos
    print("\n🔎 Searching for new awesome-agent repos...")
    all_new = {}
    for query in SEARCH_QUERIES:
        print(f"  Searching: '{query}'")
        results = search_github_repos(query, max_pages=2)
        for r in results:
            if r["repo"] not in existing and r["repo"] not in all_new:
                all_new[r["repo"]] = r
        print(f"    Found {len(results)} results, {len(all_new)} unique new so far")
    
    # Filter for genuine awesome-agent repos
    filtered = []
    for repo_name, info in all_new.items():
        if is_awesome_agent_repo(info):
            filtered.append(info)
    print(f"\n🎯 Filtered to {len(filtered)} genuine awesome-agent repos")
    
    # Update repos.yml
    added = update_repos_yml(existing, filtered)
    
    # Regenerate README
    print("\n📝 Regenerating README.md...")
    generate_readme(existing)
    
    # Update repos.yml with star counts
    if stars_updated > 0 or added > 0:
        with open(REPOS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for entry in data["repos"]:
            repo_name = entry["repo"]
            if repo_name in existing:
                entry["stars"] = existing[repo_name].get("stars", entry.get("stars", 0))
                if not entry.get("description") and existing[repo_name].get("description"):
                    entry["description"] = existing[repo_name]["description"]
        with open(REPOS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ Done! Added {added} new repos, updated {stars_updated} star counts.")


if __name__ == "__main__":
    main()
