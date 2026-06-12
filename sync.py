import re, json, urllib.request, os
from datetime import datetime

CLICKUP_TOKEN = os.environ["CLICKUP_TOKEN"]
LIST_ID = "901327467073"

SM = {"fechado":"complete","em andamento":"in progress","aberto":"to do",
      "aguardando retorno":"in progress","entregue":"complete"}

def fetch_tasks(page=0):
    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task?subtasks=true&include_closed=true&order_by=created&page={page}"
    req = urllib.request.Request(url, headers={"Authorization": CLICKUP_TOKEN})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# Buscar todas as tarefas
all_tasks = []
for page in range(3):
    data = fetch_tasks(page)
    tasks = data.get("tasks", [])
    all_tasks.extend(tasks)
    if len(tasks) < 100:
        break

print(f"Total tarefas: {len(all_tasks)}")

# Ler o painel atual
with open("painel.html", "r") as f:
    html = f.read()

updated = 0
for task in all_tasks:
    tid = task["id"]
    status_pt = task["status"]
    new_status = SM.get(status_pt, "to do")
    assignees = [a["username"] for a in task.get("assignees", [])]
    a_str = ','.join([f'"{a}"' for a in assignees])

    pattern = f'"{tid}"' + r':\{"n":"([^"]+)","s":"([^"]+)","p":([^,]+),"a":\[([^\]]*)\]'
    m = re.search(pattern, html)
    if m:
        old = m.group(0)
        new = f'"{tid}"' + ':{"n":"' + m.group(1) + '","s":"' + new_status + '","p":' + m.group(3) + ',"a":[' + a_str + ']'
        if old != new:
            html = html.replace(old, new, 1)
            updated += 1

# Atualizar data
now = datetime.now().strftime("%d/%m/%Y %H:%M")
html = re.sub(r'<b id="syncDate">[^<]+</b>', f'<b id="syncDate">{now}</b>', html)
html = re.sub(r'id="ftNote">[^<]+', f'id="ftNote">Última atualização: {now}', html)

with open("painel.html", "w") as f:
    f.write(html)

print(f"Atualizados: {updated} — {now}")
