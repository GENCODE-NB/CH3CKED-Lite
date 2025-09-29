# CH3CKED-Lite — Garena Account Checker (Termux / VPS / PC)

ตรวจว่า `username:password` ของคุณยังล็อกอินผ่าน Garena SSO ได้หรือไม่  
- ✅ ผ่าน → `results/working.csv` + `results/valid_accounts.txt`  
- ❌ ไม่ผ่าน → `results/failed.csv`  

> ใช้กับ **บัญชีของคุณเอง** เท่านั้น

## วิธีใช้งาน (Termux / VPS / PC)
```bash
python -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.termux.txt
python LiteBot.py
# → ใส่ชื่อไฟล์ .txt (ลิสต์ username:password บรรทัดละ 1)


md
