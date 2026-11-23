# Mufti AI — User Guide (naye users ke liye)

**Mufti AI aapki apni kitabon (PDF) se sawalon ke jawab deta hai — tafseel se, adab ke saath, aur
har baat ke saath kitab ke safhe (page) ka hawala.** Ye guide pehli baar istemal karne walon ke liye
hai. (English summary of each step is in *italics*.)

---

## 1. Pehli baar setup (sirf ek dafa)

1. **Python 3.12, Ollama, (optional) Tesseract install kijiye.** Details: README.md → "Windows quick start".
2. PowerShell kholiye:
   ```powershell
   cd D:\mufti-ai
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env        # sirf agar .env nahi hai
   ollama pull bge-m3                 # search ke liye (zaroori)
   ollama pull qwen3:1.7b             # offline jawab ke liye (optional)
   ```
3. **Cloud key (sab se bada farq):** `.env` file mein `GOOGLE_API_KEY=...` (ya `ANTHROPIC_API_KEY` /
   `OPENAI_API_KEY`) daaliye. Key ke bina jawab local model se aata hai — bahut dheema (2 GB GPU par
   minutes) aur fact-check nahi hota. *A cloud key gives fast, fact-checked answers.*
4. **Kitab daaliye:** PDF ko `D:\mufti-ai\data\books\` mein copy kijiye, phir app mein
   **My library → Index library** (scanned Urdu kitab mein OCR ki wajah se kaafi waqt lagta hai).
5. **Check kijiye sab theek hai:** `.\doctor.ps1` — har cheez ke saamne `[ OK ]`, `[WARN]` ya `[FAIL]`
   aur uska **hal (fix)** likha aata hai. Yehi check app mein **Guide → Setup check** mein bhi hai.

## 1b. Pehli baar app kholne par — welcome popup aur tour

- App ka interface **default English** mein hai.
- Pehli baar kholne par ek **welcome popup** aata hai: *Choose the language for directions* — English,
  Hinglish, اردو, हिन्दी. Jo zabaan chunenge, popup, **arrow wala tour** aur **Guide** usi zabaan mein ho jaate hain.
- **Show me around** dabaiye: arrows ke saath batata hai — *conversation yahan se shuru karein* (sawal ka
  box), *mic*, *jawab ka andaz*, *nayi conversation*, *library yahan hai*, *Topic index*, *Saved answers*, *AI model*, *Guide*.
- App update ke baad naya feature na dikhe to ek baar **Ctrl+F5** dabaiye (ab server browser ko har baar naya code check karne ko kehta hai).
  `→`/Enter aage, `←` peeche, Esc band.
- Baad mein zabaan badalni ho: header ka **🌐** button (popup dobara khulta hai), ya **Guide** ke andar
  "Directions language". Tour dobara: **Guide → ▶ Show the tour**.

## 2. Roz ka istemal (every day)

```powershell
cd D:\mufti-ai
# 1) Ollama chal raha ho (Start menu se "Ollama" kholiye) — cloud mode mein bhi search ke liye zaroori
# 2) App start:
.\start.ps1
```
Browser mein **http://localhost:786** kholiye. Pehli baar **Guide** khud khulta hai; baad mein
header ke **? Guide** button se.

## 3. Sawal kaise poochhein

- **Kisi bhi zabaan mein likhiye:** Urdu, Hindi, English ya Hinglish. Reply language box mein **Auto**
  rakhiye (jis zabaan mein sawal, usi mein jawab) ya khud chuniye.
- **Achhe sawal ke tips:**
  - Topic ka naam lijiye: *"Misaq-e-Madina kya tha? Tafseel se samjhao"* ✔️ — *"kuch batao"* ✖️
    (aisi soorat mein app aapko kitab ke chapters suggest karega).
  - Follow-up seedha poochhiye: *"aur detail mein samjhao"*, *"iska khulasa batao"* — pichhli baat yaad rehti hai.
  - Hawala chahiye to: *"ye kis book se hai?"* / *"reference kahan se hai?"* — kitab ka naam, musannif,
    publisher, ISBN aur pichhle jawab ke safhaat.
- **Starter topics:** welcome screen par "EXPLORE THE BOOKS" ke chips kitab ke asal chapters se bane hain — click kijiye.

## 4. Jawab ka andaz (Answer style) — ✎ box

| Style | Kab chuniye | Lambai |
|---|---|---|
| **Detailed** (default) | poora sabaq: background, har point, khulasa | 450-1100 words |
| **Short** | jaldi mein, seedha jawab | 80-180 words — *local model par sab se tez* |
| **Simple words** | naye seekhne wale / bachche; har mushkil lafz ka matlab | 200-450 words |
| **Study notes** | padhai / revision: points + "yaad rakhne ki baatein" | 200-500 words |

Har style mein **har baat ka hawala** aur **wahi fact-check** hota hai — style sirf likhne ka tareeqa badalta hai.
Jawab ke neeche **"Same question:"** buttons se wahi sawal doosre andaz mein ek click mein dobara mil jata hai.

## 5. Jawab ko kaise padhein

- **[1] [2] chips** → click karein: kitab ka asal page khulta hai (OCR text + "Open original PDF").
- **Sources** list: har hawale ka iqtibas (excerpt), PDF page aur printed page number.
- **Badges:**
  - ✓ **Fully / ◑ Partly answered from the book** — kitab ne poora ya aadha sawal cover kiya.
  - ✓ **Fact-checked against the book** — doosre AI pass ne har jumla kitab se milaya; ghalat jumle theek ya hata diye.
  - ◌ **Sources linked · not independently fact-checked** — local model ka jawab; hawale asli hain, khud check kar lijiye.
  - ↳ **Fallback used** — pasandeeda model busy/limit par tha, doosre model ne jawab diya (wajah neeche likhi hoti hai).
- **"Aage poochhiye · Ask next"** — agle 3 sawal jo isi kitab se jawab ho sakte hain. Click = naya sawal.
- **Jab jawab na mile:** app saaf batata hai ki *kitab mein ye mauzoo nahi hai*, ya *service (internet/quota)
  ka masla hai*, ya *page ka OCR padha nahi ja saka* — ye teeno alag cheezein hain.

## 6. Chapter explorer & Focus

**My library → ☰ Chapters** — kitab ke saare abwaab (chapters) aur sections page numbers ke saath.
- **Explain** — us chapter/section ka tafseeli sabaq (sirf usi hisse se search).
- **Summary** — study-notes andaz mein khulasa.
- **◎ Focus** — aapke agle saare sawal sirf usi hisse mein search honge. Composer ke upar
  "Focus: …" chip dikhta hai; **×** dabane se poori library phir se.
  Agar us hisse mein jawab na mile to app poori library search karta hai aur saaf batata hai.

## 6b. Topic index (▦)

Sidebar → **▦ Topic index**: dono kitabon ke saare chapters/sections (page numbers ke saath) aur key concepts
(English, Urdu, Hindi, Hinglish forms). Upar search kijiye — English lafz bhi Urdu titles dhoond leta hai
(jaise "equality" → آئینی مساوات کا حق, "madina" → دستور مدینہ). Har topic par **Explain**, **Summary**, **◎ Focus**.

## 6c. Photo, file aur drag & drop (📷 📎)

- **📷** dabaiye → camera khulega → page ko seedha, roshni mein rakh kar **● Capture**. (Phone/laptop camera; "⟲ Switch camera" se peeche wala camera.)
- **📎** dabaiye → folder se photo (JPG/PNG), PDF (pehle 5 pages) ya .txt/.md file chuniye. Ya file ko seedha **chat par drag karke chhod** dijiye. Screenshot ho to sawal box mein **Ctrl+V**.
- Text **isi computer par** padha jata hai (Urdu Nastaliq, Arabi, English, Hindi) — photo kahin nahi bheji jati, save bhi nahi hoti.
- Card mein text check/theek kijiye (zabaan ghalat padhi ho to *Text language* mein اردو / عربی / English / हिन्दी dabaiye), phir:
  - **✎ Explain this** — jawab **sirf aapki Islami kitabon se**, hawalon aur fact-check ke saath. Jo kitabon mein nahi, uska jawab "nahi mila" hoga.
  - **🔍 Find in my books** — ye ibarat kis kitab ke kis page par hai (bina AI, ~1 second). Wahan se *View page* ya *Explain this page*.
  - **Put in question box** — text box mein daal kar apna sawal likhiye.

## 7. Save, share, sunna, bolna

- **⧉ Copy** — jawab + hawale clipboard par. **⤓ Download** — `.md` file. **⎙ Print** — print / PDF.
- **🧠 Quiz me** — usi jawab se 3-4 MCQ sawal (jawab ki zabaan mein). Option chuniye → Sahi/Ghalat, wajah, aur kitab ke page ka chip. Har quiz ek chhoti AI call leta hai; quiz sirf us jawab ki fact-checked baaton se banta hai.
- **☆ Save** — jawab ko hamesha ke liye rakhiye. Sidebar mein **★ Saved answers**: search, Open (poora jawab hawalon ke saath), Download, aur Delete (do baar click). Conversation delete karne par bhi saved jawab rehta hai.
- **👍 / 👎** — jawab achha laga ya nahi. 👎 dabane par wajah chuniye (Wrong, Incomplete, "Book has it, but not found"…) aur chaho to page number likhiye. Ye sirf aapke computer par save hota hai aur jawab behtar karne ke liye test cases banane mein kaam aata hai.
- **◖ Read aloud** — browser ki awaaz mein sunaiye (installed voices par depend).
- **♩ Mic** — bol kar poochhiye (local Whisper; pehli dafa model download hota hai):
  1. Mic dabaiye → upar laal **Recording** patti aur timer dikhega.
  2. Boliye, phir mic **dobara dabaiye** ya **■ Stop**.
  3. Aapki baat **pehle sawal ke box mein likhi aati hai** — padh kar theek kar lijiye, phir **Send ↑** dabaiye. Khud se kuch send nahi hota.
  4. Galti se dab gaya? **✕ Cancel** ya **Esc** — recording phenk di jaati hai. 0.7 second se chhota tap khud hi ignore hota hai; 60 second par recording khud ruk jaati hai.
- **Recent conversations** (sidebar) — purani baat-cheet; **Delete this conversation** se mitaiye.
- Link: `http://localhost:786/?session=<id>` wahi conversation kholta hai; `?theme=dark` dark mode.

## 8. Models & fallback

Sidebar → **Models & fallback**: Auto (cloud pehle, Ollama aakhir mein), kisi ek cloud ko pehle rakhna,
ya **Ollama only** (sab kuch isi computer par, internet nahi — par dheema). Har jawab ke neeche likha hota
hai ki kis model ne asal mein jawab diya.
**Gemini free tier:** taqreeban 20 requests/din **har model**; ek sawal ≈ 2-3 requests. App khud doosre
Gemini models par shift karta hai. Zyada istemal ke liye paid key behtar hai.

## 9. Keyboard shortcuts

`Enter` bhejiye · `Shift+Enter` nayi line · `/` sawal box · `Alt+N` nayi conversation ·
`Alt+L` My library · `Alt+G` Guide · `Esc` dialog band.

## 10. Masle aur hal (Troubleshooting)

| Masla | Hal |
|---|---|
| "Ollama offline" / search fail | Start menu se Ollama kholiye; `.\doctor.ps1` chalaiye |
| Jawab bahut dheema | Cloud key daaliye; ya **Short** style; Models & fallback mein cloud mode |
| "quota or rate limit" | Gemini ki daily limit khatam — kal tak intezar, doosri key, ya local model |
| Naya PDF dikh nahi raha | My library → Index library; `doctor.ps1` "new PDF not indexed" batata hai |
| Urdu ajeeb dikh raha | Noto Nastaliq Urdu font install kijiye |
| Server nahi khul raha | `.\start.ps1` dobara; `server-current-error.log` dekhiye |

> **Yaad rahe:** Mufti AI ek ilmi madadgar hai jo sirf aapki kitabon se batata hai. Zaati mas'ale
> (personal ruling / fatwa) ke liye hamesha kisi mustanad alim se rujoo kijiye.
