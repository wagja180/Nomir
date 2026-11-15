# Nomir

هذا المستودع يحوي مشروعين مستقلّين لا علاقة لأحدهما بالآخر:

1. **بوت تحليل السوق ومناطق البيع/الشراء** (الكود في `bot/` و`main.py`) — موثّق أدناه.
2. **مهارات Claude لإدارة حساب إنستغرام** (المجلدان `skills/` و`skills-ar/`) — موثّقة في
   القسم الإنجليزي/العربي أسفل هذه الصفحة.

---

## بوت تحليل السوق ومناطق البيع والشراء

بوت بايثون يحلل أسواق العملات الرقمية، يكتشف **مناطق العرض/الطلب (الدعم والمقاومة)**
آلياً من بيانات الشموع، ويولّد إشارات **شراء/بيع** عند ارتداد السعر من هذه المناطق
مع تأكيد من المؤشرات الفنية (RSI, EMA, ATR). يدعم أيضاً **تنفيذ صفقات حقيقية**
عبر أي منصة تداول يدعمها [ccxt](https://github.com/ccxt/ccxt) (مثل Binance).

## ⚠️ تحذير مهم قبل الاستخدام

- هذا البرنامج **أداة مساعدة للتحليل الفني**، وليس نصيحة استثمارية، ولا يضمن الربح.
- الأسواق المالية تحمل مخاطر خسارة حقيقية لرأس المال. لا تضع أموالاً لا تتحمل خسارتها.
- **ابدأ دائماً بوضع sandbox/testnet** ثم بمبالغ صغيرة جداً قبل أي استخدام جدي.
- شغّل أمر `backtest` أولاً لفهم أداء الاستراتيجية تاريخياً قبل التفكير بالتداول الحقيقي.
- البوت لا ينفذ أي أمر حقيقي إلا إذا مررت **كلا** الخيارين `--live` و `--confirm` معاً،
  ووجدت مفاتيح API صالحة في `.env`. بدون ذلك فهو يعمل بوضع تجربة (dry-run) دائماً.
- لا تُشارك مفاتيح API الخاصة بك مع أحد، ولا ترفع ملف `.env` إلى git (مُستثنى بالفعل
  في `.gitignore`).

## التثبيت

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# عدّل .env: ضع EXCHANGE_ID ومفاتيح API إن رغبت بالتنفيذ الحقيقي
```

## طريقة عمل الاستراتيجية

1. **اكتشاف المناطق**: يبحث البوت عن القمم والقيعان المحلية (swing highs/lows) في
   الشموع، ويجمّع القريبة منها معاً في مناطق "عرض" (مقاومة) فوق السعر و"طلب" (دعم)
   تحته. كل منطقة لها "قوة" = عدد مرات ارتداد السعر منها سابقاً.
2. **شرط الإشارة**: عندما يقترب السعر من منطقة طلب ضمن اتجاه صاعد عام (EMA50 > EMA200)
   وتظهر شمعة صاعدة تؤكد الارتداد و RSI ليس في تشبع شرائي → إشارة **شراء**.
   والعكس عند منطقة عرض ضمن اتجاه هابط → إشارة **بيع**.
3. **وقف الخسارة والهدف**: وقف الخسارة يوضع خلف حد المنطقة بهامش من ATR، والهدف عند
   أقرب منطقة معاكسة (أو بنسبة مكافأة/خطر دنيا محددة في `.env`). تُرفض أي إشارة لا
   تحقق نسبة المكافأة/الخطر الدنيا (`MIN_REWARD_RISK_RATIO`).
4. **حجم الصفقة**: يُحسب تلقائياً بحيث لا تتجاوز الخسارة المحتملة نسبة `RISK_PER_TRADE`
   من رصيدك المتاح (إدارة مخاطر أساسية؛ وليست ضماناً ضد الخسارة).

## الاستخدام

### 1) تحليل السوق فقط (بدون تنفيذ)

```bash
python main.py analyze --symbol BTC/USDT --timeframe 4h
```

يطبع تقريراً نصياً بمناطق العرض/الطلب والإشارة الحالية، ويحفظ رسماً بيانياً في
`reports/BTC_USDT_4h.png` يوضح السعر والمناطق ووقف الخسارة/الهدف.

### 2) اختبار الاستراتيجية على بيانات تاريخية

```bash
python main.py backtest --symbol BTC/USDT --timeframe 4h --candles 1000
```

يعرض عدد الصفقات، نسبة الفوز، ومتوسط العائد — **افعل هذا قبل أي تداول حقيقي**.

### 3) تداول (تجربة افتراضياً، أو حقيقي صراحةً)

```bash
# وضع تجربة (dry-run) - لا ينفذ أي أمر حقيقي، فقط يطبع ما كان سيحدث
python main.py trade --symbol BTC/USDT --timeframe 1h

# تنفيذ حقيقي - يتطلب --live و --confirm معاً + مفاتيح API + رصيدك الفعلي
python main.py trade --symbol BTC/USDT --timeframe 1h --live --confirm --balance 100
```

## هيكل المشروع

```
bot/
  config.py      # إعدادات من .env (مخاطرة، منصة، مفاتيح API)
  data_fetcher.py# جلب بيانات الشموع عبر ccxt
  indicators.py  # EMA, RSI, ATR, MACD
  zones.py       # اكتشاف مناطق العرض/الطلب
  signals.py     # دمج المناطق والمؤشرات لتوليد إشارة شراء/بيع
  risk.py        # حساب حجم الصفقة حسب نسبة المخاطرة
  executor.py    # تنفيذ الأوامر (تجربة أو حقيقي) عبر ccxt
  backtest.py    # اختبار الاستراتيجية على بيانات تاريخية
  report.py      # رسم بياني + تقرير نصي
main.py          # سطر الأوامر (analyze / backtest / trade)
```

## تخصيص الإعدادات (`.env`)

| المتغير | الوصف | الافتراضي |
|---|---|---|
| `EXCHANGE_ID` | معرّف المنصة في ccxt (مثل `binance` أو `okx`) | `binance` |
| `EXCHANGE_API_PASSPHRASE` | كلمة مرور API إضافية تتطلبها بعض المنصات فقط (OKX، KuCoin...) | فارغة |
| `EXCHANGE_SANDBOX` | استخدام testnet/sandbox | `true` |
| `RISK_PER_TRADE` | نسبة رأس المال المخاطر بها لكل صفقة | `0.01` (1%) |
| `MIN_REWARD_RISK_RATIO` | أقل نسبة مكافأة/خطر مقبولة للإشارة | `1.5` |
| `ZONE_PROXIMITY_PCT` | أقصى مسافة من منطقة عرض/طلب لقبول الإشارة | `0.006` (0.6%) |
| `REQUIRE_TREND_ALIGNMENT` | اشتراط توافق الإشارة مع اتجاه EMA50/EMA200 العام | `true` |

تعديل هذه القيم الثلاث الأخيرة يتحكم بتكرار الإشارات مقابل جودتها — **اختبرها دائماً عبر
`backtest` على بيانات حقيقية قبل تفعيلها في `watch --live`**:
```bash
# مثال: اختبار إعداد أكثر تساهلاً
ZONE_PROXIMITY_PCT=0.012 MIN_REWARD_RISK_RATIO=1.2 python main.py backtest --symbol BTC/USDT --timeframe 1h --candles 1500
```

## المراقبة المستمرة (watch) — تحليل وتنفيذ تلقائي دون تدخل

```bash
# تجربة مستمرة (dry-run) — لا ينفذ أي أمر حقيقي
python main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15

# مراقبة + تنفيذ تلقائي حقيقي (يتطلب مفاتيح API ومبلغاً حقيقياً في الحساب)
python main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15 --live --confirm
```

يفحص البوت السوق كل `--interval-minutes` دقيقة، ويحفظ حالة أي صفقة مفتوحة في ملف
`state_<الرمز>.json` حتى لا يفتح صفقات مكررة بين دورة وأخرى، ويراقب وقف
الخسارة/الهدف لإغلاقها تلقائياً. أوقفه بـ `Ctrl+C`، أو إن كان يعمل في الخلفية
بـ `pkill -f "main.py watch"`.

### إشعارات فورية على الهاتف (اختياري، Termux فقط)

إن كنت تشغّل البوت على Termux، يمكنه إرسال إشعار حقيقي على هاتفك فور ظهور
إشارة جديدة أو إغلاق صفقة، بدل الحاجة لمراجعة `watch.log` يدوياً:

```bash
pkg install -y termux-api
```
ثم ثبّت تطبيق **Termux:API** المرافق من [F-Droid](https://f-droid.org/packages/com.termux.api/)
(تطبيق منفصل مطلوب لتفعيل الإشعارات فعلياً). بعدها سيعمل الإشعار تلقائياً دون
أي إعداد إضافي في الكود — لا حاجة لفعل شيء إن لم تثبّت هذا، البوت يتجاهل
الإشعار بصمت ويستمر بالعمل عادةً (مفيد أيضاً عند التشغيل على خادم VPS لاحقاً).

⚠️ **لا تُشغّله مباشرة عبر `python` عند إعادة التوجيه إلى ملف سجل** (`> watch.log`)،
فمخرجات بايثون تُخزَّن مؤقتاً ولا تظهر في الملف فوراً. استخدم دائماً `python -u`
بدلاً من `python` في هذه الحالة:
```bash
nohup python -u main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15 --live --confirm > watch.log 2>&1 &
```

## النشر على خادم (VPS) للعمل المستمر 24/7

تشغيل البوت على هاتف شخصي عبر Termux يعمل، لكنه عرضة لتوقف أندرويد للتطبيق في
الخلفية، وانقطاع الشبكة، وعدم إعادة التشغيل التلقائي بعد إعادة تشغيل الهاتف أو
انقطاع الكهرباء/البطارية. للتشغيل الجاد طويل المدى، استخدم خادماً صغيراً رخيصاً
(VPS) يعمل Linux على مدار الساعة. الخطوات:

1. **استأجر VPS** برخيص (أي مزوّد: DigitalOcean, Hetzner, Vultr, Linode, Contabo...)
   بنظام Ubuntu 22.04 أو أحدث. أبسط الخطط (1 vCPU / 1GB RAM) كافية تماماً لهذا البوت.

2. **اتصل به عبر SSH وثبّت المتطلبات:**
   ```bash
   sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
   git clone https://github.com/wagja180/Nomir.git /opt/nomir/Nomir
   cd /opt/nomir/Nomir
   git checkout claude/market-analysis-bot-49fitt
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env   # ضع مفاتيح API ونسبة المخاطرة المطلوبة
   ```

3. **أنشئ مستخدماً مخصصاً للبوت (أفضل أمنياً من تشغيله بصلاحيات root):**
   ```bash
   sudo useradd -m -s /usr/sbin/nologin nomir
   sudo chown -R nomir:nomir /opt/nomir
   ```

4. **استخدم خدمة systemd بدل nohup** ليعمل البوت تلقائياً، ويُعاد تشغيله عند أي
   عطل أو إعادة تشغيل الخادم. ملف الخدمة جاهز في `deploy/nomir-bot.service` —
   عدّل فيه مسار المشروع واسم المستخدم إن اخترت غير `nomir`، ثم:
   ```bash
   sudo cp deploy/nomir-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now nomir-bot
   ```

5. **للمتابعة:**
   ```bash
   sudo systemctl status nomir-bot      # هل يعمل الآن؟
   journalctl -u nomir-bot -f           # سجل الأحداث مباشرة (أو: tail -f watch.log)
   sudo systemctl restart nomir-bot     # إعادة تشغيل بعد تعديل .env مثلاً
   sudo systemctl stop nomir-bot        # إيقاف نهائي
   ```

بهذا يعمل البوت باستمرار دون اعتماد على بقاء هاتفك مفتوحاً أو متصلاً، ويُعاد
تشغيله تلقائياً عند أي عطل أو إعادة إقلاع للخادم.

## الخطوات التالية الممكنة

- إضافة إشعارات (تيليجرام/بريد) عند ظهور إشارة أو تنفيذ صفقة.
- دعم عدة عملات/أزواج في آن واحد.

---

## مهارات إدارة حساب إنستغرام (Instagram Skills)

Thirteen Claude skills that run an Instagram account end to end — strategy, research, scripting, writing, and review. Free, MIT licensed.

Drop the `skills/` folder into a project with Claude Code (or any Claude surface that loads skills) and each one triggers automatically when the task fits — generate a Reel hook, lint a caption, humanize a stiff draft, diagnose a flop.

### The pipeline

```
ig-strategy  ──────────────────────────────────────────────┐
     │                                                      │
     ▼                                                      │
viral-research ──► trend-audio-finder                       │
     │                                                       │
     ▼                                                       │
reel-hook-generator ──► reel-scriptwriter ──► caption-writer │
                                                    │         │
                                                    ▼         │
                                            caption-linter     │
                                                    │          │
                                                    ▼          │
                                               humanizer       │
                                                    │          │
                                                    ▼          │
                                          hashtag-strategist   │
                                                                │
carousel-builder (alt. to reel-scriptwriter for list/guide posts)
                                                                │
content-calendar  ◄─────────────────────────────────────────┘ (schedules all of the above)
bio-optimizer      (profile-level, run independently)
performance-reviewer ──► feeds findings back into ig-strategy / viral-research / bio-optimizer
```

### Skills

| Skill | Does |
|---|---|
| [`ig-strategy`](skills/ig-strategy) | Defines niche, audience, content pillars, cadence, and success metrics. |
| [`viral-research`](skills/viral-research) | Breaks down why a given top-performing post worked and extracts a reusable pattern. |
| [`trend-audio-finder`](skills/trend-audio-finder) | Matches audio to a script's tempo/mood and keeps a running trend log. |
| [`reel-hook-generator`](skills/reel-hook-generator) | Generates and scores Reel hooks against **26 formulas** on a 5-dimension rubric. |
| [`reel-scriptwriter`](skills/reel-scriptwriter) | Builds a full timed script around a chosen hook. |
| [`caption-writer`](skills/caption-writer) | Drafts a caption with a standalone hook line and one CTA. |
| [`caption-linter`](skills/caption-linter) | Checks a caption against 9 fixed rules and reports pass/fail with fixes. |
| [`humanizer`](skills/humanizer) | Strips AI-sounding tells from a script or caption and adds concrete specificity. |
| [`hashtag-strategist`](skills/hashtag-strategist) | Picks a small tiered hashtag set instead of 30 generic tags. |
| [`carousel-builder`](skills/carousel-builder) | Structures a multi-slide carousel: hook slide, one idea per slide, CTA slide. |
| [`content-calendar`](skills/content-calendar) | Turns pillars + cadence into an actual weekly/monthly posting schedule. |
| [`bio-optimizer`](skills/bio-optimizer) | Optimizes bio text, link-in-bio, highlights, and searchability. |
| [`performance-reviewer`](skills/performance-reviewer) | Diagnoses which stage of a post failed (reach, hook, pacing, value, profile, CTA) from its metrics. |

### Usage

Each skill is a standard `SKILL.md` (with reference files where the subject needs more detail than belongs inline — the 26 hook formulas, the caption lint rules, the AI-tell list). Point Claude at this repo, or copy `skills/` into your own project's skills directory, and ask for what you need:

- "Give me a hook for a Reel about [topic]" → `reel-hook-generator`
- "Does this caption work?" → `caption-linter`
- "This script sounds like AI wrote it" → `humanizer`
- "Here are last week's numbers, what should I fix?" → `performance-reviewer`

No skill here has live access to Instagram's own data (trends, algorithm signals, account insights) — they work from what you give them (metrics you paste in, posts you link or describe) and say so rather than guessing.

### النسخة العربية / Arabic version

كل المهارات الـ13 متوفرة بنسخة عربية كاملة في [`skills-ar/`](skills-ar) (مثل `skills/caption-linter` → `skills-ar/caption-linter-ar`), بنفس البنية والـ`reference/` الخاصة بها، لكن بأسماء `name` مختلفة (بإضافة `-ar`) لتجنّب أي تعارض مع النسخة الإنجليزية عند تحميل المجلدين معًا.

All 13 skills also exist in a full Arabic translation under [`skills-ar/`](skills-ar) (e.g. `skills/caption-linter` → `skills-ar/caption-linter-ar`), same structure and reference files, with `-ar`-suffixed `name` fields so both language sets can be loaded side by side without colliding.

### License

MIT — see [LICENSE](LICENSE).
