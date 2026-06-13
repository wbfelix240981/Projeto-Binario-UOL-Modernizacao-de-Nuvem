import re, json, urllib.request, os
from datetime import datetime

TOKEN = os.environ["CLICKUP_TOKEN"]
LIST_ID = "901327467073"

SM = {
    "fechado":           "complete",
    "em andamento":      "in progress",
    "aberto":            "to do",
    "aguardando retorno":"in progress",
    "entregue":          "complete",
}

def fetch(page):
    url = (f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"
           f"?subtasks=true&include_closed=true&order_by=created&page={page}")
    req = urllib.request.Request(url, headers={"Authorization": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# Buscar todas as páginas
all_tasks = []
for page in range(5):
    data = fetch(page)
    tasks = data.get("tasks", [])
    all_tasks.extend(tasks)
    print(f"Página {page}: {len(tasks)} tarefas")
    if len(tasks) < 100:
        break

print(f"Total: {len(all_tasks)} tarefas")

with open("painel.html", "r") as f:
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

with open("painel.html", "w") as f:
    f.write(html)

print(f"Atualizados: {updated} — {now}")
