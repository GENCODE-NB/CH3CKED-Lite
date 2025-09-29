# BotPlay.py — Garena SSO checker (Playwright, Ubuntu-friendly)
# ใช้กับ "บัญชีของคุณเอง" เท่านั้น
import asyncio, csv, os, time, random, re
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Set
from playwright.async_api import async_playwright, Browser, Page
from tqdm.asyncio import tqdm_asyncio

LOGIN_URL = "https://sso.garena.com/universal/login?locale=th"
PROFILE_URLS = ["https://account.garena.com/profile", "https://account.garena.com/"]
TIMEOUT_MS = 25000
HEADLESS = True
CONCURRENCY = 3
PAUSE_BETWEEN = 0.8
JITTER = (0.15, 0.45)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"

RESULTS = Path("results"); RESULTS.mkdir(exist_ok=True, parents=True)
LOGS = Path("logs"); LOGS.mkdir(exist_ok=True, parents=True)
WORKING = RESULTS/"working.csv"
FAILED  = RESULTS/"failed.csv"

FAIL_HINTS = ["invalid","incorrect","wrong","error","failed","try again","ไม่ถูกต้อง","ล้มเหลว","ผิดพลาด","ไม่สำเร็จ","กรอก"]
NICK_SELECTORS = ['[data-testid="display-name"]','input[name="displayName"]','.profile-name','.user-name','.nickname','h1','h2','span.user-name']
LOGIN_SELECTORS = ['input[name="username"]','input[type="email"]','input[name="password"]','button[type="submit"]']

def log(msg:str):
    print(time.strftime("[%Y-%m-%d %H:%M:%S] "), msg)

def read_accounts(path:str)->List[Tuple[str,str]]:
    out=[]; seen=set()
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            s=line.strip()
            if ":" not in s: continue
            u,p=s.split(":",1)
            key=f"{u.strip()}:{p.strip()}"
            if key in seen: continue
            seen.add(key); out.append((u.strip(),p.strip()))
    return out

async def still_login(page:Page)->bool:
    for sel in LOGIN_SELECTORS:
        if await page.query_selector(sel):
            return True
    return False

async def extract_nick(page:Page)->Optional[str]:
    for sel in NICK_SELECTORS:
        el = await page.query_selector(sel)
        if not el: continue
        tag = (await el.evaluate("e=>e.tagName||''")).lower()
        try:
            val = await (el.input_value() if tag=="input" else el.inner_text())
            if val:
                name = val.strip().replace("\n"," ")
                if 1<=len(name)<=120: return name
        except: continue
    return None

async def fill_login(page:Page,u:str,p:str):
    for sel in ['input[name="username"]','input[type="email"]','input[type="text"]']:
        el = await page.query_selector(sel)
        if el: await el.fill(u); break
    for sel in ['input[name="password"]','input[type="password"]']:
        el = await page.query_selector(sel)
        if el: await el.fill(p); break
    btn = await page.query_selector('button[type="submit"], text=/log\\s*in/i')
    if btn: await btn.click()
    else:
        pass_input = await page.query_selector('input[type="password"],input[name="password"]')
        if pass_input: await pass_input.press("Enter")

async def login_and_get(browser:Browser,u:str,p:str)->Tuple[Optional[str],str]:
    ctx = await browser.new_context(user_agent=UA)
    page = await ctx.new_page()
    try:
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await fill_login(page,u,p)
        try:
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
        except:
            await page.wait_for_timeout(1500)

        html = (await page.content()).lower()
        if await still_login(page):
            kw = next((k for k in FAIL_HINTS if k in html), None)
            await ctx.close()
            return None, f"login_fail:{kw or 'login_form_present'}"

        nick=None
        for url in PROFILE_URLS:
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(600)
                nick = await extract_nick(page)
                if nick: break
            except Exception as e:
                log(f"visit profile warn [{u}] {url}: {e}")

        if not nick:
            await ctx.close()
            return None, "no_nickname_selector"

        await ctx.close()
        return nick, "ok"
    except Exception as e:
        try: await ctx.close()
        except: pass
        return None, f"exception:{e}"

async def worker(sem, browser, job, out):
    u,p = job
    async with sem:
        nick, reason = await login_and_get(browser,u,p)
        out.append((u,nick,reason))
        await asyncio.sleep(PAUSE_BETWEEN + random.uniform(*JITTER))

async def main():
    path = input("ไฟล์ accounts (เช่น accounts.txt): ").strip()
    if not os.path.exists(path):
        log(f"ไม่พบไฟล์: {path}"); return
    pairs = read_accounts(path)
    log(f"โหลดบัญชี {len(pairs)} ไอดี")

    # init CSV
    if not WORKING.exists():
        with open(WORKING,"w",newline="",encoding="utf-8") as f: csv.writer(f).writerow(["username","nickname"])
    if not FAILED.exists():
        with open(FAILED,"w",newline="",encoding="utf-8") as f: csv.writer(f).writerow(["username","reason"])

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        sem = asyncio.Semaphore(CONCURRENCY)
        results=[]
        tasks = [asyncio.create_task(worker(sem,browser,j,results)) for j in pairs]
        for _ in tqdm_asyncio.as_completed(tasks, total=len(tasks), desc="Checking"):
            await _
        await browser.close()

    ok,fail=0,0
    with open(WORKING,"a",newline="",encoding="utf-8") as wf, \
         open(FAILED,"a",newline="",encoding="utf-8") as ff:
        w_ok=csv.writer(wf); w_fail=csv.writer(ff)
        for u,nick,reason in results:
            if nick:
                w_ok.writerow([u,nick]); ok+=1
            else:
                w_fail.writerow([u,reason]); fail+=1
    log(f"SUMMARY ok={ok} fail={fail} total={len(results)}")
    log("done.")

if __name__=="__main__":
    asyncio.run(main())
