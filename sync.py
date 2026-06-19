import json, re, urllib.request, os, sys
from datetime import datetime, timezone, timedelta

CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN", "")
if not CLICKUP_TOKEN:
    print("ERRO: CLICKUP_TOKEN nao encontrado!")
    sys.exit(1)

LIST_ID = "901327467073"
BRT = timezone(timedelta(hours=-3))

SM = {
    "fechado": "complete",
    "entregue": "complete",
    "revisando": "complete",
    "em andamento": "in progress",
    "aberto": "to do"
}

parent = {
    "86ahx8exe":"null","86ahx9315":"null","86ahx8c64":"null","86ahx948g":"null",
    "86ahx73pc":"null","86ahx750d":"null","86ahx7515":"null","86aj2p7gb":"null","86ahxbff7":"null",
    "86ahx8ffr":"86ahx8exe","86ahx8hrf":"86ahx8ffr","86ahx8j8p":"86ahx8hrf",
    "86ahx8qbe":"86ahx8hrf","86ahx8ujt":"86ahx8hrf","86ahx8hrt":"86ahx8ffr",
    "86ahx8jav":"86ahx8hrt","86ahx8t1z":"86ahx8hrt",
    "86ahx92xw":"86ahx9315","86ahx940c":"86ahx9315",
    "86ahx8cmc":"86ahx8c64","86aj0rzxf":"86ahx8cmc","86ahx91xf":"86ahx8c64","86aj0rzz6":"86ahx91xf",
    "86ahx9399":"86ahx8c64","86ahx93bm":"86ahx9399","86ahx93cr":"86ahx9399",
    "86ahx94tb":"86ahx948g","86ahx95ew":"86ahx948g","86ahx9cx5":"86ahx95ew","86ahx97ux":"86ahx95ew",
    "86ahx9jfb":"86ahx948g","86ahx9r7f":"86ahx948g",
    "86aj3mnd7":"86ahx948g","86aj3mj94":"86ahx948g","86aj3mfju":"86ahx948g",
    "86aj3rxnm":"86ahx948g","86aj3qkud":"86ahx948g","86aj3qg6y":"86ahx948g",
    "86aj3w78n":"86ahx948g","86aj3wq76":"86ahx948g","86aj402pa":"86ahx948g",
    "86aj2pc7t":"86ahx8nun",
    "86aj2u1m1":"86aj2p7gb",
    "86ahx758f":"86ahx73pc","86ahx7rpe":"86ahx758f","86ahx7ru4":"86ahx7rpe",
    "86ahx7vfd":"86ahx7ru4","86ahx81nc":"86ahx7ru4","86ahx7w1k":"86ahx7rpe",
    "86ahx7w9m":"86ahx7w1k","86ahx7wcg":"86ahx7w1k","86ahx7w3q":"86ahx7rpe",
    "86ahx7wgu":"86ahx7w3q","86ahx7wjm":"86ahx7w3q","86ahx81te":"86ahx7rpe",
    "86ahx8211":"86ahx81te","86ahx821p":"86ahx81te","86ahx822w":"86ahx81te",
    "86ahx7x5e":"86ahx758f","86ahx7x9p":"86ahx7x5e","86ahx7xdq":"86ahx7x9p",
    "86ahx7xfa":"86ahx7x9p","86ahx7xgr":"86ahx7x9p","86ahx7xm8":"86ahx7x5e",
    "86ahx7xtg":"86ahx7xm8","86ahx7xue":"86ahx7xm8","86ahx82kf":"86ahx7x5e",
    "86ahzgkpu":"86ahx750d","86ahx75gf":"86ahzgkpu","86ahx75pt":"86ahzgkpu",
    "86ahx7zrd":"86ahx75pt","86ahx815n":"86ahx7zrd","86ahx7zzn":"86ahx75pt","86ahx81pm":"86ahx7zzn",
    "86ahx80uu":"86ahx75pt","86ahx81qt":"86ahx80uu","86ahx80vh":"86ahx75pt","86ahx81t2":"86ahx80vh",
    "86ahx7r2a":"86ahx750d","86ahx7rfu":"86ahx7r2a","86ahx7rgd":"86ahx7rfu",
    "86ahx7znj":"86ahx7rfu","86ahx7zq3":"86ahx7rfu","86ahx7rnw":"86ahx7rfu",
    "86ahx7tmg":"86ahx7r2a","86ahx7xuu":"86ahx7tmg","86ahx897c":"86ahx7xuu","86ahx898k":"86ahx7xuu",
    "86ahx7xvw":"86ahx7tmg","86ahx8993":"86ahx7xvw","86ahx899t":"86ahx7xvw",
    "86ahx7xwn":"86ahx7tmg","86ahx89ed":"86ahx7xwn","86ahx89fm":"86ahx7xwn",
    "86ahx89gr":"86ahx7xwn","86ahx89rd":"86ahx7xwn","86ahx89qr":"86ahx7xwn",
    "86ahx7y8e":"86ahx7tmg","86ahx89jv":"86ahx7y8e","86ahx89kw":"86ahx7y8e",
    "86ahx89n9":"86ahx7y8e","86ahx89yu":"86ahx7y8e","86ahx89zb":"86ahx7y8e",
    "86ahx7ubv":"86ahx7r2a","86ahx7uu8":"86ahx7r2a","86ahx8bq9":"86ahx7uu8","86ahx8bv8":"86ahx7uu8",
    "86ahzgvc0":"86ahx7r2a","86ahx7v6d":"86ahzgvc0","86ahx7vc2":"86ahzgvc0",
    "86ahx7vnc":"86ahzgvc0","86ahx7vvm":"86ahzgvc0","86ahx7wv8":"86ahzgvc0","86ahx80x3":"86ahzgvc0",
    "86ahx7r4a":"86ahx750d","86ahx8jqq":"86ahx7r4a","86ahx8jxt":"86ahx8jqq",
    "86ahx8k6v":"86ahx8jqq","86ahx8n9x":"86ahx8jqq","86ahx8nb9":"86ahx8jqq",
    "86ahx878m":"86ahx7r4a","86ahx87jh":"86ahx878m","86ahx87nk":"86ahx878m",
    "86ahx87qf":"86ahx878m","86ahx87y7":"86ahx878m","86ahx88gh":"86ahx878m",
    "86ahx88ku":"86ahx878m","86ahx88n3":"86ahx878m","86ahx89k0":"86ahx7r4a",
    "86ahx89qd":"86ahx7r4a","86ahx8pcm":"86ahx89qd",
    "86ahx89w3":"86ahx7r4a","86ahx89ub":"86ahx89w3","86ahx89vp":"86ahx89w3","86ahx89wk":"86ahx89w3",
    "86ahx8a17":"86ahx89w3","86ahx8a23":"86ahx89w3","86ahx8a3h":"86ahx89w3",
    "86ahx8aax":"86ahx89w3","86ahx8aej":"86ahx89w3","86ahx8apy":"86ahx89w3",
    "86ahx8axu":"86ahx89w3","86ahx8ayh":"86ahx89w3","86ahx8b0p":"86ahx89w3",
    "86ahx8b1a":"86ahx89w3","86ahx8b2r":"86ahx89w3","86ahx8b59":"86ahx89w3",
    "86ahx8b5q":"86ahx89w3","86ahx8b6w":"86ahx89w3","86ahx8b71":"86ahx89w3",
    "86ahx8b79":"86ahx89w3","86ahx8b81":"86ahx89w3","86ahx8b8n":"86ahx89w3",
    "86ahx8b8u":"86ahx89w3","86ahx8b98":"86ahx89w3","86ahx8ba7":"86ahx89w3",
    "86ahx8bb4":"86ahx89w3","86ahx8bby":"86ahx89w3","86ahx8bbm":"86ahx89w3",
    "86ahx8bcf":"86ahx89w3","86ahx8dep":"86ahx89w3","86ahx8dje":"86ahx89w3",
    "86ahx8dp6":"86ahx89w3","86ahx8dtx":"86ahx89w3","86ahx8dwu":"86ahx89w3","86ahx8f6j":"86ahx89w3",
    "86ahx83r4":"86ahx750d","86ahx8gar":"86ahx83r4","86ahx8nfv":"86ahx8gar",
    "86ahx8ynx":"86ahx7515","86ahx902u":"86ahx8ynx","86ahx9053":"86ahx902u","86ahx906n":"86ahx902u",
    "86ahx8pua":"86ahx7515","86ahx90a4":"86ahx8pua","86ahx90ew":"86ahx90a4",
    "86ahx90fe":"86ahx90a4","86ahx90g1":"86ahx90a4","86ahx90gx":"86ahx90a4","86ahx90jd":"86ahx90a4",
    "86ahx90at":"86ahx8pua","86ahx90kh":"86ahx90at","86ahx90b9":"86ahx8pua","86ahx90m5":"86ahx90b9",
    "86ahx8r5b":"86ahx7515","86ahx8r8z":"86ahx7515","86ahx8rdd":"86ahx7515",
    "86ahx8nun":"86ahx7515","86ahx8u6h":"86ahx8nun","86ahx8tpw":"86ahx8nun",
    "86ahx8tww":"86ahx8nun","86ahx8u2q":"86ahx8nun","86ahx8uhu":"86ahx8nun",
    "86ahx911h":"86ahx8nun","86ahxbze1":"86ahx8nun",
    "86ahx8v98":"86ahx7515","86ahx8vk3":"86ahx7515","86ahxbfy1":"86ahxbff7",
}

def fetch_tasks(page):
    url = "https://api.clickup.com/api/v2/list/{}/task?include_closed=true&subtasks=true&page={}&order_by=created".format(LIST_ID, page)
    req = urllib.request.Request(url, headers={"Authorization": CLICKUP_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            tasks = data.get("tasks", [])
            print("Pagina {}: {} tarefas".format(page, len(tasks)))
            return tasks
    except Exception as e:
        print("ERRO pagina {}: {}".format(page, e))
        raise

all_tasks = {}
for page in range(3):
    tasks = fetch_tasks(page)
    if not tasks:
        break
    for t in tasks:
        status_obj = t.get("status", "aberto")
        status_raw = status_obj.get("status", "aberto") if isinstance(status_obj, dict) else str(status_obj)
        s = SM.get(status_raw, "to do")
        if status_raw not in SM:
            print("AVISO status desconhecido: {} em {} - {}".format(status_raw, t["id"], t["name"]))
        all_tasks[t["id"]] = {
            "n": t["name"],
            "s": s,
            "a": [a["username"] for a in t.get("assignees", [])]
        }

print("Total: {} tarefas".format(len(all_tasks)))
if len(all_tasks) == 0:
    print("ERRO: Nenhuma tarefa coletada!")
    sys.exit(1)

lines = []
for tid, data in all_tasks.items():
    par = parent.get(tid, "null")
    p = '"{}"'.format(par) if par != "null" else "null"
    nome_safe = data["n"].replace('"', '\\"')
    a = ",".join(['"{}"'.format(x) for x in data["a"]])
    lines.append('"{}": {{"n":"{}","s":"{}","p":{},"a":[{}]}}'.format(
        tid, nome_safe, data["s"], p, a))

tasks_js = "const TASKS = {\n" + ",\n".join(lines) + "\n}"

with open("painel.html", "r") as f:
    html = f.read()

s_idx = html.find("const TASKS = {")
e_idx = html.find("\nconst TOP_ORDER", s_idx)
if s_idx != -1 and e_idx != -1:
    html = html[:s_idx] + tasks_js + html[e_idx:]
else:
    print("AVISO: nao encontrou bloco TASKS no painel.html")

html = re.sub(r'const TOP_ORDER = \[.*?\];',
    'const TOP_ORDER = ["86ahx8exe","86ahx9315","86ahx8c64","86ahx948g","86ahx73pc","86ahx750d","86ahx7515","86aj2p7gb","86ahxbff7"];', html)
html = re.sub(r'const PROGRESS_GROUPS = (?:new Set\()?\[.*?\]\)?;',
    'const PROGRESS_GROUPS = new Set(["86ahx8c64","86ahx948g","86ahx73pc","86ahx750d","86ahx7515","86aj2p7gb"]);', html)

now_str = datetime.now(BRT).strftime("%d/%m/%Y %H:%M")
html = re.sub(r'<b id="syncDate">[^<]*</b>', '<b id="syncDate">{}</b>'.format(now_str), html)
html = re.sub(r'id="ftNote">[^<]+', 'id="ftNote">Auto-sync: {} BRT'.format(now_str), html)

with open("painel.html", "w") as f:
    f.write(html)

print("painel.html atualizado - {} BRT".format(now_str))
