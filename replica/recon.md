# Recon map: Cal.com — صفحة الحجز العامة (web)

Scope: صفحة الحجز التي يراها المريض فقط (ملف العيادة، اختيار الخدمة، اختيار الموعد، نموذج البيانات، التأكيد، الإلغاء وإعادة الجدولة من الرابط). لوحة تحكم Cal.com خارج النطاق.
For: عيادة المستخدم (حجز مواعيد المرضى).
Date: 2026-11-17

> **تنبيه مهم عن المصادر:** شبكة هذه الجلسة تحجب `cal.com` (رفض البروكسي برمز 403، ورفض المستخدم توسيع الشبكة).
> لم تُقرأ أي صفحة من Cal.com في هذه الجلسة. كل ما هنا مبني على معرفة سابقة عامة بمنتج Cal.com
> وبصفحة الحجز الخاصة به، لذلك كل درجات الثقة خُفّضت درجة، وكل صف يحتاج تحققاً.
> قبل `/replica-build` افتح المصادر أدناه بنفسك (أو اسمح بالنطاق) وصحّح ما يلزم، وضع لقطات مرجعية في `replica/screens/`.
>
> ملاحظة: Cal.com مفتوح المصدر، لكن قواعد هذه الحزمة تمنع قراءة كوده أو نسخه. نبني من السلوك الظاهر فقط.

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | help center / docs | https://cal.com/docs | لم يُقرأ (محجوب). أهم مصدر: إعدادات نوع الحدث وأسئلة الحجز |
| 2 | help center | https://cal.com/help | لم يُقرأ (محجوب) |
| 3 | pricing | https://cal.com/pricing | لم يُقرأ. يبيّن ما هو مدفوع (workflows، SMS، الفرق) |
| 4 | changelog | https://cal.com/changelog | لم يُقرأ |
| 5 | public API docs (v2) | https://cal.com/docs/api-reference/v2/introduction | لم يُقرأ. أفضل مصدر لنموذج البيانات (bookings, event-types, slots) |
| 6 | terms | https://cal.com/terms | لم يُقرأ. لا نستخدم حساباً على Cal.com، فبند "المنتج المنافس" غير مؤثر هنا، لكن تحقّق منه إن أنشأت حساباً للمقارنة |
| 7 | صفحة حجز عامة حقيقية | أي رابط `cal.com/<username>` عام | اقرأها يدوياً بسرعة إنسان، والتقط لقطات للحالات |
| 8 | معرفة سابقة | — | مصدر كل ما في هذا الملف حالياً |

## Core loop

مريض يفتح رابط العيادة، يختار الخدمة (والطبيب)، يختار يوماً ثم وقتاً متاحاً، يكتب اسمه ورقم هاتفه، ويحصل على تأكيد فوري مع رابط للإلغاء أو إعادة الجدولة.

## Screens

| ID | screen | route / how to reach | purpose | key components | states seen |
| --- | --- | --- | --- | --- | --- |
| S01 | ملف العيادة (قائمة الخدمات) | `/:clinic` | يعرض العيادة وكل الخدمات (أنواع الأحداث) القابلة للحجز | Avatar/Logo، اسم ونبذة، ServiceCard (الاسم، المدة، السعر إن وجد) | filled، empty (لا خدمات ظاهرة)، 404، mobile |
| S02 | صفحة الحجز: التقويم والأوقات | `/:clinic/:service` أو النقر من S01 | اختيار اليوم ثم الوقت | لوحة معلومات الخدمة (المضيف، العنوان، المدة، المكان، الوصف)، MonthCalendar، SlotList، TimezoneSelect، مفتاح 12/24 ساعة، اختيار المدة إن تعددت، تبديل العرض (شهري/أسبوعي/أعمدة) | loading، أيام متاحة مميّزة، يوم بلا أوقات، شهر بلا أوقات ("انتقل إلى أول موعد متاح")، mobile (عمودي مكدّس)، dark/light |
| S03 | نموذج بيانات الحجز | خطوة بعد اختيار الوقت (نفس الصفحة، اللوحة اليمنى تتبدل) | جمع بيانات المريض وتأكيد الحجز | ملخص الموعد المختار، Input (الاسم، البريد)، Textarea (ملاحظات)، إضافة ضيوف، أسئلة مخصصة (نص، رقم، هاتف، اختيار، اختيار متعدد، مربع تحقق، radio)، زر رجوع، زر تأكيد | validation error، submitting (زر loading)، الوقت أُخذ أثناء التعبئة (خطأ)، prefilled (من رابط أو عند إعادة الجدولة) |
| S04 | صفحة التأكيد / تفاصيل الحجز | `/booking/:uid` بعد الإرسال أو من رابط البريد | إظهار ما تم حجزه | أيقونة نجاح، العنوان، "ماذا/متى/من/أين"، الإجابات، "أضف إلى التقويم" (Google/Outlook/ICS)، روابط إعادة الجدولة والإلغاء | confirmed، pending (يتطلب موافقة العيادة)، cancelled، past (حجز انتهى)، rescheduled (يشير للموعد الجديد) |
| S05 | الإلغاء | زر الإلغاء في S04 (`/booking/:uid?cancel=true`) | المريض يلغي بنفسه | Textarea لسبب الإلغاء، زر تأكيد الإلغاء، زر تراجع | form، submitting، cancelled (S04 بحالة cancelled)، غير مسموح (موعد ماضٍ) |
| S06 | إعادة الجدولة | رابط إعادة الجدولة → S02 بوضع reschedule | اختيار وقت جديد لنفس الحجز | S02 + شارة "الموعد السابق"، S03 مملوء مسبقاً وحقل سبب اختياري | مثل S02/S03 |
| S07 | خطأ / غير موجود | رابط خاطئ، خدمة مخفية أو معطّلة | رسالة واضحة | رسالة، رابط العودة لـ S01 | 404، الخدمة غير متاحة |

ملاحظة: Cal.com يعرض S02 وS03 في نفس الإطار (لوحة معلومات يسار، تقويم وأوقات يمين) ويبدّل المحتوى دون الانتقال لصفحة جديدة. **الثقة: متوسطة.**

## Flows

```
F01 مريض يحجز موعداً (المسار الأساسي)
    S01 -> S02 (يوم ثم وقت) -> S03 -> S04
    happy path clicks: 4 نقرات (خدمة، يوم، وقت، تأكيد) + 3 حقول (اسم، بريد/هاتف، ملاحظة اختيارية)
    من رابط الخدمة مباشرة: 3 نقرات
    edge: لا أوقات هذا الشهر؛ منطقة زمنية مختلفة عن العيادة (مسافر)؛ الوقت أُخذ أثناء التعبئة؛
          حد أدنى للإشعار المسبق (لا يمكن الحجز خلال ساعتين مثلاً)؛ نافذة الحجز المستقبلي (30 يوماً فقط)؛
          حد يومي للحجوزات؛ بريد غير صالح؛ تغيّر التوقيت الصيفي بين الحجز والموعد

F02 مريض يلغي
    بريد التأكيد -> S04 -> S05 (سبب) -> S04 cancelled
    happy path clicks: 3 (الرابط، إلغاء، تأكيد)
    edge: موعد ماضٍ؛ رابط حجز مُلغى سابقاً؛ رابط بمعرّف غير موجود

F03 مريض يعيد الجدولة
    بريد التأكيد -> S04 -> S06 (S02 يوم ووقت) -> S03 مملوء -> S04 (الحجز الجديد، والقديم rescheduled)
    happy path clicks: 5
    edge: لا أوقات جديدة؛ نفس الوقت مختار؛ الحجز الأصلي ملغى

F04 حجز يتطلب موافقة العيادة (اختياري للعيادة)
    F01 -> S04 pending -> (العيادة توافق/ترفض خارج هذا النطاق) -> بريد للمريض -> S04 confirmed/cancelled
    edge: لا رد من العيادة قبل الموعد

F05 اختيار طبيب (عيادة بأكثر من طبيب)
    S01 (قائمة الأطباء أو الخدمات) -> S02 للطبيب المختار، أو "أي طبيب متاح" (round-robin)
    edge: الطبيب في إجازة؛ خدمة يقدمها طبيب واحد فقط
```

الرقم المطلوب التفوق عليه: **3 نقرات من الرابط المباشر**. اقتراح للعيادة: الهاتف بدل البريد كحقل رئيسي، والتعبئة التلقائية للمريض العائد.

## Components

| component | variants | states | used on |
| --- | --- | --- | --- |
| Button | primary، secondary، ghost، danger (إلغاء) | default، hover، focus، disabled، loading | S01–S07 |
| ServiceCard | مع سعر / بدون، مع مدة متعددة | default، hover، focus | S01 |
| ProfileHeader | عيادة / طبيب | — | S01، S02 |
| EventInfoPanel | كامل / مختصر (mobile) | — | S02، S03، S06 |
| MonthCalendar | — | يوم متاح، غير متاح، مختار، اليوم الحالي، ماضٍ، loading | S02، S06 |
| SlotList / SlotButton | قائمة، أعمدة أسبوعية | متاح، مختار، loading، فارغ | S02، S06 |
| TimezoneSelect | — | detected تلقائياً، مختار يدوياً، بحث | S02 |
| TimeFormatToggle | 12h / 24h | — | S02 |
| DurationPicker | أزرار مدد | مختار | S02 |
| LayoutToggle | شهري / أسبوعي / أعمدة | مختار | S02 (could) |
| TextInput / Email / Phone | — | default، focus، error، disabled | S03 |
| Textarea | — | default، error | S03، S05 |
| Select / Checkbox / Radio / MultiSelect | للأسئلة المخصصة | default، error | S03 |
| GuestsInput | إضافة بريد ضيف | — | S03 (could للعيادة: مرافق المريض) |
| SuccessHeader | confirmed، pending، cancelled | — | S04 |
| AddToCalendar | Google، Outlook، ICS | — | S04 |
| InlineError / Alert | error، warning، info | — | S03، S05، S07 |
| Toast | error | — | S03 (الوقت محجوز) |
| EmptyState | لا أوقات، لا خدمات | — | S01، S02 |
| Skeleton | تقويم، أوقات | — | S02 |

## Inferred data model

```
Clinic (User/Team في Cal.com)
            id, slug, name, bio, logo_url, timezone, locale, brand_color
            evidence: S01، رابط /:clinic
            confidence: medium (من الذاكرة)

Practitioner (عضو فريق)  id, clinic_id, name, avatar_url, timezone
            evidence: S01 / F05، مفهوم فرق Cal.com
            confidence: guess

Service (EventType)
            id, clinic_id, slug, title, description, length_minutes, durations[] (اختياري),
            location (in_person: address | phone | video), price, currency,
            hidden, requires_confirmation, minimum_notice_minutes,
            before_buffer, after_buffer, period (rolling N days | date range | unlimited),
            booking_limits (per day/week), seats_per_slot, slot_interval,
            booking_fields (json: الأسئلة)، success_redirect_url
            evidence: S02 لوحة المعلومات، إعدادات نوع الحدث في Cal.com، API v2 event-types
            confidence: medium

Schedule / Availability
            id, owner_id, timezone, weekly_rules [{day, start, end}], date_overrides [{date, start, end | off}]
            evidence: أيام وأوقات متاحة في S02
            confidence: medium

Slot (محسوب، غير مخزّن)
            start, end, attendees_count (للمقاعد)
            evidence: S02، API v2 /slots
            confidence: medium

Booking
            id, uid (لروابط S04)، service_id, practitioner_id, start_at, end_at,
            status (accepted | pending | cancelled | rejected), rescheduled_from_uid,
            cancellation_reason, reschedule_reason, location, responses (json),
            created_at
            evidence: S03، S04، S05، S06، API v2 bookings
            confidence: medium

Attendee
            id, booking_id, name, email, phone, timezone, locale
            evidence: S03 (الاسم، البريد، الضيوف)
            confidence: medium
```

Relationships: Clinic 1-n Practitioner، Clinic 1-n Service، Practitioner n-n Service، Practitioner 1-n Schedule، Service 1-n Booking، Booking 1-n Attendee، Booking 0-1 Booking (rescheduled_from).

ملاحظة للعيادة: لا تخزّن تشخيصاً أو تاريخاً مرضياً في `responses`. اجعل الأسئلة إدارية (سبب الزيارة باختصار، مريض جديد/عائد) لتقليل البيانات الصحية الحساسة.

## Feature matrix

See `features.csv`. Must: 17, should: 13, could: 9, skip: 6.

## Out of scope (cannot or should not be cloned)

- لوحة تحكم Cal.com كاملة (إنشاء الحسابات، الإعدادات، التحليلات). نحتاج فقط إعداداً بسيطاً للعيادة، يقرره `/replica-architect`.
- متجر التطبيقات وتكاملات الشركاء (App Store).
- علامة Cal.com التجارية وشعارها ونصوصها التسويقية وأيقوناتها.
- السجلات الطبية الإلكترونية وأي بيانات علاجية: مجال منظَّم (قوانين حماية البيانات الصحية المحلية، وHIPAA إن وُجد مرضى أمريكيون). صفحة الحجز تجمع بيانات إدارية فقط.
- إرسال SMS/WhatsApp مجاناً: يتطلب مزوداً مدفوعاً (مثل Twilio أو WhatsApp Business API) وحسابك الخاص.
- قراءة كود Cal.com المفتوح أو نسخه.

## Size

Screens 7، flows 5، entities 7 (Clinic، Practitioner، Service، Schedule، Slot، Booking، Attendee).

Hard parts:
1. **حساب الأوقات المتاحة**: المناطق الزمنية، التوقيت الصيفي، الفواصل، الحد الأدنى للإشعار، حدود الحجز، وتعارضها مع مواعيد قائمة.
2. **منع الحجز المزدوج**: حالة التسابق عند حجز مريضين لنفس الوقت (قيد فريد أو قفل في قاعدة البيانات).
3. **الإشعارات**: بريد التأكيد والتذكير (وظائف مجدولة)، وWhatsApp/SMS عبر مزوّد خارجي.
4. (اختياري) **مزامنة Google Calendar** للأطباء لقراءة أوقات الانشغال.
5. **العربية وRTL** في التقويم والأرقام والتواريخ.

Size: **S إلى M**. صفحة حجز لطبيب واحد بإعدادات ثابتة وبريد تأكيد: S (نهاية أسبوع). مع عدة أطباء وتذكيرات وWhatsApp ومزامنة تقويم: M (بضعة أسابيع).
