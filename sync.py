import re, json, urllib.request, os, sys, traceback
from datetime import datetime

TOKEN = os.environ["CLICKUP_TOKEN"]
LIST_ID = "901327467073"

print(f"Token primeiros 10 chars: {TOKEN[:10]}...", flush=True)
print(f"Token tamanho: {len(TOKEN)}", flush=True)

SM = {
    "fechado":            "complete",
    "em andamento":       "in progress",
    "aberto":             "to do",
    "aguardando retorno": "in progress",
    "entregue":           "complete",
}

def fetch(page):
    url = (f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"
           f"?subtasks=true&include_closed=true&order_by=created&page={page}")
    print(f"Fetching: {url[:80]}", flush=True)
    req = urllib.request.Request(url, headers={
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Status: {r.status}", flush=True)
        return json.loads(r.read())

# Testar conexão primeiro
try:
    test_req = urllib.request.Request(
        "https://api.clickup.com/api/v2/user",
        headers={"Authorization": TOKEN}
    )
    with urllib.request.urlopen(test_req, timeout=10) as r:
        user = json.loads(r.read())
        print(f"User OK: {user['user']['username']}", flush=True)
except Exception as e:
    print(f"ERRO USER: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

# Buscar todas as páginas
all_tasks = []
for page in range(5):
    try:
        data = fetch(page)
        tasks = data.get("tasks", [])
        all_tasks.extend(tasks)
        print(f"Página {page}: {len(tasks)} tarefas", flush=True)
        if len(tasks) < 100:
            break
    except Exception as e:
        print(f"Erro página {page}: {e}", flush=True)
        traceback.print_exc()
        if page == 0:
            sys.exit(1)
        break

print(f"Total: {len(all_tasks)} tarefas", flush=True)

with open("painel.html", "r", encoding="utf-8") as f:
    html = f.read()

updated = 0
for task in all_tasks:
    tid    = task["id"]
    status = SM.get(task.get("status", "aberto"), "to do")
    names  = [a.get("username","") for a in task.get("assignees", [])]
    a_str  = ",".join(f'"{n}"' for n in names if n)

    pat = f'"{tid}"' + r':\{"n":"([^"]+)","s":"([^"]+)","p":([^,]+),"a":\[([^\]]*)\]'
    m   = re.search(pat, html)
    if not m:
        continue

    new_entry = f'"{tid}"' + ':{"n":"' + m.group(1) + '","s":"' + status + '","p":' + m.group(3) + ',"a":[' + a_str + ']'
    if m.group(0) != new_entry:
        html = html.replace(m.group(0), new_entry, 1)
        updated += 1

now = datetime.now().strftime("%d/%m/%Y %H:%M")
html = re.sub(r'<b id="syncDate">[^<]+</b>', f'<b id="syncDate">{now}</b>', html)
html = re.sub(r'id="ftNote">[^<]+',          f'id="ftNote">Última atualização: {now}', html)

with open("painel.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Atualizados: {updated} — {now}", flush=True)
