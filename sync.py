"""
sync.py — Atualiza LAST_SYNC_UTC no painel BCP Edge UOL (Glete)
Roda via GitHub Actions a cada hora.
"""
import re, os, sys, shutil
from datetime import datetime, timezone, timedelta

CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN", "")
if not CLICKUP_TOKEN:
    print("ERRO: CLICKUP_TOKEN nao encontrado nos secrets do GitHub!")
    print("Adicione em: Settings > Secrets and variables > Actions > New repository secret")
    print("  Nome: CLICKUP_TOKEN")
    print("  Valor: pk_118043914_J5M4TLXNJIC4RUA4G540YT309FSRVJFC")
    sys.exit(1)

LIST_ID   = "901329195447"   # 2° Região - Glete
BRT       = timezone(timedelta(hours=-3))

# Mapeamento de status ClickUp -> status interno do painel
SM = {
    "fechado":    "shipped",
    "entregue":   "shipped",
    "concluído":  "shipped",
    "revisando":  "in progress",
    "em andamento":"in progress",
    "aberto":     "backlog",
}

import urllib.request, json

def fetch_tasks():
    """Busca todas as tarefas da lista no ClickUp."""
    tasks = {}
    for page in range(5):
        url = (
            "https://api.clickup.com/api/v2/list/{}/task"
            "?include_closed=true&page={}&order_by=created"
        ).format(LIST_ID, page)
        req = urllib.request.Request(url, headers={"Authorization": CLICKUP_TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                batch = data.get("tasks", [])
                print("Pagina {}: {} tarefas".format(page, len(batch)))
                if not batch:
                    break
                for t in batch:
                    raw = t.get("status", {})
                    raw_str = raw.get("status", "aberto") if isinstance(raw, dict) else str(raw)
                    tasks[t["id"]] = {
                        "name":   t["name"],
                        "status": SM.get(raw_str.lower(), "backlog"),
                        "raw":    raw_str,
                    }
        except Exception as e:
            print("ERRO pagina {}: {}".format(page, e))
            raise
    return tasks

# ── Buscar tarefas ──────────────────────────────────────────────────────────
all_tasks = fetch_tasks()
print("Total: {} tarefas".format(len(all_tasks)))
if not all_tasks:
    print("ERRO: nenhuma tarefa retornada pelo ClickUp")
    sys.exit(1)

# ── Atualizar status das fases no painel ────────────────────────────────────
# IDs conhecidos e seus campos no HTML (status embutido no JS como string)
STATUS_MAP_HTML = {
    "shipped":     "shipped",
    "in progress": "in progress",
    "backlog":     "backlog",
}

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Atualizar LAST_SYNC_UTC e o comentário com horário BRT correto
utc_now  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
brt_date = datetime.now(BRT).strftime("%d/%m/%Y")
brt_time = datetime.now(BRT).strftime("%H:%M")
html = re.sub(
    r"const LAST_SYNC_UTC = \"[^\"]*\";\s*//[^\n]*",
    'const LAST_SYNC_UTC = "{}";   // dados lidos do ClickUp em {} {} (BRT)'.format(
        utc_now, brt_date, brt_time
    ),
    html
)

# Atualizar cada tarefa do ClickUp que aparece no HTML pelo seu id
changed = 0
for tid, info in all_tasks.items():
    new_status = info["status"]
    # Encontrar ocorrências do id no HTML e atualizar status próximo
    # Padrão: id:'XXXX', ...status:'YYY'  — pode ter atributos no meio
    pattern = r"(id:'" + re.escape(tid) + r"'[^}]{0,200}?status:')(shipped|in progress|backlog)(')"
    def replacer(m, ns=new_status):
        old = m.group(2)
        if old != ns:
            return m.group(1) + ns + m.group(3)
        return m.group(0)
    new_html, n = re.subn(pattern, replacer, html)
    if n > 0:
        old_matches = re.findall(pattern, html)
        for om in old_matches:
            if om[1] != new_status:
                print("  {} «{}»: {} → {}".format(tid, info["name"][:40], om[1], new_status))
                changed += 1
        html = new_html

# Atualizar também o comentário de quantidade/horário
brt_now = datetime.now(BRT).strftime("%d/%m/%Y às %H:%M")
html = re.sub(
    r'Fonte: ClickUp · lista "2° Região - Glete" \([^)]+\)\.',
    'Fonte: ClickUp · lista "2° Região - Glete" ({} tarefas, lidas em {} BRT).'.format(
        len(all_tasks), brt_now
    ),
    html
)

print("Status atualizados: {} fases".format(changed))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

shutil.copy("index.html", "painel.html")

print("index.html e painel.html atualizados — {} BRT".format(brt_now))
