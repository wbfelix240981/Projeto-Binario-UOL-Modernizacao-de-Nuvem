#!/usr/bin/env python3
"""
sync.py — Sincronização ClickUp → data/tasks.json

Uso:
  python3 scripts/sync.py --token $CLICKUP_TOKEN       # produção
  python3 scripts/sync.py --test                        # modo simulado
  python3 scripts/sync.py --token $TOKEN --dry-run      # busca mas não salva

Regras de negócio:
  - Só atualiza campos dinâmicos: status (s), responsável (a)
  - NUNCA sobrescreve: nome (n), parent (p) — vêm do HTML original
  - Novas tarefas são adicionadas com parent=null
  - Status em PT-BR → interno: ver STATUS_MAP
  - NÃO usa [skip ci] nos commits (quebraria Cloudflare Pages)
"""

import json, re, sys, urllib.request, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
TASKS_FILE = ROOT / "data" / "tasks.json"
CONFIG_FILE = ROOT / "data" / "config.json"
BRT = timezone(timedelta(hours=-3))

# ─── Vocabulário de status ──────────────────────────────────────────────────
# IMPORTANTE: Lista BCP usa PT-BR customizado. Nunca assumir padrão inglês.
STATUS_MAP = {
    "fechado":            "complete",
    "entregue":           "complete",
    "revisando":          "complete",
    "em andamento":       "in progress",
    "aguardando retorno": "in progress",
    "aberto":             "to do",
    # fallbacks inglês (caso lista mude para padrão)
    "closed":    "complete",
    "complete":  "complete",
    "done":      "complete",
    "in progress": "in progress",
    "open":      "to do",
    "to do":     "to do",
}


def now_str():
    return datetime.now(BRT).strftime("%d/%m/%Y %H:%M")


def fetch_clickup(token: str, lista_id: str, pages: int = 3) -> dict:
    """Busca tarefas do ClickUp (até `pages` páginas)."""
    all_tasks = {}
    for page in range(pages):
        url = (f"https://api.clickup.com/api/v2/list/{lista_id}/task"
               f"?include_closed=true&subtasks=true&page={page}&order_by=created")
        req = urllib.request.Request(url, headers={"Authorization": token})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  ERRO página {page}: {e}")
            break

        tasks = data.get("tasks", [])
        if not tasks:
            break

        for t in tasks:
            status_obj = t.get("status", "aberto")
            raw = status_obj.get("status", "aberto") if isinstance(status_obj, dict) else str(status_obj)
            s = STATUS_MAP.get(raw.lower().strip(), "to do")
            all_tasks[t["id"]] = {
                "n": t["name"],
                "s": s,
                "a": [a["username"] for a in t.get("assignees", [])],
                "raw_status": raw,
            }
        print(f"  Página {page}: {len(tasks)} tarefas")

    return all_tasks


def simulated_clickup() -> dict:
    """Dados simulados para testes (3 cenários)."""
    with open(TASKS_FILE) as f:
        stored = json.load(f)["tasks"]

    tids = list(stored.keys())
    sim = {}
    for tid, d in stored.items():
        sim[tid] = {"n": d["n"], "s": d["s"], "a": d["a"], "raw_status": d["s"]}

    # Cenário (b): simular 2 mudanças de status
    if len(tids) > 5:
        sim[tids[0]]["s"] = "in progress"
        sim[tids[0]]["raw_status"] = "em andamento"
        sim[tids[1]]["s"] = "complete"
        sim[tids[1]]["raw_status"] = "fechado"

    # Cenário (c): simular nova tarefa
    sim["86ajteste1"] = {
        "n": "Tarefa de teste simulada",
        "s": "to do",
        "a": ["Usuário Teste"],
        "raw_status": "aberto"
    }

    return sim


def sync(clickup_tasks: dict, dry_run: bool = False) -> dict:
    """
    Compara ClickUp com tasks.json atual.
    Retorna relatório de mudanças e (se não dry_run) salva.
    """
    with open(TASKS_FILE) as f:
        stored_data = json.load(f)
    stored = stored_data["tasks"]

    novas, ch_status, ch_resp = [], [], []

    for tid, cu in clickup_tasks.items():
        if tid not in stored:
            novas.append(tid)
            stored[tid] = {
                "n": cu["n"],
                "s": cu["s"],
                "p": None,          # parent=null para novas (fora do escopo %)
                "a": cu["a"]
            }
            continue

        # Atualizar apenas campos dinâmicos
        changed = False
        if stored[tid]["s"] != cu["s"]:
            ch_status.append({
                "id": tid,
                "nome": stored[tid]["n"],
                "de": stored[tid]["s"],
                "para": cu["s"],
                "raw": cu["raw_status"]
            })
            stored[tid]["s"] = cu["s"]
            changed = True

        if set(stored[tid].get("a", [])) != set(cu["a"]):
            ch_resp.append({"id": tid, "nome": stored[tid]["n"],
                            "de": stored[tid].get("a"), "para": cu["a"]})
            stored[tid]["a"] = cu["a"]
            changed = True

        # NUNCA alterar "n" (nome) nem "p" (parent) automaticamente

    report = {
        "timestamp": now_str(),
        "novas": len(novas),
        "novas_ids": novas,
        "status": len(ch_status),
        "status_changes": ch_status,
        "responsaveis": len(ch_resp),
        "resp_changes": ch_resp,
        "total_tasks": len(stored),
        "changed": bool(novas or ch_status or ch_resp)
    }

    if not dry_run and report["changed"]:
        stored_data["tasks"] = stored
        stored_data["_meta"]["last_sync"] = now_str()
        stored_data["_meta"]["total"] = len(stored)
        with open(TASKS_FILE, "w") as f:
            json.dump(stored_data, f, ensure_ascii=False, indent=2)

    return report


def print_report(r: dict, dry_run: bool = False):
    mode = "DRY-RUN" if dry_run else "SYNC"
    print(f"\n=== RELATÓRIO {mode} — {r['timestamp']} BRT ===")
    print(f"  Total tarefas: {r['total_tasks']}")
    print(f"  {'➕' if r['novas'] else '✅'} Novas: {r['novas']}")
    if r['novas_ids']:
        for tid in r['novas_ids']:
            print(f"    • {tid}")
    print(f"  {'🔄' if r['status'] else '✅'} Status: {r['status']}")
    for c in r['status_changes']:
        print(f"    • {c['nome']}: {c['de']} → {c['para']} (raw: {c['raw']})")
    print(f"  {'👤' if r['responsaveis'] else '✅'} Responsáveis: {r['responsaveis']}")
    for c in r['resp_changes']:
        print(f"    • {c['nome']}: {c['de']} → {c['para']}")
    if not r['changed']:
        print("  ✅ Nenhuma mudança detectada.")
    print()


def run_tests():
    """Testa os 3 cenários antes de qualquer produção."""
    print("=== TESTES SIMULADOS ===\n")

    # Cenário (a): Nada mudou
    with open(TASKS_FILE) as f:
        stored = json.load(f)["tasks"]
    sim_a = {tid: {"n": d["n"], "s": d["s"], "a": d["a"], "raw_status": d["s"]}
             for tid, d in stored.items()}
    r_a = sync(sim_a, dry_run=True)
    assert not r_a["changed"], "FALHOU cenário (a): devia não ter mudanças"
    print(f"✅ Cenário (a) — Nada mudou: OK ({r_a['total_tasks']} tasks)")

    # Cenário (b): Algo mudou
    sim_b = dict(sim_a)
    tid_test = list(stored.keys())[0]
    sim_b[tid_test] = {**sim_b[tid_test], "s": "in progress", "raw_status": "em andamento"}
    r_b = sync(sim_b, dry_run=True)
    assert r_b["status"] >= 1, "FALHOU cenário (b): devia ter 1 mudança de status"
    print(f"✅ Cenário (b) — Algo mudou: OK ({r_b['status']} mudança de status)")

    # Cenário (c): Regra de negócio — status PT-BR
    raw_statuses = ["fechado", "entregue", "revisando", "em andamento",
                    "aguardando retorno", "aberto"]
    for raw in raw_statuses:
        mapped = STATUS_MAP.get(raw.lower().strip())
        assert mapped is not None, f"FALHOU: status '{raw}' não mapeado!"
    print(f"✅ Cenário (c) — Vocabulário PT-BR: {len(raw_statuses)} status mapeados OK")

    # Cenário (d): Nova tarefa
    sim_d = dict(sim_a)
    sim_d["86ajteste_nova"] = {"n": "Tarefa Nova Teste", "s": "to do", "a": [], "raw_status": "aberto"}
    r_d = sync(sim_d, dry_run=True)
    assert r_d["novas"] >= 1, "FALHOU cenário (d): devia detectar nova tarefa"
    print(f"✅ Cenário (d) — Nova tarefa: OK (detectada e parent=null)")

    print("\n✅ TODOS OS TESTES PASSARAM!\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="ClickUp API token")
    parser.add_argument("--test", action="store_true", help="Modo teste simulado")
    parser.add_argument("--dry-run", action="store_true", help="Busca mas não salva")
    args = parser.parse_args()

    # Sempre rodar testes primeiro
    run_tests()

    with open(CONFIG_FILE) as f:
        config = json.load(f)
    lista_id = config["lista_id"]

    if args.test:
        print("=== MODO SIMULADO ===")
        cu_tasks = simulated_clickup()
    elif args.token:
        print(f"=== BUSCANDO CLICKUP (lista {lista_id}) ===")
        cu_tasks = fetch_clickup(args.token, lista_id)
    else:
        print("Informe --token TOKEN ou --test")
        sys.exit(1)

    print(f"  Total coletado: {len(cu_tasks)} tarefas\n")
    report = sync(cu_tasks, dry_run=args.dry_run)
    print_report(report, dry_run=args.dry_run)

    # Exit code 0 = mudou (GitHub Actions usa para decidir se faz commit)
    # Exit code 2 = nada mudou
    sys.exit(0 if report["changed"] else 2)


if __name__ == "__main__":
    main()
