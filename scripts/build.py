#!/usr/bin/env python3
"""
build.py — Reconstrói index.html / painel.html a partir de:
  - data/tasks.json  (dados dinâmicos do ClickUp)
  - data/config.json (dados curados estáticos)
  - index.html atual (como template — substitui apenas blocos marcados)

Uso:
  python3 scripts/build.py --input index.html --output index.html
  python3 scripts/build.py --input index.html --output painel.html --dry-run
"""

import json, re, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
TASKS_FILE = ROOT / "data" / "tasks.json"
CONFIG_FILE = ROOT / "data" / "config.json"
BRT = timezone(timedelta(hours=-3))


def now_str():
    return datetime.now(BRT).strftime("%d/%m/%Y %H:%M")


def build_tasks_js(tasks: dict) -> str:
    """Serializa tasks dict para bloco JS const TASKS = {...}"""
    lines = []
    for tid, d in tasks.items():
        nome = d["n"].replace('"', '\\"')
        s = d["s"]
        p = "null" if not d.get("p") else f'"{d["p"]}"'
        a = ",".join([f'"{x}"' for x in d.get("a", [])])
        lines.append(f'"{tid}":{{"n":"{nome}","s":"{s}","p":{p},"a":[{a}]}}')
    return "const TASKS = {\n" + ",\n".join(lines) + "\n}"


def build_top_order(config: dict, tasks: dict) -> str:
    """
    Reconstrói TOP_ORDER respeitando regra:
    finalizadas → em andamento → não iniciadas → Golive sempre último
    """
    top_ids = config["top_order"]
    golive = "86ahxbff7"

    def get_status(tid):
        return tasks.get(tid, {}).get("s", "complete")

    ids_sem_golive = [t for t in top_ids if t != golive]
    fin  = [t for t in ids_sem_golive if get_status(t) == "complete"]
    and_ = [t for t in ids_sem_golive if get_status(t) == "in progress"]
    nao  = [t for t in ids_sem_golive if get_status(t) == "to do"]

    ordered = fin + and_ + nao + [golive]
    return "const TOP_ORDER = [" + ",".join([f'"{t}"' for t in ordered]) + "];"


def build_progress_groups(config: dict) -> str:
    pgs = config["progress_groups"]
    return 'const PROGRESS_GROUPS = new Set([' + ",".join([f'"{p}"' for p in pgs]) + ']);'


def calc_pct(tasks: dict, progress_groups: set) -> tuple:
    """Calcula % em Python puro sem Node.js"""
    # Montar parent map
    parent_map = {tid: d.get("p") for tid, d in tasks.items()}

    def in_scope(tid):
        c, visited = tid, set()
        while c:
            if c in visited:
                break
            visited.add(c)
            if c in progress_groups:
                return True
            c = parent_map.get(c)
        return False

    tot = done = ip = td = 0
    for tid, d in tasks.items():
        if in_scope(tid):
            tot += 1
            if d["s"] == "complete":   done += 1
            elif d["s"] == "in progress": ip += 1
            else: td += 1

    pct = f"{done/tot*100:.1f}".replace(".", ",") if tot else "0,0"
    return pct, done, ip, td, tot


def rebuild(input_path: Path, output_path: Path, dry_run: bool = False) -> dict:
    # Carregar dados
    with open(TASKS_FILE) as f:
        tasks_data = json.load(f)
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    tasks = tasks_data["tasks"]
    pg_set = set(config["progress_groups"])
    now = now_str()

    # Carregar HTML atual como base
    with open(input_path, encoding="utf-8") as f:
        html = f.read()

    # 1. Substituir bloco TASKS
    tasks_js = build_tasks_js(tasks)
    start = html.find("const TASKS = {")
    end = html.find("\nconst TOP_ORDER", start)
    if start == -1 or end == -1:
        raise ValueError("Bloco TASKS não encontrado no HTML!")
    html = html[:start] + tasks_js + html[end:]

    # 2. Atualizar TOP_ORDER
    top_str = build_top_order(config, tasks)
    html = re.sub(r'const TOP_ORDER = \[.*?\];', top_str, html)

    # 3. Atualizar PROGRESS_GROUPS
    pg_str = build_progress_groups(config)
    html = re.sub(r'const PROGRESS_GROUPS = [^;]+;', pg_str, html)

    # 4. Atualizar data/hora
    html = re.sub(r'<b id="syncDate">[^<]*</b>', f'<b id="syncDate">{now}</b>', html)
    html = re.sub(r'id="ftNote">[^<]+', f'id="ftNote">Auto-sync: {now} BRT', html)

    # 5. Calcular %
    pct, done, ip, td, tot = calc_pct(tasks, pg_set)

    report = {
        "timestamp": now,
        "total_tasks": len(tasks),
        "pct": pct,
        "done": done,
        "ip": ip,
        "td": td,
        "tot_scope": tot,
        "output": str(output_path)
    }

    if not dry_run:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ {output_path.name} gerado — {pct}% | ✅ {done}/{tot} | 🟡 {ip} | ⬜ {td}")
    else:
        print(f"[DRY-RUN] {output_path.name} — {pct}% | ✅ {done}/{tot} | 🟡 {ip}")

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="index.html")
    parser.add_argument("--output", default="index.html")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_path = ROOT / args.input
    output_path = ROOT / args.output

    if not input_path.exists():
        print(f"ERRO: {input_path} não encontrado!")
        return

    report = rebuild(input_path, output_path, dry_run=args.dry_run)
    print(f"📊 {report['pct']}% | ✅ {report['done']}/{report['tot_scope']} | "
          f"🟡 {report['ip']} | ⬜ {report['td']} | Total: {report['total_tasks']}")


if __name__ == "__main__":
    main()
